"""Economic Census 2013 enterprise density, from the real SHRUG village-level extract.

Emits `ec13_density.json` in the schema `SampleDataSource.block_density` and
`district_density_stats` already read: block densities per 1,000 households, plus per-district
mean and standard deviation for the z-score in `feasibility/competitors.py`.

Two honesty constraints are baked in:

* EC13 covers rural *and* urban shrids, but Mission Antyodaya — the household denominator — is
  rural-only. Mixing them puts a town's establishments over a handful of rural households and
  produces densities in the thousands. The numerator is therefore restricted to the rural shrid
  set from `ec13r_shrid_key.csv`, so numerator and denominator describe the same universe.
* EC13 ships **establishment counts only in total** (`ec13_count_all`). The 90 `ec13_emp_shric_*`
  columns are *employment*, not counts, so a per-category establishment figure can only be
  apportioned: `count_all x (emp_shric_cat / emp_all)`. That is an approximation and the emitted
  `method` string says so. It is never presented as an observed count.
* The category split needs the SHRIC -> category mapping, which is a separate SHRUG download
  (the "SHRIC Industry Code" module). Without it this script still emits the real, unambiguous
  `all` density rather than guessing which code means "dairy".
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

from common import (
    DATASETS,
    DEFAULT_OUT,
    PC11_STATES,
    meta,
    num,
    progress,
    read_csv,
    resolve_state,
    state_name,
    write_json,
)

EC13 = DATASETS / "shrug-ec13-csv" / "ec13_shrid.csv"
EC13_RURAL_KEY = DATASETS / "shrug-ec-keys-csv" / "ec13r_shrid_key.csv"
NAMES = DATASETS / "shrug-shrid-keys-csv" / "shrid_loc_names.csv"
ANTYODAYA = DATASETS / "shrug-antyodaya-csv" / "antyodaya_shrid.csv"
MAPPING = Path(__file__).resolve().parent / "shric_categories.json"

#: A block needs enough households for a per-1,000 rate to mean anything.
MIN_BLOCK_HOUSEHOLDS = 100


#: shrid2 is "11-<state>-<district>-<subdistrict>-<village>". A block is the subdistrict.
def block_key(shrid: str) -> str | None:
    parts = shrid.split("-")
    return "-".join(parts[:4]) if len(parts) >= 5 else None


def district_key(shrid: str) -> str | None:
    parts = shrid.split("-")
    return "-".join(parts[:3]) if len(parts) >= 5 else None


def load_mapping() -> dict[str, list[int]]:
    """category -> [shric codes]. Absent is fine; we then emit only the total density."""
    if not MAPPING.exists():
        print(f"  note: {MAPPING.name} absent — emitting total enterprise density only.")
        print("        Download the SHRUG 'SHRIC Industry Code' module to unlock the split.")
        return {}
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    return {k: [int(c) for c in v] for k, v in mapping.items() if not k.startswith("_")}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", default=["JH"],
                    help="PC11 ids, 2-letter codes or names; 'all' for every state")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wanted = (set(PC11_STATES) if args.states == ["all"]
              else {resolve_state(s) for s in args.states})
    print(f"EC13 density for {len(wanted)} state(s): {sorted(state_name(s) for s in wanted)}")

    categories = load_mapping()

    # Block and district names, so the emitted keys match what Village.district / .block carry.
    # Keys are "State|District|Block": block names repeat across districts and districts repeat
    # across states, so a bare name is ambiguous the moment more than one state ships.
    block_name: dict[str, str] = {}
    district_name: dict[str, str] = {}
    for n, row in enumerate(read_csv(NAMES, ["shrid2", "state_name", "district_name",
                                             "subdistrict_name"]), 1):
        progress("loc names", n)
        shrid = row["shrid2"].strip()
        if shrid.split("-")[1] not in wanted:
            continue
        bk, dk = block_key(shrid), district_key(shrid)
        st = (row["state_name"] or "").strip().title()
        di = (row["district_name"] or "").strip().title()
        sd = (row["subdistrict_name"] or "").strip().title()
        if bk and st and di and sd:
            block_name[bk] = f"{st}|{di}|{sd}"
        if dk and st and di:
            district_name[dk] = f"{st}|{di}"
    print(f"  named {len(block_name):,} blocks, {len(district_name):,} districts")

    # Rural shrids only — see the module docstring. Antyodaya has no urban rows, so an urban
    # numerator over a rural denominator is a category error, not an outlier to clip.
    rural: set[str] = set()
    for n, row in enumerate(read_csv(EC13_RURAL_KEY, ["shrid2"]), 1):
        progress("ec13 rural key", n)
        s = row["shrid2"].strip()
        if s and s.split("-")[1] in wanted:
            rural.add(s)
    print(f"  {len(rural):,} rural shrids in scope")

    emp_cols = sorted({c for codes in categories.values() for c in codes})
    cols = ["shrid2", "ec13_count_all", "ec13_emp_all"] + [f"ec13_emp_shric_{c}" for c in emp_cols]

    # --- households per block, from Mission Antyodaya ---
    households: dict[str, float] = defaultdict(float)
    for n, row in enumerate(read_csv(ANTYODAYA, ["shrid2", "total_hhd"]), 1):
        progress("antyodaya", n)
        key = block_key(row["shrid2"])
        if key and key.split("-")[1] in wanted:
            households[key] += num(row["total_hhd"], 0.0) or 0.0
    print(f"  households aggregated for {len(households):,} blocks")

    # --- enterprise counts per block, from EC13 ---
    counts: dict[str, float] = defaultdict(float)
    emp_all: dict[str, float] = defaultdict(float)
    emp_cat: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for n, row in enumerate(read_csv(EC13, cols), 1):
        progress("ec13", n)
        if row["shrid2"].strip() not in rural:
            continue
        key = block_key(row["shrid2"])
        if not key:
            continue
        counts[key] += num(row["ec13_count_all"], 0.0) or 0.0
        emp_all[key] += num(row["ec13_emp_all"], 0.0) or 0.0
        for cat, codes in categories.items():
            emp_cat[key][cat] += sum(
                num(row.get(f"ec13_emp_shric_{c}"), 0.0) or 0.0 for c in codes
            )
    print(f"  EC13 aggregated for {len(counts):,} blocks")

    # --- densities per 1,000 households ---
    blocks: dict[str, dict[str, float]] = {}
    for key, hh in households.items():
        if hh < MIN_BLOCK_HOUSEHOLDS or key not in counts or key not in block_name:
            continue  # too few households for a per-1,000 rate, or no name to key it by
        total = counts[key]
        row: dict[str, float] = {"all": round(total * 1000 / hh, 2)}
        if emp_all[key] > 0:
            for cat in categories:
                share = emp_cat[key][cat] / emp_all[key]
                row[cat] = round(total * share * 1000 / hh, 2)
        blocks[block_name[key]] = row

    # --- district mean/std across blocks, for the z-score ---
    by_district: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for key, row in blocks.items():
        dk = "|".join(key.split("|")[:2])  # "State|District" from "State|District|Block"
        for cat, value in row.items():
            by_district[dk][cat].append(value)

    district_stats: dict[str, dict[str, dict[str, float]]] = {}
    for dk, cats in by_district.items():
        stats: dict[str, dict[str, float]] = {}
        for cat, values in cats.items():
            if len(values) < 2:
                continue  # a standard deviation over one block is not a statistic
            stats[cat] = {
                "mean": round(statistics.fmean(values), 2),
                "std": round(statistics.pstdev(values), 2),
                "n_blocks": len(values),
            }
        if stats:
            district_stats[dk] = stats

    payload = {
        "_meta": meta(
            "Economic Census 2013 via SHRUG v2.2 (ec13_shrid.csv), households from Mission "
            "Antyodaya (antyodaya_shrid.csv)",
            "Real observations. Block = PC11 subdistrict, aggregated from village-level rows.",
            unit="enterprises per 1,000 households",
            key_type=(
                "blocks keyed 'State|District|Block', district_stats 'State|District' — matching "
                "Village.state / .district / .block"
            ),
            universe=(
                f"rural shrids only (ec13r_shrid_key.csv); blocks with at least "
                f"{MIN_BLOCK_HOUSEHOLDS} households"
            ),
            states=sorted(state_name(s) for s in wanted),
            categories=sorted(categories) or ["all"],
            method_note=(
                "'all' is the observed EC13 establishment count. Per-category figures are "
                "apportioned as count_all x (emp_shric_category / emp_all): EC13 publishes "
                "establishment counts only in total, so a category count is an estimate derived "
                "from that category's employment share, not an observed count."
            ),
        ),
        "district_stats": district_stats,
        "blocks": blocks,
    }
    write_json(args.out / "ec13_density.json", payload)
    print(f"  {len(blocks):,} blocks, {len(district_stats):,} districts")


if __name__ == "__main__":
    main()
