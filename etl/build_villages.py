"""Village records: Mission Antyodaya amenities + PC11 census + shrid polygon centroids.

Emits `villages/<CODE>.json.gz` matching `setubiz.data.loader.Village` exactly.

Sources and the division of labour between them:

* **PC11 PCA** supplies population, households, literacy, SC/ST and worker shares. Population
  deliberately comes from the census rather than Antyodaya: Antyodaya's counts are ~2019, and
  feeding them into fields named `*_2011` would double-count roughly eight years of growth on top
  of the intercensal factor in `feasibility/market_reach.py`.
* **Mission Antyodaya (2019)** supplies amenities only — bank, pucca road, electricity, and the
  market/haat/mandi flags that replace the synthetic `category="mandi"` POI rows.
* **SHRUG location names** supply name, district and subdistrict — the join that makes the
  phonetic matcher possible at all.
* **SHRUG shrid spatial statistics** supply the published centroid (`latitude`/`longitude`) and
  `tdist_*`, the distance in km to the nearest town of a given population. `dist_to_town_km` is
  therefore measured, not estimated. This replaces an earlier bounding-box centroid read out of
  the shrid GeoPackage: the published centroid is authoritative, and it makes the 874 MB .gpkg
  unnecessary.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    DATASETS,
    DEFAULT_OUT,
    PC11_STATES,
    flag,
    meta,
    num,
    progress,
    read_csv,
    resolve_state,
    state_code,
    state_id_of,
    state_name,
    write_json,
)

ANTYODAYA = DATASETS / "shrug-antyodaya-csv" / "antyodaya_shrid.csv"
PC11_KEY = DATASETS / "shrug-pc-keys-csv" / "pc11r_shrid_key.csv"
NAMES = DATASETS / "shrug-shrid-keys-csv" / "shrid_loc_names.csv"
SPATIAL = DATASETS / "shrug-shrid-keys-csv" / "shrid2_spatial_stats.csv"

#: The PCA module is still to be downloaded; accept whatever folder name it unpacks into.
PCA_GLOBS = ["shrug-pc11-csv/*pca*.csv", "shrug-pca-csv/*.csv", "shrug-*/pc11_pca*shrid*.csv",
             "shrug-*/*pca_clean_shrid*.csv"]

#: PCA column names, in preference order. SHRUG has renamed some of these between releases, so
#: the loader probes rather than assuming one spelling.
PCA_FIELDS: dict[str, list[str]] = {
    "population": ["pc11_pca_tot_p"],
    "households": ["pc11_pca_no_hh", "pc11_pca_tot_hh"],
    "literates": ["pc11_pca_p_lit"],
    "scheduled_caste": ["pc11_pca_p_sc"],
    "scheduled_tribe": ["pc11_pca_p_st"],
    "workers": ["pc11_pca_tot_work_p", "pc11_pca_tot_work"],
}

#: Which town size defines "the nearest town". 50,000 is the smallest settlement that reliably
#: has a bank branch, a wholesale market and transport links -- the things that matter to a
#: village micro-enterprise.
TOWN_DISTANCE_COLUMN = "tdist_50"

#: Antyodaya amenity columns worth carrying: each is already consumed by, or directly feeds,
#: a rule in `feasibility/swot.py` or a threat in `feasibility/threats.py`.
AMENITIES = {
    "has_bank": "is_bank_available",
    "has_pucca_road": "internal_pucca_road",
    "has_mandi": "mandi",
    "has_regular_market": "regular_market",
    "has_weekly_haat": "weekly_haat",
    "has_milk_route": "availability_of_milk_routes",
    "has_veterinary": "is_veterinary_hospital_available",
    "has_poultry_project": "availability_of_poultry_dev_proj",
    "has_cottage_industry": "availability_of_cottage_small_sc",
    "has_handloom": "is_handloom",
    "has_handicrafts": "is_handicrafts",
}
ANTYODAYA_COLS = ["shrid2", "total_hhd", "total_population", "no_electricity", "total_shg",
                  *AMENITIES.values()]


def find_one(globs: list[str]) -> Path | None:
    for g in globs:
        hits = sorted(DATASETS.glob(g))
        if hits:
            return hits[0]
    return None


def preflight() -> Path:
    """Name precisely what is missing, rather than failing on a KeyError deep inside a join."""
    missing: list[str] = []
    for path, what in ((NAMES, "shrid_loc_names.csv"), (SPATIAL, "shrid2_spatial_stats.csv")):
        if not path.exists():
            missing.append(
                f"  * {what} — SHRUG 'Shrug Location Names and Additional Keys' module (CSV).\n"
                f"    Expected at {path.relative_to(DATASETS.parent)}"
            )
    pca = find_one(PCA_GLOBS)
    if pca is None:
        missing.append(
            "  * PC11 PRIMARY CENSUS ABSTRACT — SHRUG Population Census module,\n"
            "    row '2011 Population Census Abstract', CSV, at shrid/village level.\n"
            "    Needed for households_2011, literacy_rate, sc_pct, st_pct, workers_pct.\n"
            "    (pc11r_shrid_key.csv carries only pc11_pca_tot_p.)\n"
            "    NOTE: the Village Directory (shrug-vd11-csv) is the amenities half of the\n"
            "    module and does NOT contain these columns."
        )
    if missing:
        raise SystemExit(
            "Cannot build village records — every field below is non-optional on "
            "setubiz.data.loader.Village.\n\nMissing inputs:\n" + "\n".join(missing)
        )
    return pca


def resolve_pca_columns(pca: Path) -> dict[str, str]:
    """Probe the PCA header for each needed variable; fail naming what could not be found."""
    import csv as _csv

    with pca.open(newline="", encoding="utf-8") as fh:
        header = next(_csv.reader(fh))
    found, absent = {}, []
    for field, candidates in PCA_FIELDS.items():
        hit = next((c for c in candidates if c in header), None)
        if hit:
            found[field] = hit
        else:
            absent.append(f"{field} (tried {candidates})")
    if absent:
        raise SystemExit(
            f"{pca.name} is missing expected PCA columns:\n  " + "\n  ".join(absent)
            + f"\n\nHeader was: {header[:25]}"
        )
    return found


def share(numerator: float | None, denominator: float | None) -> float:
    """A population share, clamped to [0, 1]. Returns 0.0 when the denominator is unusable."""
    if not denominator or denominator <= 0 or numerator is None:
        return 0.0
    return round(min(max(numerator / denominator, 0.0), 1.0), 4)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", default=["JH"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wanted = (set(PC11_STATES) if args.states == ["all"]
              else {resolve_state(s) for s in args.states})
    print(f"Villages for {len(wanted)} state(s): {sorted(state_name(s) for s in wanted)}")

    pca_path = preflight()
    pca_cols = resolve_pca_columns(pca_path)
    print(f"  PCA: {pca_path.name} -> {pca_cols}")

    # --- names ---
    names: dict[str, dict] = {}
    for n, row in enumerate(read_csv(NAMES, ["shrid2", "state_name", "district_name",
                                             "subdistrict_name", "village_name", "place_name"]), 1):
        progress("loc names", n)
        shrid = row["shrid2"].strip()
        if state_id_of(shrid) not in wanted:
            continue
        label = (row["village_name"] or row["place_name"] or "").strip()
        if not label:
            continue  # a village we cannot name is a village the user can never search for
        names[shrid] = {
            "name": label.title(),
            "district": (row["district_name"] or "").strip().title(),
            "block": (row["subdistrict_name"] or "").strip().title(),
        }
    print(f"  {len(names):,} named villages")

    # --- centroids and town distance ---
    geo: dict[str, dict] = {}
    for n, row in enumerate(read_csv(SPATIAL, ["shrid2", "latitude", "longitude",
                                               TOWN_DISTANCE_COLUMN]), 1):
        progress("spatial stats", n)
        shrid = row["shrid2"].strip()
        if shrid not in names:
            continue
        lat, lon = num(row["latitude"]), num(row["longitude"])
        if lat is None or lon is None:
            continue
        geo[shrid] = {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "dist_to_town_km": round(num(row[TOWN_DISTANCE_COLUMN], 0.0) or 0.0, 2),
        }
    print(f"  {len(geo):,} with centroid + town distance")

    # --- census demography ---
    census: dict[str, dict] = {}
    cols = ["shrid2", *pca_cols.values()]
    for n, row in enumerate(read_csv(pca_path, cols), 1):
        progress("pca", n)
        shrid = row["shrid2"].strip()
        if shrid not in geo:
            continue
        pop = num(row[pca_cols["population"]], 0.0) or 0.0
        if pop <= 0:
            continue  # an uninhabited village has no shares to compute
        census[shrid] = {
            "population_2011": int(pop),
            "households_2011": int(num(row[pca_cols["households"]], 0.0) or 0.0),
            "literacy_rate": share(num(row[pca_cols["literates"]]), pop),
            "sc_pct": share(num(row[pca_cols["scheduled_caste"]]), pop),
            "st_pct": share(num(row[pca_cols["scheduled_tribe"]]), pop),
            "workers_pct": share(num(row[pca_cols["workers"]]), pop),
        }
    print(f"  {len(census):,} with PCA demography")

    # --- amenities ---
    amenity: dict[str, dict] = {}
    for n, row in enumerate(read_csv(ANTYODAYA, ANTYODAYA_COLS), 1):
        progress("antyodaya", n)
        shrid = row["shrid2"].strip()
        if shrid not in census:
            continue
        rec = {field: flag(row[col]) for field, col in AMENITIES.items()}
        rec["has_power"] = not flag(row["no_electricity"])  # stored inverted upstream
        rec["self_help_groups"] = int(num(row["total_shg"], 0.0) or 0.0)
        rec["population_survey_2019"] = int(num(row["total_population"], 0.0) or 0.0)
        amenity[shrid] = rec
    print(f"  {len(amenity):,} with Antyodaya amenities")

    # --- assemble, sharded by state ---
    by_state: dict[str, list[dict]] = {s: [] for s in wanted}
    no_amenities = 0
    for shrid, name_row in names.items():
        if shrid not in geo or shrid not in census:
            continue
        am = amenity.get(shrid)
        if am is None:
            # Antyodaya is rural-only and not exhaustive; keep the village, flag the gap, and
            # let the amenity booleans default to False rather than inventing a bank.
            no_amenities += 1
            am = {f: False for f in AMENITIES} | {
                "has_power": False, "self_help_groups": 0, "population_survey_2019": 0}
        by_state[state_id_of(shrid)].append({
            "shrid": shrid,
            "name": name_row["name"],
            "name_hi": None,  # no Devanagari source in SHRUG; the matcher transliterates input
            "state": state_name(state_id_of(shrid)),
            "district": name_row["district"],
            "block": name_row["block"],
            **geo[shrid],
            **census[shrid],
            **am,
        })

    for sid, rows in by_state.items():
        if not rows:
            print(f"  {state_name(sid)}: no rows, skipped")
            continue
        rows.sort(key=lambda r: r["shrid"])
        write_json(
            args.out / "villages" / f"{state_code(sid)}.json",
            {
                "_meta": meta(
                    "Census 2011 PCA + SHRUG location names and spatial statistics (v2.2), "
                    "amenities from Mission Antyodaya",
                    "Real observations.",
                    state=state_name(sid),
                    census_year="2011",
                    amenities_year="2019",
                    villages=len(rows),
                    without_amenity_row=no_amenities,
                    method_note=(
                        "Population and households are Census 2011 PCA, so the intercensal "
                        "factor in feasibility/market_reach.py still applies. Amenity flags are "
                        "Mission Antyodaya ~2019 and are NOT scaled. dist_to_town_km is SHRUG "
                        f"{TOWN_DISTANCE_COLUMN}: measured km to the nearest town of 50,000+."
                    ),
                ),
                "villages": rows,
            },
            compress=True,
        )
        print(f"  {state_name(sid)}: {len(rows):,} villages")


if __name__ == "__main__":
    main()
