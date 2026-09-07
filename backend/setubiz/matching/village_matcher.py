"""Phonetic village matching (PLAN.md §6 — demo-critical).

A rural user says "Ormanjhi"; ASR writes "Ormanji", "Aurmanjhi" or "ओरमांझी". A plain string match
fails on all three. We transliterate, reduce to an Indic-adapted Soundex code, blend that with a
fuzzy ratio and a geography prior, and return the top three for the user to confirm — we never
silently pick one.
"""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from setubiz.data.loader import DataSource, Village
from setubiz.geo import haversine_km
from setubiz.schemas import VillageMatch

#: Devanagari → Latin. Deliberately small: village names use a narrow slice of the script, and a
#: full ITRANS dependency buys nothing here.
_DEVANAGARI = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "ii",
    "उ": "u",
    "ऊ": "uu",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "ऋ": "ri",
    "क": "k",
    "ख": "kh",
    "ग": "g",
    "घ": "gh",
    "ङ": "n",
    "च": "ch",
    "छ": "chh",
    "ज": "j",
    "झ": "jh",
    "ञ": "n",
    "ट": "t",
    "ठ": "th",
    "ड": "d",
    "ढ": "dh",
    "ण": "n",
    "त": "t",
    "थ": "th",
    "द": "d",
    "ध": "dh",
    "न": "n",
    "प": "p",
    "फ": "ph",
    "ब": "b",
    "भ": "bh",
    "म": "m",
    "य": "y",
    "र": "r",
    "ल": "l",
    "व": "v",
    "श": "sh",
    "ष": "sh",
    "स": "s",
    "ह": "h",
    "ळ": "l",
    "क़": "q",
    "ख़": "kh",
    "ग़": "g",
    "ज़": "z",
    "ड़": "r",
    "ढ़": "rh",
    "फ़": "f",
    "ा": "a",
    "ि": "i",
    "ी": "i",
    "ु": "u",
    "ू": "u",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ृ": "ri",
    "ं": "n",
    "ँ": "n",
    "ः": "h",
    "्": "",
    "़": "",
}

_ASPIRATES = (
    ("chh", "c"),
    ("ch", "c"),
    ("kh", "k"),
    ("gh", "g"),
    ("jh", "j"),
    ("th", "t"),
    ("dh", "d"),
    ("ph", "p"),
    ("bh", "b"),
    ("sh", "s"),
    ("rh", "r"),
    ("aa", "a"),
    ("ii", "i"),
    ("uu", "u"),
    ("ee", "i"),
    ("oo", "u"),
)

_SOUNDEX_GROUPS = {
    **dict.fromkeys("bfpvw", "1"),
    **dict.fromkeys("cgjkqsxz", "2"),
    **dict.fromkeys("dt", "3"),
    **dict.fromkeys("l", "4"),
    **dict.fromkeys("mn", "5"),
    **dict.fromkeys("r", "6"),
}


#: The nukta letters are composition-excluded, so NFC leaves them as base + U+093C. Written as
#: escapes because a literal here would itself be stored decomposed and never match.
#: बेड़ो is Bero, not Bedo — U+0921 U+093C is a retroflex flap, not a plain "d".
_NUKTA_PAIRS = {
    "\u0915\u093c": "q",
    "\u0916\u093c": "kh",
    "\u0917\u093c": "g",
    "\u091c\u093c": "z",
    "\u0921\u093c": "r",  # retroflex flap: Bero, not Bedo
    "\u0922\u093c": "rh",
    "\u092b\u093c": "f",
}


def transliterate(text: str) -> str:
    """Devanagari to a rough Latin form; Latin input passes through normalized."""
    normalized = unicodedata.normalize("NFC", text)
    for pair, latin in _NUKTA_PAIRS.items():
        normalized = normalized.replace(pair, latin)
    out = []
    for ch in normalized:
        out.append(_DEVANAGARI.get(ch, ch))
    latin = "".join(out).lower()
    return re.sub(r"[^a-z ]+", "", latin).strip()


def indic_soundex(text: str, length: int = 4) -> str:
    """Soundex with aspirated digraphs folded first — 'Ormanjhi' and 'Ormanji' must agree."""
    latin = transliterate(text).replace(" ", "")
    for src, dst in _ASPIRATES:
        latin = latin.replace(src, dst)
    if not latin:
        return ""
    head, tail = latin[0], latin[1:]
    codes = []
    previous = _SOUNDEX_GROUPS.get(head, "")
    for ch in tail:
        code = _SOUNDEX_GROUPS.get(ch, "")
        if code and code != previous:
            codes.append(code)
        if ch not in "hy":  # h and y do not break a run of the same group
            previous = code
    return (head.upper() + "".join(codes)).ljust(length, "0")[:length]


def _score(query: str, village: Village, near: tuple[float, float] | None) -> tuple[float, str]:
    q_latin = transliterate(query)
    candidates = [transliterate(village.name)]
    if village.name_hi:
        candidates.append(transliterate(village.name_hi))

    fuzzy = max(fuzz.WRatio(q_latin, c) for c in candidates) / 100.0
    phonetic = 1.0 if any(indic_soundex(query) == indic_soundex(c) for c in candidates) else 0.0
    prior = 0.0
    if near:
        distance = haversine_km(near[0], near[1], village.lat, village.lon)
        prior = max(0.0, 1.0 - distance / 50.0)

    score = 0.55 * fuzzy + 0.30 * phonetic + 0.15 * prior
    if phonetic and fuzzy > 0.8:
        reason = "spelling and pronunciation both match"
    elif phonetic:
        reason = f"sounds the same ({indic_soundex(village.name)})"
    elif fuzzy > 0.85:
        reason = "spelling is a close match"
    else:
        reason = "partial match"
    if near and prior > 0.5:
        reason += ", and it is nearby"
    return round(score, 4), reason


def match_villages(
    query: str,
    source: DataSource,
    *,
    state: str | None = None,
    district: str | None = None,
    near: tuple[float, float] | None = None,
    limit: int = 3,
    min_score: float = 0.35,
) -> tuple[VillageMatch, ...]:
    """Top-`limit` candidates, highest first. The UI must ask the user to confirm."""
    if not query.strip():
        return ()

    pool = [
        v
        for v in source.all_villages()
        if (state is None or v.state.lower() == state.lower())
        and (district is None or v.district.lower() == district.lower())
    ]

    scored = []
    for village in pool:
        score, reason = _score(query, village, near)
        if score >= min_score:
            scored.append(
                VillageMatch(
                    shrid=village.shrid,
                    name=village.name,
                    name_hi=village.name_hi,
                    block=village.block,
                    district=village.district,
                    state=village.state,
                    score=score,
                    reason=reason,
                )
            )
    scored.sort(key=lambda m: (-m.score, m.name))
    return tuple(scored[:limit])
