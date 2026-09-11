"""The facts object — the locked single source of truth for every number (PLAN.md §3).

Nothing downstream computes. The narrator reads this and may not introduce a figure that is not in
`numeric_index`; the validator enforces that mechanically. If a number is not here, it is not true.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict

from setubiz.config import get_settings
from setubiz.data.loader import DataSource, Village, get_data_source
from setubiz.eligibility import EligibilityResult, SocialCategory, assess
from setubiz.facts.provenance import resolve
from setubiz.feasibility import competitors as competitors_mod
from setubiz.feasibility import demand as demand_mod
from setubiz.feasibility import market_reach as reach_mod
from setubiz.feasibility import swot as swot_mod
from setubiz.feasibility import threats as threats_mod
from setubiz.finance.alternatives import AlternativeSet, viable_configurations
from setubiz.finance.amortization import AmortizationResult, MoratoriumMode, amortize
from setubiz.finance.cost_templates import CostTemplate, find_template_for_category
from setubiz.finance.alternatives import AlternativeSet, viable_configurations
from setubiz.finance.rightsizing import RightSizing, right_size
from setubiz.finance.router import ActivityKind, SchemeRoute, route
from setubiz.money import ZERO, format_inr, q
from setubiz.schemas import Advisory, AdvisoryRequest, Source


class Facts(BaseModel):
    """Frozen. Serialize with `model_dump_json()` — that file is `facts.json`."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    generated_at: datetime
    request: AdvisoryRequest
    village: Village
    template: CostTemplate

    market: reach_mod.MarketReach
    competitors: competitors_mod.CompetitorEstimate
    demand: demand_mod.DemandEstimate
    threats: threats_mod.ThreatAssessment
    swot: swot_mod.Swot

    scheme: SchemeRoute
    right_sizing: RightSizing
    #: Sizes of the same business that do work, when the one as costed does not.
    alternatives: AlternativeSet
    amortization_max: AmortizationResult | None
    amortization_recommended: AmortizationResult | None
    amortization_alternate_mode: AmortizationResult | None

    eligibility: EligibilityResult

    numeric_index: dict[str, Decimal]
    provenance: dict[str, tuple[str, ...]]
    sources: tuple[Source, ...]
    #: Bilingual engine advisories. The UI renders `text_en`/`text_hi` by the chosen language.
    warnings: tuple[Advisory, ...]
    #: True while any contributing source is a synthetic placeholder. Never ship a report
    #: claiming otherwise — the sample data README explains why.
    contains_synthetic_data: bool

    def verbatim_text(self) -> str:
        """Locked strings the report may quote word for word.

        A digit inside one of these — a PIN code in an SCA address, a rate quoted in a scheme
        note — is grounded by construction: it came from the facts object, not from a model.
        """
        parts: list[str] = [
            *self.eligibility.reasons,
            *self.eligibility.conditions,
            *(d.en for d in self.eligibility.documents),
            *(d.hi or "" for d in self.eligibility.documents),
            *(w.text_en for w in self.warnings),
            *(w.text_hi for w in self.warnings),
            *self.template.assumptions,
            *(li.item for li in self.template.fixed_capital),
            *(li.item for li in self.template.monthly_revenue),
            *(li.item for li in self.template.monthly_opex),
            *(t.text_en for t in self.threats.threats),
            *(t.text_hi for t in self.threats.threats),
            *(i.text_en for i in self.swot.items),
            *(i.text_hi for i in self.swot.items),
            self.template.source,
            self.template.unit,
            self.template.name,
            self.scheme.scheme_name,
            *self.scheme.notes,
            self.competitors.band.method,
            self.demand.per_household_monthly.method,
            self.demand.addressable_market_monthly.method,
        ]
        if self.eligibility.sca:
            parts += [
                self.eligibility.sca.address,
                self.eligibility.sca.name,
                self.eligibility.sca.channel,
            ]
        if self.eligibility.corporation:
            parts.append(self.eligibility.corporation.income_ceiling_note or "")
        return " ".join(p for p in parts if p)

    def allowed_numbers(self, tolerance: Decimal = Decimal("0.02")) -> set[Decimal]:
        """Every figure the narration layer is permitted to state."""
        allowed: set[Decimal] = set(self.numeric_index.values())
        for row in self.amortization_recommended.schedule if self.amortization_recommended else ():
            allowed.update(
                {row.quarter, row.opening, row.interest, row.principal, row.instalment, row.closing}
            )
        for row in self.amortization_max.schedule if self.amortization_max else ():
            allowed.update(
                {row.quarter, row.opening, row.interest, row.principal, row.instalment, row.closing}
            )
        for item in (
            *self.template.fixed_capital,
            *self.template.monthly_opex,
            *self.template.monthly_revenue,
        ):
            allowed.add(item.amount)
        for row in self.right_sizing.max_loan_dscr + self.right_sizing.recommended_dscr:
            allowed.update({Decimal(row.year), row.dscr, row.debt_service, row.noi})
        if self.threats.seasonality:
            allowed.update(Decimal(a) for a in self.threats.seasonality.arrivals)
            allowed.update(Decimal(p) for p in self.threats.seasonality.modal_price)
        allowed.update(Decimal(n.village.households_2011) for n in self.market.neighbours)
        allowed.update(Decimal(str(n.distance_km)) for n in self.market.neighbours)
        allowed.update(Decimal(s.households) for s in self.market.income_segments)
        allowed.update(Decimal(str(s.share * 100)) for s in self.market.income_segments)
        return {q(v, Decimal("0.01")) for v in allowed if isinstance(v, Decimal)} | {
            q(Decimal(v), Decimal("0.01")) for v in allowed if not isinstance(v, Decimal)
        }


