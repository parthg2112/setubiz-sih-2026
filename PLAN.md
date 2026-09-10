# SetuBiz — Master Plan (v2, merged)

**SIH 2026 · Problem Statement SIH26091** — AI-Driven Hyper-Local Business Advisory and Financial Structuring Assistant for Rural Micro-Entrepreneurs
**Organization:** Ministry of Social Justice and Empowerment (MoSJE) · Software · Agriculture, FoodTech & Rural Development
**Status:** Approved working plan · 2026-09-06 · **Idea submission deadline: 20 September 2026**

> Merged from: (a) verified external research pass, (b) team's `SIH26091_Models_Architecture_Workflow.docx`, (c) team's `SIH26091_Architecture_Summary_1Page.docx`. Conflict resolutions are marked ⚖️.

---

## 0. Verified research findings that shape the build (Sep 2026)

1. **The PS's Logic A/B are copied verbatim from real MoSJE/NSFDC schemes:**
   - **Micro Finance Scheme** — units ≤ ₹1.40 L; NSFDC finances 90% (max loan **₹1.25 L**); beneficiary rate **6.5%**; repayment ≤ 3 years in **quarterly instalments**; **3-month moratorium inside the 3-year window**. Source: <https://www.dosje.gov.in/schemes-and-services/micro-finance-scheme/>
   - **Term Loan Scheme** — units > ₹1.40 L to ₹50.00 L; 90% loan (max **₹45 L**); beneficiary rate **8.0%**; **quarterly instalments within 7 years**; **6-month moratorium (12 months for plantation/construction)**. Source: <https://www.dosje.gov.in/schemes-and-services/2998/>
   - The "10% margin" = promoter contribution. Loan flow: **NSFDC → State Channelizing Agency (SCA) @2.5%/4% → beneficiary**. Our product must speak NSFDC/SCA language natively — the single biggest "we understand the ministry" signal.
