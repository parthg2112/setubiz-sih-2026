"""Which document is this? Keyword and layout scoring, deliberately not a model.

A classifier with three classes and a handful of near-unmistakable keywords does not need to be
learned, and a rule a judge can read beats an accuracy figure they cannot check. It also means
the answer is the same every time, which matters when the next stage is a set difference.
"""

from __future__ import annotations

import re

from setubiz.documents.schemas import DocumentKind

#: Words that place a document, in both scripts. Weighted: a word that only ever appears on one
#: kind of document counts for more than one that could appear on any of them.
_MARKERS: dict[DocumentKind, tuple[tuple[str, int], ...]] = {
    DocumentKind.QUOTATION: (
        ("quotation", 3),
        ("quote", 2),
        ("proforma", 3),
        ("estimate", 2),
        ("invoice", 2),
        ("gstin", 2),
        ("unit rate", 2),
        ("qty", 1),
        ("quantity", 1),
        ("amount", 1),
        ("total", 1),
        ("कोटेशन", 3),
        ("प्रस्ताव", 2),
        ("अनुमान", 2),
        ("दर", 1),
        ("मात्रा", 1),
        ("कुल", 1),
    ),
    DocumentKind.INCOME_CERTIFICATE: (
        ("income certificate", 4),
        ("annual income", 3),
        ("family income", 3),
        ("income", 1),
        ("tehsildar", 1),
        ("आय प्रमाण", 4),
        ("वार्षिक आय", 3),
        ("पारिवारिक आय", 3),
        ("आय", 1),
    ),
    DocumentKind.CASTE_CERTIFICATE: (
        ("caste certificate", 4),
        ("community certificate", 4),
        ("scheduled caste", 3),
        ("scheduled tribe", 3),
        ("backward class", 3),
        ("caste", 1),
        ("जाति प्रमाण", 4),
        ("अनुसूचित जाति", 3),
        ("अनुसूचित जनजाति", 3),
        ("पिछड़ा वर्ग", 3),
        ("जाति", 1),
    ),
}

#: A quotation is the only one of the three that is a table of money, so several lines carrying
#: two or more amounts is strong evidence on its own, whatever the header says.
_AMOUNT = re.compile(r"(?:₹|rs\.?|inr)?\s*\d[\d,]{2,}(?:\.\d{2})?", re.IGNORECASE)


def _tabular_score(text: str) -> int:
    money_lines = sum(1 for line in text.splitlines() if len(_AMOUNT.findall(line)) >= 2)
    return min(money_lines, 5)


def classify(text: str) -> tuple[DocumentKind, dict[str, int]]:
    """Return the best guess and every score, so a wrong answer can be argued with."""
    lowered = text.lower()
    scores = {
        kind: sum(weight for word, weight in markers if word in lowered)
        for kind, markers in _MARKERS.items()
    }
    scores[DocumentKind.QUOTATION] += _tabular_score(text)

    best = max(scores, key=lambda k: scores[k])
    # Two points is one strong keyword or two weak ones. Below that we say we do not know, which
    # is a better answer than routing a caste certificate through a quotation parser.
    kind = best if scores[best] >= 2 else DocumentKind.UNKNOWN
    return kind, {k.value: v for k, v in scores.items()}