def _resolve_village(request: AdvisoryRequest, source: DataSource) -> Village:
    if request.village_shrid:
        village = source.village_by_shrid(request.village_shrid)
        if village is None:
            raise KeyError(f"unknown village shrid {request.village_shrid!r}")
        return village
    from setubiz.matching.village_matcher import match_villages  # local: avoids an import cycle

    matches = match_villages(request.village_query or "", source, state=request.state, limit=1)
    if not matches:
        raise KeyError(f"no village matched {request.village_query!r}")
    village = source.village_by_shrid(matches[0].shrid)
    assert village is not None
    return village


def _swot_metrics(
    village: Village,
    reach: reach_mod.MarketReach,
    comp: competitors_mod.CompetitorEstimate,
    dem: demand_mod.DemandEstimate,
    threat: threats_mod.ThreatAssessment,
    rs: RightSizing,
    scheme: SchemeRoute,
    template: CostTemplate,
) -> dict[str, Any]:
    capacity = q(comp.band.point * template.monthly_revenue_total)
    ratio = (
        q(dem.addressable_market_monthly.point / capacity, Decimal("0.01"))
        if capacity > 0
        else Decimal("0")
    )
    per_competitor = (
        q(Decimal(reach.households_now) / comp.band.point, Decimal("1"))
        if comp.band.point > 0
        else Decimal("0")
    )
    return {
        "demand_supply_ratio": ratio,
        "households_per_competitor": per_competitor,
        "competitors_point": comp.band.point,
        "competitors_low": comp.band.low,
        "competitors_high": comp.band.high,
        "households_now": reach.households_now,
        "villages_in_radius": reach.villages_in_radius,
        "villages_with_bank": reach.villages_with_bank,
        "mandis_in_radius": reach.mandis_in_radius,
        "radius_km": reach.radius_km,
        "literacy_rate": village.literacy_rate,
        "literacy_pct": round(village.literacy_rate * 100, 1),
        "road_connected_share": reach.road_connected_share,
        "road_pct": q(reach.road_connected_share * 100, Decimal("1")),
        "dist_to_town_km": village.dist_to_town_km,
        "recommended_min_dscr": rs.recommended_min_dscr,
        "max_loan_min_dscr": rs.max_loan_min_dscr,
        "recommended_loan": rs.recommended_loan,
        "recommended_loan_fmt": format_inr(rs.recommended_loan),
        "max_loan": rs.max_loan,
        "max_loan_fmt": format_inr(rs.max_loan),
        "capital_shortfall": rs.capital_shortfall,
        "capital_shortfall_fmt": format_inr(rs.capital_shortfall),
        "seasonality_cv": (
            threat.seasonality.coefficient_of_variation if threat.seasonality else Decimal("0")
        ),
        "in_scope": scheme.in_scope,
        "scheme_name": scheme.scheme_name,
        "rate_pct": q(scheme.annual_rate * 100, Decimal("0.1")),
    }


