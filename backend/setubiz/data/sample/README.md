# Sample data — synthetic placeholders

**Every file in this directory is synthetic.** The numbers are *shaped* like the real sources so
the pipeline, the schemas and the demo work offline, but they are **not real observations and must
never be quoted as findings** — not in the deck, not in the report, not to a judge.

The report layer marks every fact sourced from here with `"synthetic": true`, and the provenance
panel shows it. Do not remove that flag until a file is replaced with real data.

| File | Shaped like | Real source to swap in |
|---|---|---|
| `villages.json` | Census 2011 PCA village records joined on `shrid` | SHRUG v2.2 (`shrug_pc11`, village polygons) — <https://www.devdatalab.org/shrug> |
| `pois.json` | OSM Overpass node dump | Overpass API, `shop=*` / `craft=*` / `amenity=marketplace` |
| `ec13_density.json` | Economic Census 2013 block activity densities | SHRUG EC13 tables; Udyam registry once granularity is verified |
| `hces_demand.json` | HCES 2023-24 per-category consumption shares | microdata.gov.in catalogue 237 (registration required) |
| `arrivals.json` | AGMARKNET monthly arrivals and modal prices | data.gov.in resource `9ef84268-d588-465a-a308-a864a43d0070` |
| `cost_templates/*.yaml` | NABARD Model Bankable Project unit economics | NABARD model project reports (these are the closest to real — the line items and ratios follow published norms) |
| `schemes/*.yaml` | MoSJE corporation scheme parameters | **These ARE real.** Rates, caps, tenures and ceilings are transcribed from the official portals; each entry carries its `source` URL. |

## Swapping in real data

`setubiz/data/loader.py` defines the `DataSource` protocol. `SampleDataSource` reads this
directory. A real implementation (`ShrugDataSource`, `OverpassDataSource`, …) satisfies the same
protocol, so nothing downstream of the loader changes.

The only exception is `schemes/` — that is reference data, not sample data, and it is already real.
