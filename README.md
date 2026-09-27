# SetuBiz

AI-driven hyper-local business advisory and financial structuring assistant for rural
micro-entrepreneurs — SIH 2026, Problem Statement SIH26091 (Ministry of Social Justice &
Empowerment).

**Master plan:** [`PLAN.md`](./PLAN.md) — scheme research, model specs, data plan, demo strategy.
**Coverage:** [`docs/PRD-COVERAGE.md`](./docs/PRD-COVERAGE.md) — what is built, partial, and missing.

> **Core rule.** ML only where the data is genuinely uncertain (competitor density, local
> demand). Every financial calculation and eligibility decision is deterministic code. The
> language model explains — it never decides.

## The one idea

The problem statement's own formula — `Project Cost = Margin ÷ 10%` — computes the **maximum**
loan a beneficiary may take. That is exactly the mechanism behind the business failures the
ministry wants to prevent.

SetuBiz computes the loan the business can actually **service**: NABARD appraisal standard
DSCR ≥ 1.5, stress-tested at −15% and −30% revenue, capped by the scheme ceiling and by what
the unit actually costs. Both numbers are shown side by side with the binding constraint named.

Demo persona — a Ranchi village, ₹1,00,000 of savings, a 2-animal dairy unit:

| | |
|---|---|
| Loan the scheme formula permits | **₹9,00,000** — worst-year DSCR **0.52** |
| Loan the cash flow can service | **₹2,05,000** — worst-year DSCR **2.30**, limited by the −15% stress case |
| What the unit actually costs | ₹4,10,800, of which ₹3,10,800 needs borrowing |

The uncomfortable part is reported too: cash flow supports ₹2.05 L against a ₹3.11 L need, so
the honest advice is a smaller unit or a larger promoter contribution — not a bigger loan.

## Run it

```bash
make setup     # venv + backend install + npm install
make test      # 170 tests; decision layer must hold 100% coverage
make api       # http://localhost:8000  (docs at /docs)
make web       # http://localhost:5173
```

No API key, no network, no database. If port 8000 is taken: `make api PORT=8010`, then
`SETUBIZ_API=http://localhost:8010 make web`.

Without a browser:

```bash
setubiz advise --village "Ormanji" --savings 100000 --category dairy --income 280000 --lang hi
setubiz match "ओरमांझी"          # what the phonetic matcher would offer for confirmation
setubiz templates                # NABARD-style unit economics
```

`make demo` boots the whole thing under Docker Compose.

### Deploying to Vercel

One project serves both halves: the Vite build is the static output, `api/index.py` runs the
FastAPI app as a Python function. No secrets to set — the LLM lanes are off by default and the
sample data is committed.

```bash
npx vercel login
npx vercel        # preview
npx vercel --prod
```

Smoke-test the function before trusting the UI: `curl https://<deployment>/api/v1/cost-templates`
should return five templates. `/docs` and `/healthz` are not routed here; the SPA owns
everything outside `/api`.

## What is built

| Layer | Status |
|---|---|
| **Decision — finance** (`setubiz/finance`) | Complete. Logic A/B router with the real NSFDC caps, quarterly amortization in both moratorium treatments, DSCR right-sizing, stress tests, NABARD-style cost templates. 100% test coverage, golden vectors asserted to the paisa. |
| **Decision — eligibility** (`setubiz/eligibility`) | Complete. SC→NSFDC (₹5 L ceiling, w.e.f. 07-01-2026), safai karamchari→NSKFDC (no ceiling), OBC/EBC→NBCFDC (₹3 L). Verdict, conditions, bilingual document checklist, SCA address, PM-DAKSH handoff, comparison cards. 100% coverage. |
| **Estimation** (`setubiz/feasibility`) | v0 deterministic. Competitor density from EC13 block z-scores floored by observed OSM POIs; demand from published HCES shares as a band; seasonality from mandi arrivals; SWOT from a YAML rule library. Every estimate is a **band with a stated method**, never a bare number. |
| **Data** (`setubiz/data/real`, built by `etl/`) | Real. Census 2011 PCA + SHRUG v2.2 names and centroids + Mission Antyodaya amenities (29,480 Jharkhand villages, totalling to the published rural census figure within 0.003%); Economic Census 2013 density split by SHRIC industry code; HCES 2023-24 consumption for 29 states; OpenStreetMap POIs. `data/sample/` remains as a synthetic fallback and declares itself so. |
| **Facts contract** (`setubiz/facts`) | Complete. One frozen object holds every quotable figure plus a `provenance` map from figure → source. Tested: no indexed number may exist without a registered source. |
| **Language** (`setubiz/narration`) | Three lanes, tried in order: cloud LLM, local Llama 3.1 8B via llama.cpp, template. The template lane (Jinja, en + hi) is the default and needs nothing. Every lane paraphrases the deterministic draft and is checked by the numeric-grounding validator. |
| **API / CLI / PWA** | FastAPI at `/api/v1`, a Typer CLI, and a React + Vite + Tailwind app: red-vs-green hero, DSCR and seasonality charts, quarterly schedule, sticky contents rail with scroll-spy on desktop, bilingual and light/dark toggles, provenance panel. |

