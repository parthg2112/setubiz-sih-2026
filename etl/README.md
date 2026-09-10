# Dataset ETL

Turns the multi-gigabyte extracts in `datasets/` (gitignored) into the small, committed files
under `backend/setubiz/data/real/`.

Nothing here is imported by the application. The seam is the on-disk schema, which is identical to
the one `SampleDataSource` already reads — so switching the app to real data is one env var:

```bash
SETUBIZ_DATA_DIR=backend/setubiz/data/real make api
```

## Status

| Output | State | Source |
|---|---|---|
| `ec13_density.json` | **real** | Economic Census 2013 via SHRUG `ec13_shrid.csv`, households from Mission Antyodaya |
| `hces_demand.json` | **real** | HCES 2023-24 Fact Sheet, Statements 4 & 7 and Figure 1R |
| `pois/<ST>.json.gz` | **real** | OpenStreetMap via Overpass |
| `arrivals.json` | live prices only | data.gov.in; needs a personal key and a portal history export |
| `villages/<ST>.json.gz` | **blocked** | needs three SHRUG modules — run `build_villages.py` for the list |
| `schemes/`, `cost_templates/`, `swot_rules.yaml` | real already | copied from `data/sample/`, unchanged |

## Commands

```bash
cd etl
python3 build_ec13_density.py --states JH            # or: --states all
python3 build_hces_demand.py                         # all states in one file
python3 fetch_pois.py       --states JH --pause 3    # ~2.5 min per category, cached
python3 fetch_arrivals.py   --states JH [--history agmarknet_export.csv]
python3 build_villages.py   --states JH              # prints exactly what is still missing
```

`--states` accepts PC11 ids (`20`), two-letter codes (`JH`) or names (`Jharkhand`); `all` does
every state. Overpass responses are cached under `etl/.cache/`, so re-runs are free.

## Honesty constraints encoded here

These are deliberate and should survive refactors:

* **EC13 has no per-industry establishment counts.** Only `ec13_count_all` plus 90
  `ec13_emp_shric_*` *employment* columns. A per-category count can therefore only be apportioned
  as `count_all x (emp_shric_cat / emp_all)`, and the emitted `method_note` says so. The category
  split is gated on the SHRUG "SHRIC Industry Code" module and stays off until it is downloaded —
  guessing which of 90 codes means "dairy" is not acceptable.
* **EC13 covers rural and urban; Mission Antyodaya is rural-only.** Mixing them puts a town's
  establishments over a handful of rural households. The numerator is restricted to the rural
  shrid set from `ec13r_shrid_key.csv`. Before this fix the worst Jharkhand block read 5,912
  enterprises per 1,000 households; after it, 773, with a median of 49.
* **Population comes from PC11, not Antyodaya.** Antyodaya's counts are ~2019; feeding them into
  fields named `*_2011` would double-count growth already applied by `intercensal_growth`.
  Antyodaya supplies amenities only.
* **`addressable_share` in `hces_demand.json` is an assumption** and ships its own rationale
  string. `share_of_mpce` and `cv` are not assumptions — the first is published, the second is
  computed from the published rural MPCE distribution.
* **Rural OSM coverage is very sparse.** All of Jharkhand has 120 mapped POIs across the six
  categories: 87 kirana, 23 marketplaces, 7 dairy, 2 poultry, 1 tailor, 0 flour mills. This is
  why `feasibility/competitors.py` treats an observed count as a floor and never as a census.
* **The AGMARKNET API is a daily snapshot, not a history.** The seasonality index needs 12 months,
  which must be exported from the portal and passed with `--history`. Without it the file carries
  no `series` and `threats.assess` drops the seasonality threat rather than inventing one.
