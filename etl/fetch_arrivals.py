"""AGMARKNET mandi arrivals and modal prices.

Two lanes, because the two things this project needs come from different places:

* **Live prices** — data.gov.in resource 9ef84268-d588-465a-a308-a864a43d0070. This resource is a
  *daily snapshot* ("Current Daily Price of Various Commodities from Various Markets"), so it
  gives today's modal price per market, and nothing historical.
* **The 12-month series** that `feasibility/threats.py` needs for the seasonality index. One API
  call cannot produce it. Export it from the AGMARKNET portal (agmarknet.gov.in -> Price/Arrival
  report -> monthly, 12 months) and pass the CSV with `--history`.

If no history is supplied the script still emits a valid `arrivals.json` carrying the live prices
and **no** `series`. `threats.assess` already handles a missing series by dropping the seasonality
threat, so the report simply says less rather than saying something invented.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

from common import CACHE, DEFAULT_OUT, meta, resolve_state, state_name, write_json

RESOURCE = "9ef84268-d588-465a-a308-a864a43d0070"
ENDPOINT = f"https://api.data.gov.in/resource/{RESOURCE}"
SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

#: Which mandi commodity stands in for each business category's input or output price risk.
CATEGORY_COMMODITY: dict[str, str] = {
    "dairy": "Maize",        # fodder/feed cost
    "poultry": "Maize",      # feed cost
    "flour_mill": "Wheat",   # the grain being milled
    "kirana": "Potato",      # a high-turnover staple line
    "tailoring": "",         # no mandi commodity drives a tailoring unit
}
MONSOON_DEPENDENT = ["dairy", "poultry", "flour_mill"]


def api_key() -> str:
    key = os.environ.get("SETUBIZ_DATA_GOV_API_KEY", "").strip()
    if not key:
        env = Path(__file__).resolve().parent.parent / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("SETUBIZ_DATA_GOV_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        raise SystemExit(
            "No data.gov.in key. Set SETUBIZ_DATA_GOV_API_KEY in .env or the environment.\n"
            "Get one from data.gov.in -> My Account -> Generate API Key."
        )
    if key == SAMPLE_KEY:
        print("  WARNING: this is the portal's public SAMPLE key. It is shared, rate-limited and")
        print("           returns at most 10 records. Generate a personal key for a real pull.")
    return key


def fetch_page(key: str, state: str, offset: int, limit: int) -> dict:
    params = {"api-key": key, "format": "json", "limit": str(limit), "offset": str(offset),
              "filters[state.keyword]": state}
    url = f"{ENDPOINT}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}: {exc.read()[:160]!r}"}
    except (urllib.error.URLError, TimeoutError) as exc:
        # The shared sample key routinely stalls. A missing snapshot must not abort the build.
        return {"error": f"request failed ({exc}) - likely the shared sample key throttling"}
    except json.JSONDecodeError as exc:
        return {"error": f"non-JSON response ({exc})"}


def live_prices(key: str, state: str, *, pages: int, limit: int) -> list[dict]:
    """Today's snapshot for one state. Returns [] (with a printed reason) rather than raising."""
    records: list[dict] = []
    for page in range(pages):
        payload = fetch_page(key, state, page * limit, limit)
        if "error" in payload:
            print(f"  API error: {payload['error']}")
            break
        batch = payload.get("records") or []
        records.extend(batch)
        if len(batch) < limit:
            break
        time.sleep(1)
    return records