def _numeric_index(
    reach: reach_mod.MarketReach,
    comp: competitors_mod.CompetitorEstimate,
    dem: demand_mod.DemandEstimate,
    threat: threats_mod.ThreatAssessment,
    rs: RightSizing,
    scheme: SchemeRoute,
    template: CostTemplate,
    amort_max: AmortizationResult | None,
    amort_rec: AmortizationResult | None,
    eligibility: EligibilityResult,
    alternatives: AlternativeSet,
    metrics: dict[str, Any],
) -> dict[str, Decimal]:
    index: dict[str, Decimal] = {
        "households_now": Decimal(reach.households_now),
        "households_2011": Decimal(reach.households_2011),
        "population_now": Decimal(reach.population_now),
        "population_2011": Decimal(reach.population_2011),
        "villages_in_radius": Decimal(reach.villages_in_radius),
        "villages_with_bank": Decimal(reach.villages_with_bank),
        "mandis_in_radius": Decimal(reach.mandis_in_radius),
        "radius_km": Decimal(str(reach.radius_km)),
        "growth_factor": reach.growth_factor,
        "road_connected_pct": q(reach.road_connected_share * 100, Decimal("0.1")),
        "village_households_2011": Decimal(reach.centre.households_2011),
        "village_population_2011": Decimal(reach.centre.population_2011),
        "literacy_pct": q(Decimal(str(reach.centre.literacy_rate)) * 100, Decimal("0.1")),
        "sc_pct": q(Decimal(str(reach.centre.sc_pct)) * 100, Decimal("0.1")),
        "st_pct": q(Decimal(str(reach.centre.st_pct)) * 100, Decimal("0.1")),
        "dist_to_town_km": Decimal(str(reach.centre.dist_to_town_km)),
        "competitors_low": comp.band.low,
        "competitors_point": comp.band.point,
        "competitors_high": comp.band.high,
        "competitors_observed_osm": Decimal(comp.osm_observed),
        "competitor_density_per_1k_households": comp.density_per_1k_households,
        "demand_per_household_low": dem.per_household_monthly.low,
        "demand_per_household_point": dem.per_household_monthly.point,
        "demand_per_household_high": dem.per_household_monthly.high,
        "addressable_market_low": dem.addressable_market_monthly.low,
        "addressable_market_point": dem.addressable_market_monthly.point,
        "addressable_market_high": dem.addressable_market_monthly.high,
        "demand_supply_ratio": metrics["demand_supply_ratio"],
        "households_per_competitor": metrics["households_per_competitor"],
        "margin": scheme.margin,
        "project_cost": scheme.project_cost,
        "max_loan": rs.max_loan,
        "recommended_loan": rs.recommended_loan,
        "headroom": rs.headroom,
        "required_capital": rs.required_capital,
        "debt_need": rs.debt_need,
        "capital_shortfall": rs.capital_shortfall,
        "annual_noi": rs.annual_noi,
        "monthly_revenue": template.monthly_revenue_total,
        "monthly_opex": template.monthly_opex_total,
        "monthly_net": template.monthly_net,
        "fixed_capital": template.fixed_capital_total,
        "working_capital": template.working_capital,
        "working_capital_months": Decimal(template.working_capital_months),
        "annual_rate_pct": q(scheme.annual_rate * 100, Decimal("0.001")),
        "quarterly_rate_pct": q(scheme.quarterly_rate * 100, Decimal("0.001")),
        "sca_rate_pct": q((scheme.sca_rate or ZERO) * 100, Decimal("0.001")),
        "total_quarters": Decimal(scheme.total_quarters),
        "moratorium_quarters": Decimal(scheme.moratorium_quarters),
        "repayment_quarters": Decimal(scheme.repayment_quarters),
        "tenure_years": Decimal(scheme.total_quarters // 4),
        "dscr_threshold": rs.dscr_threshold,
        "stress_floor": rs.stress_floor,
        "max_loan_min_dscr": rs.max_loan_min_dscr,
        "recommended_min_dscr": rs.recommended_min_dscr,
    }

    # The stressed operating surplus is a property of the unit, not of the loan, so index it
    # unconditionally. Deriving it from `rs.*_stress` alone left it missing whenever no loan was
    # sized (an out-of-scope margin), and the report template then failed to render at all.
    for factor in get_settings().stress_factors:
        drop = str(int((1 - factor) * 100))
        stressed_revenue = q(template.monthly_revenue_total * factor)
        stressed = q((stressed_revenue - template.monthly_opex_total) * 12)
        index[f"annual_noi_stress_{drop}"] = stressed

    if amort_max:
        index["quarterly_instalment_max"] = amort_max.instalment
        index["total_interest_max"] = amort_max.total_interest
        index["total_outflow_max"] = amort_max.total_outflow
    if amort_rec:
        index["quarterly_instalment_recommended"] = amort_rec.instalment
        index["total_interest_recommended"] = amort_rec.total_interest
        index["total_outflow_recommended"] = amort_rec.total_outflow
    for row in rs.recommended_dscr:
        index[f"recommended_dscr_year_{row.year}"] = row.dscr
        index[f"recommended_debt_service_year_{row.year}"] = row.debt_service
    for row in rs.max_loan_dscr:
        index[f"max_loan_dscr_year_{row.year}"] = row.dscr
        index[f"max_loan_debt_service_year_{row.year}"] = row.debt_service
    for stress in rs.recommended_stress:
        key = str(int((1 - stress.revenue_factor) * 100))
        index[f"recommended_min_dscr_stress_{key}"] = stress.min_dscr
        index[f"annual_noi_stress_{key}"] = stress.annual_noi
    for stress in rs.max_loan_stress:
        key = str(int((1 - stress.revenue_factor) * 100))
        index[f"max_loan_min_dscr_stress_{key}"] = stress.min_dscr
    if threat.seasonality:
        index["seasonality_cv"] = threat.seasonality.coefficient_of_variation
        index["peak_to_trough_ratio"] = threat.seasonality.peak_to_trough_ratio
    if threat.price_band:
        index["price_low"] = threat.price_band.low
        index["price_point"] = threat.price_band.point
        index["price_high"] = threat.price_band.high
    for config in alternatives.considered:
        n = config.units
        # The size itself is quoted in the prose ("750 birds"), so it needs grounding too.
        index[f"alt_{n}_units"] = Decimal(n)
        index[f"alt_{n}_project_cost"] = config.project_cost
        index[f"alt_{n}_debt_need"] = config.debt_need
        index[f"alt_{n}_loan"] = config.loan
        index[f"alt_{n}_instalment"] = config.instalment
        index[f"alt_{n}_annual_noi"] = config.annual_noi
        index[f"alt_{n}_shortfall"] = config.shortfall
        # 999 is the no-debt-service sentinel, not a ratio; indexing it would let the narrator
        # quote it as one.
        if config.loan > 0:
            index[f"alt_{n}_min_dscr"] = config.min_dscr
    if alternatives.closest is not None:
        index["alt_closest_units"] = Decimal(alternatives.closest.units)
    if alternatives.additional_margin_needed is not None:
        index["alt_additional_margin_needed"] = alternatives.additional_margin_needed
    if alternatives.phased is not None:
        index["alt_phased_expansion_cost"] = alternatives.phased.expansion_cost
        index["alt_phased_annual_retained"] = alternatives.phased.annual_retained
        index["alt_phased_years"] = Decimal(alternatives.phased.years_to_expand)
    if eligibility.income_ceiling is not None:
        index["income_ceiling"] = eligibility.income_ceiling
    if eligibility.annual_family_income is not None:
        index["annual_family_income"] = eligibility.annual_family_income
    return index


def build_facts(request: AdvisoryRequest, source: DataSource | None = None) -> Facts:
    """Run the whole deterministic pipeline and lock the result."""
    settings = get_settings()
    source = source or get_data_source()

    village = _resolve_village(request, source)
    template = find_template_for_category(request.business_category)
    if template is None:
        raise KeyError(
            f"no cost template for business category {request.business_category!r}; "
            "the finance engine cannot right-size without unit economics"
        )

    reach = reach_mod.compute(village, source, request.radius_km)
    comp = competitors_mod.get_estimator(settings.competitor_estimator).estimate(
        village, reach, request.business_category, source
    )
    dem = demand_mod.get_estimator(settings.demand_estimator).estimate(
        reach, request.business_category, source
    )
    threat = threats_mod.assess(reach, request.business_category, source)

    scheme = route(request.savings, ActivityKind(request.activity_kind))
    mode = MoratoriumMode(request.moratorium_mode)
    rs = right_size(scheme, template, mode)
    alternatives = viable_configurations(scheme, template, mode)

    amort_max = (
        amortize(
            scheme.max_loan,
            scheme.annual_rate,
            scheme.total_quarters,
            scheme.moratorium_quarters,
            mode,
        )
        if scheme.max_loan > 0
        else None
    )
    amort_rec = (
        amortize(
            rs.recommended_loan,
            scheme.annual_rate,
            scheme.total_quarters,
            scheme.moratorium_quarters,
            mode,
        )
        if rs.recommended_loan > 0
        else None
    )
    alternate = (
        MoratoriumMode.CAPITALIZED if mode is MoratoriumMode.SERVICED else MoratoriumMode.SERVICED
    )
    amort_alt = (
        amortize(
            rs.recommended_loan,
            scheme.annual_rate,
            scheme.total_quarters,
            scheme.moratorium_quarters,
            alternate,
        )
        if rs.recommended_loan > 0
        else None
    )

    eligibility = assess(
        SocialCategory(request.social_category),
        request.annual_family_income,
        state=request.state,
        activity_category=request.business_category,
        is_woman=request.is_woman,
        has_prior_experience=request.has_prior_experience,
        requested_loan=rs.recommended_loan or None,
    )

    metrics = _swot_metrics(village, reach, comp, dem, threat, rs, scheme, template)
    swot = swot_mod.evaluate(metrics)
    index = _numeric_index(
        reach,
        comp,
        dem,
        threat,
        rs,
        scheme,
        template,
        amort_max,
        amort_rec,
        eligibility,
        alternatives,
        metrics,
    )

    source_ids = tuple(
        dict.fromkeys(
            (
                *reach.sources,
                *comp.band.sources,
                *dem.per_household_monthly.sources,
                *dem.addressable_market_monthly.sources,
                *threat.sources,
                *scheme.sources,
                "finance_engine",
                "nabard_templates",
                *eligibility.sources,
                *alternatives.sources,
                *(c for item in swot.items for c in item.cites),
            )
        )
    )
    # The registry declares each source synthetic by default. The loader knows what it actually
    # read, so let it correct the record -- otherwise a report built on real data still disclaims
    # itself as sample data, which is its own kind of false statement.
    sources = tuple(
        s.model_copy(update={"synthetic": source.source_synthetic[s.id]})
        if s.id in source.source_synthetic
        else s
        for s in resolve(source_ids)
    )

    provenance: dict[str, tuple[str, ...]] = {}
    for key in index:
        if key.startswith(("competitors", "competitor_density")):
            provenance[key] = comp.band.sources
        elif key.startswith(("demand_", "addressable_")):
            provenance[key] = dem.addressable_market_monthly.sources
        elif key.startswith(
            (
                "households",
                "population",
                "villages",
                "village_",
                "road_",
                "growth",
                "radius",
                "mandis",
                "literacy",
                "sc_pct",
                "st_pct",
                "dist_to_town",
            )
        ):
            provenance[key] = reach.sources
        elif key.startswith(("price_", "seasonality", "peak_")):
            provenance[key] = ("agmarknet",)
        elif key.startswith(
            ("monthly_", "fixed_capital", "working_capital", "required_capital", "annual_noi")
        ):
            provenance[key] = ("nabard_templates",)
        elif key.startswith("alt_"):
            # The size search re-costs the NABARD template and re-runs the finance engine, so it
            # cites both. Stated here rather than left to the catch-all below, which would be
            # right by accident.
            provenance[key] = alternatives.sources
        elif key.startswith(("income_", "annual_family")):
            provenance[key] = eligibility.sources
        elif key in {
            "annual_rate_pct",
            "quarterly_rate_pct",
            "sca_rate_pct",
            "total_quarters",
            "moratorium_quarters",
            "repayment_quarters",
            "tenure_years",
        }:
            provenance[key] = scheme.sources
        else:
            provenance[key] = ("finance_engine", "nabard_templates")

    return Facts(
        generated_at=datetime.now(UTC),
        request=request,
        village=village,
        template=template,
        market=reach,
        competitors=comp,
        demand=dem,
        threats=threat,
        swot=swot,
        scheme=scheme,
        right_sizing=rs,
        alternatives=alternatives,
        amortization_max=amort_max,
        amortization_recommended=amort_rec,
        amortization_alternate_mode=amort_alt,
        eligibility=eligibility,
        numeric_index=index,
        provenance=provenance,
        sources=sources,
        warnings=tuple(rs.warnings) + tuple(comp.notes),
        contains_synthetic_data=any(s.synthetic for s in sources),
    )
