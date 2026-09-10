"""Village records: Mission Antyodaya amenities + PC11 census + shrid polygon centroids.

Emits `villages/<CODE>.json.gz` matching `setubiz.data.loader.Village` exactly.

Sources and the division of labour between them:

* **PC11 PCA** supplies population, households, literacy, SC/ST and worker shares. Population
  deliberately comes from the census rather than Antyodaya: Antyodaya's counts are ~2019, and
  feeding them into fields named `*_2011` would double-count roughly eight years of growth on top
  of the intercensal factor in `feasibility/market_reach.py`.
* **Mission Antyodaya (2019)** supplies amenities only — bank, pucca road, electricity, and the
  market/haat/mandi flags that replace the synthetic `category="mandi"` POI rows.
* **Shrid polygons** supply the centroid. Read straight out of the GeoPackage's R-tree index with
  stdlib sqlite3, so no geopandas/fiona dependency: the R-tree stores each feature's bounding box,
  and a village polygon's bbox centre is within a few tens of metres of its true centroid. That
  approximation is recorded in `_meta`.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
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
POLY_DIR = DATASETS / "shrug-shrid-poly-gpkg"

#: Candidate locations for the two modules that are not downloaded yet. Each is a (glob, why)
#: pair; the preflight prints the missing ones with the exact module to fetch.
NAMES_GLOBS = ["shrug-names-csv/*.csv", "shrug-keys-csv/*name*.csv", "shrug-*/shrid_names*.csv"]
PCA_GLOBS = ["shrug-pc11-pca-csv/*.csv", "shrug-pca-csv/*.csv", "shrug-*/pc11_pca*.csv"]

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


def preflight() -> tuple[Path | None, Path | None, Path | None]:
    """Report precisely which inputs are missing, rather than failing on a KeyError deep in a join."""
    names = find_one(NAMES_GLOBS)
    pca = find_one(PCA_GLOBS)
    gpkg = next(iter(sorted(POLY_DIR.glob("*.gpkg"))), None) if POLY_DIR.exists() else None

    missing: list[str] = []
    if names is None:
        missing.append(
            "  * VILLAGE NAMES — SHRUG 'Keys / Location Names' module.\n"
            "    Needed for Village.name / .district / .block and the entire phonetic matcher.\n"
            "    Expected at datasets/shrug-names-csv/*.csv"
        )
    if pca is None:
        missing.append(
            "  * PC11 PRIMARY CENSUS ABSTRACT — SHRUG 'Population Census' PCA module.\n"
            "    Needed for literacy_rate, sc_pct, st_pct, workers_pct.\n"
            "    (pc11r_shrid_key.csv carries only pc11_pca_tot_p.)\n"
            "    Expected at datasets/shrug-pc11-pca-csv/*.csv"
        )
    if gpkg is None:
        missing.append(
            "  * SHRID POLYGONS — SHRUG 'Open Polygons' module, GPKG format.\n"
            "    Needed for lat/lon. The current datasets/shrug-shrid-poly-gpkg/ holds only\n"
            "    README.md and open_poly.bib — the .gpkg itself never downloaded.\n"
            "    Expected at datasets/shrug-shrid-poly-gpkg/*.gpkg"
        )
    if missing:
        raise SystemExit(
            "Cannot build village records — every field below is non-optional on "
            "setubiz.data.loader.Village.\n\nMissing inputs:\n" + "\n".join(missing)
        )
    return names, pca, gpkg


def centroids(gpkg: Path, wanted: set[str]) -> dict[str, tuple[float, float]]:
    """Bounding-box centres from the GeoPackage R-tree. Stdlib sqlite3 only — see module docstring."""
    con = sqlite3.connect(f"file:{gpkg}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT table_name FROM gpkg_contents WHERE data_type='features'")]
        if not tables:
            raise SystemExit(f"{gpkg.name} has no feature tables")
        table = tables[0]
        geom_col = con.execute(
            "SELECT column_name FROM gpkg_geometry_columns WHERE table_name=?", (table,)
        ).fetchone()[0]
        pk = con.execute(f"SELECT name FROM pragma_table_info('{table}') WHERE pk=1").fetchone()[0]

        out: dict[str, tuple[float, float]] = {}
        rows = con.execute(
            f'SELECT t."shrid2", (r.minx+r.maxx)/2.0, (r.miny+r.maxy)/2.0 '
            f'FROM "{table}" t JOIN "rtree_{table}_{geom_col}" r ON r.id = t."{pk}"'
        )
        for shrid, lon, lat in rows:
            s = (shrid or "").strip()
            if s and state_id_of(s) in wanted:
                out[s] = (round(float(lat), 6), round(float(lon), 6))
        return out
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="*", default=["JH"])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    wanted = (set(PC11_STATES) if args.states == ["all"]
              else {resolve_state(s) for s in args.states})
    print(f"Villages for {len(wanted)} state(s): {sorted(state_name(s) for s in wanted)}")

    names_file, pca_file, gpkg = preflight()

    # --- amenities (Mission Antyodaya 2019) ---
    amenity: dict[str, dict] = {}
    for n, row in enumerate(read_csv(ANTYODAYA, ANTYODAYA_COLS), 1):
        progress("antyodaya", n)
        shrid = row["shrid2"].strip()
        if state_id_of(shrid) not in wanted:
            continue
        rec = {field: flag(row[col]) for field, col in AMENITIES.items()}
        rec["has_power"] = not flag(row["no_electricity"])  # stored inverted upstream
        rec["self_help_groups"] = int(num(row["total_shg"], 0.0) or 0.0)
        rec["population_survey_2019"] = int(num(row["total_population"], 0.0) or 0.0)
        amenity[shrid] = rec
    print(f"  {len(amenity):,} villages with Antyodaya amenities")

    # --- census population + household counts (PC11) ---
    census: dict[str, dict] = {}
    for n, row in enumerate(read_csv(PC11_KEY, ["shrid2", "pc11_pca_tot_p", "pc11_land_area"]), 1):
        progress("pc11 key", n)
        shrid = row["shrid2"].strip()
        if state_id_of(shrid) in wanted:
            census[shrid] = {
                "population_2011": int(num(row["pc11_pca_tot_p"], 0.0) or 0.0),
                "land_area_2011": num(row["pc11_land_area"]),
            }
    print(f"  {len(census):,} villages with PC11 population")

    geo = centroids(gpkg, wanted)
    print(f"  {len(geo):,} villages with centroids")

    # `names_file` and `pca_file` join in here on shrid2 once the modules are downloaded;
    # preflight() guarantees they exist by this point.
    raise SystemExit(
        "Join stubs for names/PCA are not written yet — rerun once preflight passes so the real "
        f"column layout of {names_file.name} and {pca_file.name} can be read rather than guessed."
    )


if __name__ == "__main__":
    main()