def parse_history(path: Path) -> dict[str, dict[str, list[int]]]:
    """AGMARKNET portal monthly export -> {commodity: {arrivals: [...12], modal_price: [...12]}}.

    Column names on the portal export vary by report; we match case-insensitively on substrings
    rather than assuming one exact header.
    """
    arrivals: dict[str, dict[int, float]] = defaultdict(dict)
    prices: dict[str, dict[int, float]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower().strip(): c for c in (reader.fieldnames or [])}

        def find(*needles: str) -> str | None:
            for low, orig in cols.items():
                if all(n in low for n in needles):
                    return orig
            return None

        c_comm, c_month = find("commodity"), find("month")
        c_arr, c_price = find("arrival"), find("modal")
        if not all([c_comm, c_month, c_arr, c_price]):
            raise SystemExit(
                f"{path.name}: could not find commodity/month/arrival/modal columns in "
                f"{reader.fieldnames}"
            )
        for row in reader:
            month = (row[c_month] or "").strip()[:3].title()
            if month not in MONTHS:
                continue
            i = MONTHS.index(month)
            comm = (row[c_comm] or "").strip().title()
            for raw, sink in ((row[c_arr], arrivals), (row[c_price], prices)):
                # A blank or malformed cell just means that month is unreported; the 12/12
                # completeness check below is what decides whether the series is usable.
                with contextlib.suppress(TypeError, ValueError):
                    sink[comm][i] = float(str(raw).replace(",", "").strip())

    series: dict[str, dict[str, list[int]]] = {}
    for comm in set(arrivals) | set(prices):
        a, p = arrivals.get(comm, {}), prices.get(comm, {})
        if len(a) == 12 and len(p) == 12:
            series[comm] = {"arrivals": [int(a[i]) for i in range(12)],
                            "modal_price": [int(p[i]) for i in range(12)]}
        else:
            print(f"  skipping {comm}: {len(a)}/12 arrival months, {len(p)}/12 price months")
    return series


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", default=["JH"])
    ap.add_argument("--history", type=Path, help="AGMARKNET portal monthly CSV export")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args()

    key = api_key()
    wanted = [resolve_state(s) for s in args.states]

    markets: dict[str, dict] = {}
    live: dict[str, list[dict]] = {}
    for sid in wanted:
        name = state_name(sid)
        print(f"{name}: fetching live snapshot")
        records = live_prices(key, name, pages=args.pages, limit=args.limit)
        print(f"  {len(records)} records")
        if records:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / f"agmarknet-{name.replace(' ', '_')}.json").write_text(
                json.dumps(records), encoding="utf-8")
            live[name] = [
                {"market": r.get("market"), "district": r.get("district"),
                 "commodity": r.get("commodity"), "modal_price": r.get("modal_price"),
                 "arrival_date": r.get("arrival_date")}
                for r in records
            ]
            busiest = defaultdict(int)
            for r in records:
                busiest[(r.get("market"), r.get("district"))] += 1
            (market, district), _ = max(busiest.items(), key=lambda kv: kv[1])
            markets[name] = {"name": market, "district": district, "state": name}

    series = parse_history(args.history) if args.history else {}
    if not series:
        print("  no 12-month history supplied — emitting without `series`.")
        print("  threats.assess drops the seasonality index rather than inventing one.")

    payload = {
        "_meta": meta(
            f"AGMARKNET via data.gov.in resource {RESOURCE}"
            + (f", 12-month history from {args.history.name}" if series else ""),
            "Real observations." if series else
            "Live prices only. The API resource is a daily snapshot and carries no history.",
            arrivals_unit="tonnes/month",
            price_unit="Rs/quintal",
            url=f"https://www.data.gov.in/resource/{RESOURCE}",
            has_seasonality=bool(series),
            method_note=(
                "The data.gov.in resource publishes only the current day's prices. The 12-month "
                "arrivals and modal-price series required by the seasonality index must be "
                "exported from agmarknet.gov.in and passed with --history."
            ),
        ),
        "category_commodity_proxy": {k: v for k, v in CATEGORY_COMMODITY.items() if v},
        "market": next(iter(markets.values()), None),
        "markets_by_state": markets,
        "series": series,
        "months": MONTHS,
        "monsoon_dependent_categories": MONSOON_DEPENDENT,
        "live_prices": live,
    }
    write_json(args.out / "arrivals.json", payload)


if __name__ == "__main__":
    main()
