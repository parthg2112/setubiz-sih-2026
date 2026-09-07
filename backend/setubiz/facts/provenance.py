"""The source registry. Every number in a report traces back to an id in here (PLAN.md §3, §9)."""

from __future__ import annotations

from setubiz.schemas import Source, SourceKind

_SOURCES: tuple[Source, ...] = (
    Source(
        id="shrug_sample",
        title="Census 2011 village PCA (SHRUG v2.2 schema)",
        kind=SourceKind.CENSUS,
        url="https://www.devdatalab.org/shrug",
        year="2011",
        synthetic=True,
        note="Synthetic sample rows shaped like SHRUG v2.2. Replace before any real claim.",
    ),
    Source(
        id="osm_sample",
        title="OpenStreetMap points of interest",
        kind=SourceKind.OSM,
        url="https://www.openstreetmap.org/copyright",
        synthetic=True,
        note="Rural OSM coverage is sparse; a POI count is a floor on competitors, not a census.",
    ),
    Source(
        id="ec13_sample",
        title="Economic Census 2013 block enterprise density",
        kind=SourceKind.ECONOMIC_CENSUS,
        url="https://www.devdatalab.org/shrug_download/ec13",
        year="2013",
        synthetic=True,
    ),
    Source(
        id="hces_sample",
        title="Household Consumption Expenditure Survey 2023-24",
        kind=SourceKind.CONSUMPTION_SURVEY,
        url="https://microdata.gov.in/",
        year="2023-24",
        synthetic=True,
        note="All-India rural MPCE anchor ₹4,122 is published; per-category shares are illustrative.",
    ),
    Source(
        id="agmarknet_sample",
        title="AGMARKNET mandi arrivals and modal prices",
        kind=SourceKind.MARKET_PRICES,
        url="https://data.gov.in/resource/9ef84268-d588-465a-a308-a864a43c0075",
        synthetic=True,
    ),
    Source(
        id="intercensal_scaling",
        title="District intercensal population scaling 2011 → 2026",
        kind=SourceKind.COMPUTED,
        note="Census 2027 house-listing began April 2026; 2011 remains the only village-level base.",
    ),
    Source(
        id="nabard_templates",
        title="NABARD Model Bankable Projects — unit cost templates",
        kind=SourceKind.COST_TEMPLATE,
        url="https://www.nabard.org/",
        note="Line items follow published model project norms; local prices vary.",
    ),
    Source(
        id="mosje_corporations",
        title="MoSJE apex corporations — NSFDC / NSKFDC / NBCFDC",
        kind=SourceKind.SCHEME,
        url="https://www.dosje.gov.in/",
    ),
    Source(
        id="nsfdc_micro_finance",
        title="NSFDC Micro Finance Scheme",
        kind=SourceKind.SCHEME,
        url="https://www.dosje.gov.in/schemes-and-services/micro-finance-scheme/",
    ),
    Source(
        id="nsfdc_term_loan",
        title="NSFDC Term Loan Scheme",
        kind=SourceKind.SCHEME,
        url="https://www.dosje.gov.in/schemes-and-services/2998/",
    ),
    Source(
        id="nsfdc",
        title="National Scheduled Castes Finance and Development Corporation",
        kind=SourceKind.SCHEME,
        url="https://nsfdc.nic.in/",
    ),
    Source(
        id="nskfdc",
        title="National Safai Karamcharis Finance and Development Corporation",
        kind=SourceKind.SCHEME,
        url="https://nskfdc.nic.in/",
    ),
    Source(
        id="nbcfdc",
        title="National Backward Classes Finance and Development Corporation",
        kind=SourceKind.SCHEME,
        url="https://nbcfdc.gov.in/",
    ),
    Source(
        id="finance_engine",
        title="SetuBiz deterministic finance engine",
        kind=SourceKind.COMPUTED,
        note="Quarterly amortization, DSCR right-sizing and stress tests — auditable code, no ML.",
    ),
)

SOURCES: dict[str, Source] = {s.id: s for s in _SOURCES}


def resolve(ids: tuple[str, ...] | list[str]) -> tuple[Source, ...]:
    """Look up source records, skipping ids that are not registered."""
    return tuple(SOURCES[i] for i in dict.fromkeys(ids) if i in SOURCES)


def unknown_ids(ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(i for i in ids if i not in SOURCES)
