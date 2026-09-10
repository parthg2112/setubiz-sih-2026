"""Real OpenStreetMap points of interest, per state, via the Overpass API.

Emits `pois/<CODE>.json.gz` in the schema `SampleDataSource` already reads. One request per
(state, category), cached on disk so a rebuild costs nothing and the public endpoint is not
hammered.

Rural OSM coverage is sparse and uneven, which is *why* `feasibility/competitors.py` treats an
observed POI count as a floor on competitors rather than a census. That framing is preserved in
the emitted `_meta.known_limitation`.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from common import (
    CACHE,
    DEFAULT_OUT,
    PC11_STATES,
    meta,
    resolve_state,
    state_code,
    state_name,
    write_json,
)

ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "SetuBiz-ETL/0.1 (SIH26091 rural advisory prototype; contact via repo)"

#: ISO 3166-2 subdivision codes, which is how OSM tags Indian states. Keyed by PC11 state id.
ISO_3166_2: dict[str, str] = {
    "01": "IN-JK", "02": "IN-HP", "03": "IN-PB", "04": "IN-CH", "05": "IN-UT",
    "06": "IN-HR", "07": "IN-DL", "08": "IN-RJ", "09": "IN-UP", "10": "IN-BR",
    "11": "IN-SK", "12": "IN-AR", "13": "IN-NL", "14": "IN-MN", "15": "IN-MZ",
    "16": "IN-TR", "17": "IN-ML", "18": "IN-AS", "19": "IN-WB", "20": "IN-JH",
    "21": "IN-OR", "22": "IN-CT", "23": "IN-MP", "24": "IN-GJ", "25": "IN-DD",
    "26": "IN-DN", "27": "IN-MH", "28": "IN-AP", "29": "IN-KA", "30": "IN-GA",
    "31": "IN-LD", "32": "IN-KL", "33": "IN-TN", "34": "IN-PY", "35": "IN-AN",
}

#: category -> OSM tag filters. Categories match the cost templates and the EC13 split;
#: "mandi" is what `feasibility/market_reach.py` counts for buyer concentration.
CATEGORY_TAGS: dict[str, list[str]] = {
    "dairy": ['"shop"="dairy"', '"amenity"="dairy"', '"craft"="dairy"'],
    "kirana": ['"shop"="convenience"', '"shop"="general"', '"shop"="grocery"',
               '"shop"="supermarket"'],
    "tailoring": ['"craft"="tailor"', '"shop"="tailor"', '"craft"="dressmaker"'],
    "poultry": ['"shop"="butcher"', '"shop"="poultry"', '"craft"="poultry"'],
    "flour_mill": ['"craft"="grinding_mill"', '"shop"="flour"', '"man_made"="flour_mill"'],
    "mandi": ['"amenity"="marketplace"', '"shop"="farm"'],
}


def query_for(iso: str, tags: list[str]) -> str:
    clauses = "".join(
        f"  node[{t}](area.a);\n  way[{t}](area.a);\n  relation[{t}](area.a);\n" for t in tags
    )
    return (
        f'[out:json][timeout:300];\narea["ISO3166-2"="{iso}"]->.a;\n'
        f"(\n{clauses});\nout center tags;\n"
    )


def fetch(query: str, *, pause: float, retries: int = 3) -> dict:
    """Cached POST to Overpass. The cache key is the query itself, so edits invalidate cleanly."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"overpass-{hashlib.sha256(query.encode()).hexdigest()[:16]}.json.gz"
    if path.exists():
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)

    body = urllib.parse.urlencode({"data": query}).encode()
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(ENDPOINT, data=body, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=330) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            with gzip.open(path, "wt", encoding="utf-8") as fh:
                json.dump(payload, fh)
            time.sleep(pause)  # be a good citizen on a free shared endpoint
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            wait = pause * (2**attempt)
            print(f"    attempt {attempt}/{retries} failed ({exc}); retrying in {wait:.0f}s")
            time.sleep(wait)
    raise SystemExit(f"Overpass failed after {retries} attempts: {last}")


def elements_to_pois(payload: dict, category: str) -> list[dict]:
    out: list[dict] = []
    for el in payload.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        tags = el.get("tags", {})
        # The tag that actually matched, for provenance — not a guess about what the place is.
        osm_tag = next(
            (f"{k}={tags[k]}" for k in ("shop", "craft", "amenity", "man_made") if k in tags),
            "",
        )
        out.append({
            "id": f"{el.get('type','n')[0]}{el.get('id')}",
            "name": tags.get("name") or tags.get("name:en") or f"unnamed {category}",
            "category": category,
            "osm_tag": osm_tag,
            "lat": round(float(lat), 6),
            "lon": round(float(lon), 6),
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", default=["JH"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pause", type=float, default=5.0, help="seconds between Overpass requests")
    args = ap.parse_args()

    wanted = (sorted(PC11_STATES) if args.states == ["all"]
              else sorted({resolve_state(s) for s in args.states}))

    for sid in wanted:
        iso = ISO_3166_2[sid]
        print(f"{state_name(sid)} ({iso})")
        pois: list[dict] = []
        per_category: dict[str, int] = {}
        for category, tags in CATEGORY_TAGS.items():
            payload = fetch(query_for(iso, tags), pause=args.pause)
            found = elements_to_pois(payload, category)
            per_category[category] = len(found)
            pois.extend(found)
            print(f"  {category:<11} {len(found):>6}")

        write_json(
            args.out / "pois" / f"{state_code(sid)}.json",
            {
                "_meta": meta(
                    "OpenStreetMap via Overpass API",
                    "Real observations. Licensed ODbL — attribution required.",
                    state=state_name(sid),
                    iso_3166_2=iso,
                    counts=per_category,
                    tags={k: v for k, v in CATEGORY_TAGS.items()},
                    known_limitation=(
                        "Rural OSM coverage is sparse and uneven. A POI count is a floor on the "
                        "number of competitors, never a census of them."
                    ),
                ),
                "pois": pois,
            },
            compress=True,
        )
        print(f"  total {len(pois):,}")


if __name__ == "__main__":
    main()
