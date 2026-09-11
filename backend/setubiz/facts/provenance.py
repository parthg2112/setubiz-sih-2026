"""The source registry. Every number in a report traces back to an id in here (PLAN.md §3, §9)."""

from __future__ import annotations

from setubiz.schemas import Source, SourceKind

_SOURCES: tuple[Source, ...] = (
    Source(
        id="census_pc11",
        title="Census of India 2011: Primary Census Abstract, village level",
        kind=SourceKind.CENSUS,
        publisher=(
            "Office of the Registrar General & Census Commissioner, Ministry of Home Affairs"
        ),
        url="https://censusindia.gov.in/census.website/data/census-tables",
        year="2011",
        note=(
            "Population, households, literates, Scheduled Caste, Scheduled Tribe and worker "
            "counts for every village. Linked to village names and polygon centroids through "
            "SHRUG v2.2 (Development Data Lab). Village populations reconcile to the published "
            "state rural totals within 0.003%."
        ),
    ),
    Source(
        id="mission_antyodaya",
        title="Mission Antyodaya village survey",
        kind=SourceKind.CENSUS,
        publisher="Ministry of Rural Development",
        url="https://missionantyodaya.nic.in",
        year="2019",
        note=(
            "Village infrastructure: bank branch, pucca road, electricity, mandi, weekly haat, "
            "milk routes and self-help groups. Surveyed in 2019, so amenity flags are fresher "
            "than the 2011 census counts and are not scaled."
        ),
    ),
    Source(
        id="openstreetmap",
        title="OpenStreetMap points of interest",
        kind=SourceKind.OSM,
        publisher="OpenStreetMap contributors, ODbL licensed",
        url="https://www.openstreetmap.org/copyright",
        note="Rural OSM coverage is sparse; a POI count is a floor on competitors, not a census.",
    ),
    Source(
        id="economic_census_2013",
        title="Sixth Economic Census 2013: establishment counts by industry",
        kind=SourceKind.ECONOMIC_CENSUS,
        publisher=("Central Statistics Office, Ministry of Statistics & Programme Implementation"),
        url="https://www.mospi.gov.in",
        year="2013",
        note=(
            "Enterprise counts per 1,000 rural households, aggregated to the block. The Economic "
            "Census publishes establishment counts only in total, so a per-category figure is "
            "apportioned by that industry's share of employment."
        ),
    ),
    Source(
        id="hces_2023_24",
        title="Household Consumption Expenditure Survey 2023-24",
        kind=SourceKind.CONSUMPTION_SURVEY,
        publisher=("National Statistics Office, Ministry of Statistics & Programme Implementation"),
        url="https://www.mospi.gov.in/publication/household-consumption-expenditure-survey-2023-24",
        year="2023-24",
        note=(
            "Published Fact Sheet: state rural MPCE (Statement 7), item-group shares of spend "
            "(Statement 4) and the rural MPCE distribution (Figure 1R), which sets the band width. "
            "What share of that spend one village enterprise can capture is our assumption, and "
            "each category states its reasoning."
        ),
    ),
    Source(
        id="agmarknet",
        title="AGMARKNET daily mandi prices",
        kind=SourceKind.MARKET_PRICES,
        publisher=(
            "Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare"
        ),
        url="https://data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
        note=(
            "The open-data resource publishes the current day's prices only. The twelve-month "
            "arrivals series behind the seasonality index needs a portal export; until then the "
            "seasonality assessment is omitted rather than estimated."
        ),
    ),
    Source(
        id="intercensal_scaling",
        title="District intercensal population scaling 2011 → 2026",
        kind=SourceKind.COMPUTED,
        note=(
            "Census 2027 house-listing began April 2026; 2011 remains the only village-level base."
        ),
    ),
    Source(
        id="nabard_templates",
        title="NABARD Model Bankable Projects: unit cost templates",
        kind=SourceKind.COST_TEMPLATE,
        publisher="National Bank for Agriculture and Rural Development",
        url="https://www.nabard.org/",
        note="Line items follow published model project norms; local prices vary.",
    ),
    Source(
        id="mosje_corporations",
        title="MoSJE apex corporations: NSFDC / NSKFDC / NBCFDC",
        kind=SourceKind.SCHEME,
        publisher="Ministry of Social Justice & Empowerment",
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
    # The five comparison schemes. Registered because the stacking layer cites them; without a
    # Source record here, any figure or verdict attributed to them fails the facts contract.
    Source(
        id="pmmy",
        title="Pradhan Mantri MUDRA Yojana",
        kind=SourceKind.SCHEME,
        publisher="Ministry of Finance",
        url="https://www.mudra.org.in/",
        note="Collateral-free term lending with no caste-category test. Rate set by the bank.",
    ),
    Source(
        id="pmegp",
        title="Prime Minister's Employment Generation Programme",
        kind=SourceKind.SCHEME,
        publisher="Ministry of Micro, Small and Medium Enterprises / KVIC",
        url="https://www.kviconline.gov.in/pmegpeportal/",
        note=(
            "Carries a capital subsidy for rural and special-category applicants. The published "
            "rate is a range rather than a single figure, so this build quotes no subsidy "
            "percentage and computes none."
        ),
    ),
    Source(
        id="cgtmse",
        title="Credit Guarantee Fund Trust for Micro and Small Enterprises",
        kind=SourceKind.SCHEME,
        publisher="Ministry of Micro, Small and Medium Enterprises",
        url="https://www.cgtmse.in/",
        note="A guarantee cover, not a loan. Removes a collateral demand rather than adding money.",
    ),
    Source(
        id="dri",
        title="Differential Rate of Interest scheme",
        kind=SourceKind.SCHEME,
        publisher="Reserve Bank of India",
        url="https://www.rbi.org.in/",
        note=(
            "4% fixed lending for the weakest borrowers, capped at Rs 20,000 with its own "
            "income test."
        ),
    ),
    Source(
        id="stand_up_india",
        title="Stand-Up India",
        kind=SourceKind.SCHEME,
        publisher="Department of Financial Services",
        url="https://www.standupmitra.in/",
        note="Greenfield lending for Scheduled Caste, Scheduled Tribe and women entrepreneurs.",
    ),
    Source(
        id="finance_engine",
        title="SetuBiz deterministic finance engine",
        kind=SourceKind.COMPUTED,
        note="Quarterly amortization, DSCR right-sizing and stress tests. Auditable code, no ML.",
    ),
)

SOURCES: dict[str, Source] = {s.id: s for s in _SOURCES}


def resolve(ids: tuple[str, ...] | list[str]) -> tuple[Source, ...]:
    """Look up source records, skipping ids that are not registered."""
    return tuple(SOURCES[i] for i in dict.fromkeys(ids) if i in SOURCES)


def unknown_ids(ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(i for i in ids if i not in SOURCES)