## Offline narration lane (Llama 3.1 8B)

The answer to "what if the network dies at the venue". Off by default; the weights are a
~4.7 GB download this repo does not ship:

```bash
pip install -e ".[local]"
export SETUBIZ_LOCAL_LLM_ENABLED=1
export SETUBIZ_LOCAL_LLM_MODEL_PATH=~/models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
```

Output is constrained by a **GBNF grammar** generated from the report's own section ids, so a
non-section response cannot be sampled at all. It then goes through the same numeric-grounding
validator as every other lane. Without the runtime or the weights the lane reports itself
unavailable and the template narrator serves, so enabling it can never make the demo worse.
`/api/v1/metrics` shows which lane would serve the next request.

**Unverified:** generation quality on the real model has not been observed here. The grammar,
the availability gate, the retry loop and the fallback are tested; the model is not.

## What is not built yet

Full matrix in [`docs/PRD-COVERAGE.md`](./docs/PRD-COVERAGE.md). The short version:

- **Models ①–④ are not trained.** `LightgbmDensityEstimator` is registered and raises
  `NotImplementedError` with a pointer to PLAN.md §3 — it needs Udyam labels whose granularity
  is still unverified. Local demand uses a state mean ± CV, not Fay–Herriot small-area
  estimation. No intent/slot classifier; no price-seasonality model beyond the arrivals index.
- **Mandi seasonality has no history.** The data.gov.in AGMARKNET resource publishes only the
  current day's prices, so the 12-month arrivals series behind the seasonality index needs a
  portal export from agmarknet.gov.in. Until then `threats.assess` drops the seasonality threat
  rather than inventing one, and the chart does not render.
- **One state so far.** The dataset ships Jharkhand (29,480 villages). The ETL is national —
  `python etl/build_villages.py --states BR OD WB` adds more — but each state costs an Overpass
  pass for its POIs.
- **`poultry` has no Economic Census density.** SHRIC has no livestock-rearing code, so the
  competitor estimate falls back to the observed OSM floor and says so in the report.
- **No ASR/TTS.** The mic button uses the browser Web Speech API and degrades to typing. The
  Indic ASR / Bhashini lane is not wired.
- **No PostGIS, no pgvector, no RAG, no ministry dashboard.** Geography is haversine over
  committed rows behind a `DataSource` protocol; swapping in PostGIS touches only
  `data/loader.py`.
- **No server-side PDF.** The bank handout uses a print stylesheet (browser print-to-PDF).
  WeasyPrint needs GTK native dependencies and is painful on Windows; a `/report/pdf` route is
  the documented next step.
- **No business-failure classifier**, deliberately: no labelled dataset of failed rural
  micro-enterprises exists. We stress-test the cash flow instead and show where it breaks.

## Anti-hallucination, and its honest limit

Three layers, in order:

1. **Structured output** — the LLM lane constrains generation with `output_config.format`, so a
   schema-invalid response is impossible.
2. **Numeric grounding** — every figure in the prose must exist in `facts.numeric_index` or a
   locked table. Tolerance is derived from how precisely the figure was written (`₹44,729`
   tolerates ₹0.50, `₹14.33 L` tolerates ₹500). Failures trigger regeneration; the catch rate
   is served at `/api/v1/metrics`.
3. **Verdict fidelity** — eligibility and loan verdicts are copied from the facts object, never
   restated by the model.

**The limit, stated before it is asked:** layer 2 catches *invented* numbers, not *misattributed*
ones. A figure lifted from row 14 of the repayment schedule and captioned as something else is
grounded and passes. That is what layer 3 is for.

The template narrator is put through the same validator, and the suite asserts it passes on
every category in both languages — which is what makes the catch-rate figure meaningful for
the LLM lane.

## Layout

```
backend/setubiz/
  money.py schemas.py config.py geo.py     Decimal money, shared value objects, settings
  finance/      router · amortization · rightsizing · cost_templates     deterministic
  eligibility/  rules                                                    deterministic
  feasibility/  market_reach · competitors · demand · threats · swot      estimation (bands)
  facts/        builder · provenance                                     the locked contract
  narration/    template_narrator · validator · llm_narrator             explains, never decides
  matching/     village_matcher                                          Indic phonetic matching
  data/         loader + sample/                                         swappable DataSource
  api/ cli.py
frontend/src/   pages/{Ask,Report} · components/*                        React + Vite + Tailwind
```

Charts are hand-rolled SVG against a CVD-validated palette — no charting dependency, 60 KB
gzipped JS plus 6 KB CSS, which matters on a rural connection. Open Sans and Noto Sans
Devanagari are self-hosted per subset, so nothing is fetched from a CDN and an English session
never downloads the ~100 KB of Devanagari faces.

The report serves two audiences at once: a sticky contents rail with scroll-spy, the
recommended loan and the binding constraint pinned beside it on desktop; the same nav as a
scrolling chip row on a phone; and a print stylesheet that re-stamps the light palette, so a
dark-mode viewer's PDF is black on white.