2. **Category-aware routing:** NSFDC (Scheduled Castes; family income ceiling **raised to ₹5 L w.e.f. 2026-01-07** — PIB), NSKFDC (safai karamcharis & dependents; **no income ceiling**), NBCFDC (OBC/EBC; **₹3 L** ceiling, loans to ₹15 L @85%). All via SCAs/RRBs/banks.
3. **Census 2027 is underway** (Phase 1 house-listing from April 2026) → 2011 village data + intercensal scaling is the story every data-grounded team must tell. Source: <https://www.pib.gov.in/PressNoteDetails.aspx?id=154867>
4. **SHRUG v2.2** (devdatalab.org/shrug — take v2.2, NOT v1.5; IDs don't match): village polygons + Census PCA/VD + Economic Census 2013 + Mission Antyodaya + night lights, all joined on one `shrid`. Solves village coordinates AND EC13 competitor ground truth.
5. **AGMARKNET** live API on data.gov.in (resource `9ef84268-d588-465a-a308-a864a43d0070`, 3,000+ mandis, free key) — prices **and arrivals** (arrivals = seasonality signal for Threats).
6. **LGD** (<https://lgdirectory.gov.in/>, 658k inhabited villages; LGD↔pincode on data.gov.in) — official geo join key alongside shrid.
7. **Bhashini** (bhashini.gov.in; org registration → ASR/TTS/translation, 22 languages) — cloud fallback for the voice layer.
8. **SIH judging:** novelty, complexity, clarity, feasibility, practicability, sustainability, scalability + live demo & code walkthrough; evaluators actively penalize "AI-generated slop." Every number must be **computed deterministically, never LLM-generated**.

---

## 1. Product thesis

Voice-first advisor for a rural first-time entrepreneur. They **speak** their village, savings, and business idea. They get back: is there room in this market, **how much should they actually borrow**, which scheme fits, and what to carry to the bank.

**The one idea that wins: capacity to borrow ≠ capacity to repay.** The PS formula (Project Cost = Margin ÷ 10%) computes the *maximum* loan — exactly the mechanism causing the business failures the ministry complains about. We compute the **right-sized** loan (NABARD appraisal standard **DSCR ≥ 1.5**, stress-tested at −15% / −30% revenue) and show the difference.

**Modes:** (a) self-serve voice PWA, (b) **assisted VLE/CSC operator mode** (real deployment path), (c) **ministry policy dashboard** (block-level demand–supply heatmap, scheme-fit funnel, NSFDC pipeline).

**Pilot geography** ⚖️: Ranchi district, Jharkhand (ground-truth validation there); Maharashtra optional second.

---

## 2. Layered architecture

| Layer | Responsibility | Built with |
|---|---|---|
| **Estimation** (ML — only where data is genuinely uncertain) | Competitors nearby; local demand | Trained models (below) |
| **Decision** (deterministic — no ML) | Loan structuring, right-sizing, eligibility, stacking, stress tests | Pure Python rule engines |
| **Language** (pretrained — explains, never decides) | Narration, translation, speech, scheme Q&A | ASR/TTS/LLM/RAG |

```
VOICE IN (village | savings | idea | language)
  → Silero VAD → ASR → Intent+Slot classifier → phonetic village matcher
  → GEO: shrid lookup → villages within 10 km (PostGIS)   [isochrone = stretch]
  → DATA: SHRUG (PCA11+EC13+polygons) | OSM Overpass | HCES | NABARD templates
  → ESTIMATION: ① competitor density  ② local demand  (④ price seasonality, stretch)
  → DECISION: financial engine (cost, EMI, right-size, stress) + rule engine + stacking
  → FACTS: locked facts.json — single source of truth for every number
  → LANGUAGE: BGE-M3 → pgvector → reranker → LLM (GBNF grammar + numeric validation)
  → OUT: on-screen report with citations | TTS read-aloud | PDF bank handout | dashboard
```

---

## 3. Models we train (each reports a metric vs an explicit baseline)

| # | Model | Spec | Baseline to beat |
|---|------|---|---|
| ① | **Competitor Density Estimator** ★ flagship | LightGBM; target log(enterprises/1k households); labels = Udyam district×activity counts; features = OSM POIs + census (households, literacy, workers, SC/ST, road/bank/power, dist-to-town); ≈5–7k rows; **hold out entire states**; predict density → × village households (never raw counts) | Raw OSM count. **v0 deterministic fallback = SHRUG EC13 block-density z-scores** (demo-safe if Udyam granularity check fails) |
| ② | **Local Demand Estimator** | HCES 2023-24 microdata (microdata.gov.in cat. 237); regression MVP, cite Fay–Herriot small-area estimation; output rupees/household/month as a **band** | State average applied uniformly |
| ③ | **Intent + Slot classifier** | IndicBERT/LaBSE embeddings + logistic/MLP; ~200 hand-labelled Hindi/English phrases; slots: category, margin, village, caste category, state | Keyword matching |
| ④ | Price seasonality (stretch) | SARIMA/Prophet on AGMARKNET arrivals/prices — the seasonality chart is the deliverable | Seasonal-naive |

**Pretrained (no training):** Silero VAD · IndicConformer/IndicWhisper ASR (INT8) · Indic-TTS/Piper · BGE-M3 embeddings · bge-reranker-v2-m3 · narration LLM ⚖️ **cloud API primary (Gemini/Groq) + Llama 3.1 8B Instruct Q4_K_M local fallback lane** for the offline/CSC story. (Docx said Llama-8B in one file and "Qwen3.5-9B" in the other — the Qwen designation is unverified; do not put it in the deck.)

**Deliberately NOT ML (say so in the deck):** EMI/loan math, eligibility verdicts, scheme stacking, stress tests — auditable code. **No business-failure classifier** (no labelled data exists; we stress-test instead — volunteer this answer before it's asked).

**Anti-hallucination (3 layers):** GBNF grammar-constrained decoding (schema-invalid output structurally impossible) → numeric grounding (every number must exist in facts.json or a retrieved chunk, else regenerate) → verdict fidelity (eligibility must match rule engine 100%). **Log and present the catch rate** (e.g., "validator caught 4.2% of generations").

**Facts object:** locked JSON — households-within-10km, TAM band, competitors low/high, gap, seasonality, price band, required_capital, max_loan, recommended_loan, EMI both, scheme, eligibility, sources[] — the LLM may not introduce any figure outside it.

---

## 4. Module 1 — hyper-local feasibility (6 PS parameters)

| Parameter | Method | Data |
|---|---|---|
| Market Reach | Σ village populations within radius (2011 × district intercensal growth), income-segmented; channels = mandis/haats/bus routes | SHRUG PCA11, WorldPop, OSM |
| Opportunity Analysis | Activity-density z-scores vs district mean; under-served NIC/SHRIC categories | SHRUG EC13 (+Udyam later) |
| SWOT | Budget-banded rule library over computed metrics; LLM narrates only | all |
| Threats | Arrivals seasonality index (AGMARKNET), monsoon dependency, single-buyer/mandi flags, flood/drought layers | AGMARKNET, IMD, NDMA |
| Competitor Mapping | Model ① estimate (band) + OSM POI heatmap on MapLibre | OSM/Overpass, EC13 |
| Product Market Value | Price bands from mandi spreads × purchasing power (Model ②) → recommended price point | AGMARKNET, HCES |

Report pipeline: engine emits `facts.json` → LLM narrates with citations → JSON-validated bilingual HTML/PDF with per-section **data provenance footers**; offline fallback = template-only report.

---

## 5. Module 2 — financial structuring engine (deterministic, 100% test coverage)

**Router (PS rules primary, NSFDC facts encoded):**
- Margin M → Project P = M / 0.10 → Loan L = 0.9·P, **caps: ₹1.25 L (A) / ₹45 L (B)**.
- Logic A: P ≤ ₹1.40 L → 6.5%, 3 yr quarterly, 3-month moratorium (inside window).
- Logic B: ₹1.40 L < P ≤ ₹50 L → 8.0%, 7 yr quarterly, 6-month moratorium (12 mo plantation/construction).
- Edge cases: M < ₹14k → only A viable; M > ₹5 L → beyond scheme → referral + PMEGP/MUDRA comparison.

**Quarterly amortization:** EMI_q = L·r(1+r)ⁿ / ((1+r)ⁿ−1), r = annual/4; moratorium interest mode configurable (serviced quarterly vs capitalized), both displayed.

**Golden unit-test vectors:**
- B: M = ₹1,00,000 → P = ₹10,00,000, L = ₹9,00,000; r = 2%/q; moratorium 2 q → 26 instalments ≈ **₹44,729/q**; total interest ≈ ₹2.63 L.
- A: P = ₹1,40,000 → L = **₹1,25,000 (capped, not ₹1.26 L)**; r = 1.625%/q; moratorium 1 q → 11 instalments ≈ ~~₹12,471/q~~ → **corrected to ₹12,501.34/q** under the r = annual/4 convention that vector B matches to the paisa. See README §"Correction to PLAN.md §5". Do not quote ₹12,471.
- Boundary: M = ₹14,000 → A; M = ₹14,001 → B; M = ₹5,00,000 → B (P = ₹50 L); M = ₹5,00,001 → out of scope.

**Right-sizing (flagship):** NABARD cost templates → required_capital, monthly revenue/opex → DSCR per loan year, threshold **1.5** (configurable) → **recommended loan ≤ max loan**; stress at −15%/−30%; UI shows Max (red) vs Recommended (green). Example: dairy template ₹4.1 L required vs ₹10 L borrowable; at ₹9 L loan the base case fails DSCR — the demo moment.

**Scheme router enrichment:** category (SC / Safai Karamchari / OBC-EBC / Women) → income-ceiling check (₹5 L / none / ₹3 L) → eligibility verdict + document checklist + **state SCA list + PM-DAKSH handoff**; comparison toggle: PMMY, PMEGP, CGTMSE, DRI, Stand-Up India.

---

## 6. Data plan

**Now (blocks everything):** SHRUG v2.2 (Ranchi first) · OSM Overpass POIs · NABARD Model Bankable Projects (cost templates with BCR/IRR/repayment) · scheme PDFs from **official portals only** (NSFDC/NSKFDC/NBCFDC first — they ARE the PS logic — then PMMY, CGTMSE, PMEGP, PMFME, SVANidhi, Stand-Up India) · **first task: verify Udyam API granularity (pincode + activity?) — decides Model ① design.**

**Week 2:** HCES 2023-24 microdata (register immediately — approval lag; factsheet rural MPCE ₹4,122) · SHRIC ↔ NIC ↔ our-category mapping · Udyam dashboard as 2013→2026 bridge.

**Later:** AGMARKNET cache (keep a minimal seasonality index regardless — feeds Threats) · Livestock Census (dairy) · IMD rainfall · AI4Bharat/Bhashini voice options.

**Village-name matcher (demo-critical):** Indic-adapted Soundex/Metaphone + fuzzy distance + GPS prior + top-3 confirmation UI.

---

## 7. Stack

FastAPI · PostgreSQL + PostGIS + pgvector · React + Tailwind voice-first PWA + MapLibre · Celery/FastAPI background tasks · WeasyPrint (bank handout PDF) · scikit-learn/LightGBM · ONNX Runtime (speech) · llama.cpp (local fallback LLM) · Docker Compose (`make demo` one-command boot). OSRM isochrone = stretch, not blocker.

---

## 8. Timeline ⚖️ — 14 days to the Sep-20 idea gate (not 4 weeks)

| Window | Deliverables |
|---|---|
| **Sep 6–8** | Repo + Docker; SHRUG ingest (Ranchi) + village coords; **finance engine complete** (router, caps, moratorium modes, DSCR right-sizing, stress) + golden tests; 3 NABARD templates; Udyam granularity check; HCES registration |
| **Sep 9–11** | Estimation models v1 + baselines logged; facts-object report pipeline (GBNF + numeric validation); Hindi voice loop (VAD+ASR+TTS, intent classifier, village matcher); scheme corpus + rule YAML |
| **Sep 12–14** | PWA polish; assisted mode; ministry dashboard stub; PDF handout; **END-TO-END FREEZE = fallback demo** |
| **Sep 15–18** | Ranchi ground-truth shop-count validation (credibility claim no one else has); deck built around the red max-loan column; demo video ×3 takes |
| **Sep 19–20** | Submit |
| **Post-gate** | More categories/languages, stacking graph, offline hardening → 36-h finale plan (existing build runs by hour 6; freeze fallback by hour 12; 6 full rehearsals; feature-freeze hour 30) |

**Staffing:** the two strongest members on Data/Geo joins + Competitor Density (the bottleneck, not the LLM). Backend must be flawless, not clever. Presentation owns the September gate.

---

## 9. Differentiators & demo

1. Right-sized loan vs max loan (red column) — the ministry's own failure mechanism, answered.
2. Speaks NSFDC/SCA natively: Logic A/B caps, quarterly instalments, moratorium rules, **Jan-2026 ₹5 L ceiling**.
3. Every number computed + cited; grammar-constrained LLM; catch-rate metric; live "where did that number come from?" provenance panel.
4. Competitor-density ML with honest baselines + Ranchi ground-truth check.
5. Assisted VLE mode + ministry dashboard (deployment + policy story).
6. Voice-first vernacular, offline-capable lane.

**Demo script:** speak a Ranchi village + ₹1 L savings + dairy → feasibility band report (Hindi voice) → red ₹9 L vs green right-sized loan → quarterly schedule + DSCR chart → NSFDC route + document checklist → judge asks provenance → flip the citation panel.

**Judge Q&A (prepared):** where numbers come from · "just a ChatGPT wrapper?" (show validator catch) · Census 2011 staleness (scaling + HCES validation) · why no failure predictor (no labels → stress tests) · offline (quantized local lane, network off).

---

## 10. Risks / prepared responses

| Risk | Response |
|---|---|
| Census 2011 age | Only village-level data that exists; scale by district growth; validate against HCES 2023-24 & Mission Antyodaya/night lights |
| Village coordinates missing | SHRUG v2.2 polygons solve it; budget half a day regardless |
| Udyam granularity insufficient | Model ① falls back to EC13 density baseline; demo unaffected |
| LLM/cloud failure at event | Local 8B lane + template-only reports + cached demo |
| OSM rural sparsity | That IS Model ①'s job; report bands + confidence badges |
| DPDP/privacy | No PII to the LLM; local processing |

## First coding milestone
Repo scaffold + `finance` package (router, NSFDC-capped loans, quarterly amortization with moratorium modes, DSCR right-sizing, stress tests, NABARD-style cost templates as YAML) + pytest golden vectors + FastAPI endpoints — the deterministic core everything else hangs off.
