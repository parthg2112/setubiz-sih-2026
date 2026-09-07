"""Estimation layer — bands, baselines and the rule engine (PLAN.md §3, §4)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.data.loader import SampleDataSource
from setubiz.feasibility import competitors, demand, market_reach, swot, threats
from setubiz.geo import haversine_km
from setubiz.schemas import Confidence


@pytest.fixture
def source():
    return SampleDataSource()


@pytest.fixture
def ormanjhi(source):
    return next(v for v in source.all_villages() if v.name == "Ormanjhi")


@pytest.fixture
def reach(ormanjhi, source):
    return market_reach.compute(ormanjhi, source, radius_km=10.0)


def test_haversine_matches_a_known_distance():
    # Ranchi (23.34, 85.31) to Bokaro (23.67, 85.98) is roughly 78 km.
    assert 74 < haversine_km(23.34, 85.31, 23.67, 85.98) < 82
    assert haversine_km(23.34, 85.31, 23.34, 85.31) == 0


def test_radius_query_is_inclusive_and_sorted(ormanjhi, source):
    hits = source.villages_within(ormanjhi.lat, ormanjhi.lon, 10.0)
    assert hits[0].village.shrid == ormanjhi.shrid  # the centre is its own nearest neighbour
    assert hits[0].distance_km == 0
    assert [h.distance_km for h in hits] == sorted(h.distance_km for h in hits)
    assert all(h.distance_km <= 10.0 for h in hits)
    assert len(source.villages_within(ormanjhi.lat, ormanjhi.lon, 30.0)) > len(hits)


def test_market_reach_scales_2011_forward(reach):
    assert reach.growth_factor == Decimal("1.29")  # Ranchi, from settings
    assert reach.households_now == int(Decimal(reach.households_2011) * reach.growth_factor)
    assert reach.population_now > reach.population_2011
    assert reach.reference_year == 2026
    assert "intercensal_scaling" in reach.sources


def test_income_segments_partition_the_catchment(reach):
    assert reach.income_segments
    assert sum(s.share for s in reach.income_segments) == Decimal("1.00")
    assert sum(s.households for s in reach.income_segments) <= reach.households_now


def test_unknown_district_falls_back_to_the_default_growth_factor():
    assert market_reach.growth_factor_for("Some Other District") == Decimal("1.25")
    assert market_reach.growth_factor_for("RANCHI") == Decimal("1.29")


def test_competitor_estimate_is_a_band_floored_by_observed_pois(ormanjhi, reach, source):
    est = competitors.Ec13ZScoreEstimator().estimate(ormanjhi, reach, "dairy", source)
    assert est.band.low <= est.band.point <= est.band.high
    assert est.band.low >= est.osm_observed  # an observed count is a hard floor
    assert est.band.unit == "enterprises"
    assert est.z_score is not None
    assert est.band.confidence is Confidence.MEDIUM
    assert "ec13_sample" in est.band.sources


def test_competitor_estimator_falls_back_when_a_block_has_no_ec13_row(ormanjhi, reach, source):
    orphan = ormanjhi.model_copy(update={"block": "Nowhere"})
    est = competitors.Ec13ZScoreEstimator().estimate(orphan, reach, "dairy", source)
    assert est.band.confidence is Confidence.LOW
    assert est.z_score is None
    assert any(n.id == "no_ec13_row" for n in est.notes)
    assert all(n.text_en and n.text_hi for n in est.notes)


def test_competitor_estimate_is_raised_to_the_observed_count(ormanjhi, source):
    """A tiny catchment can estimate fewer enterprises than are actually mapped."""
    tiny = market_reach.compute(ormanjhi, source, radius_km=0.5)
    est = competitors.Ec13ZScoreEstimator().estimate(ormanjhi, tiny, "kirana", source)
    assert est.band.point >= est.osm_observed


def test_the_ml_estimator_is_registered_but_honestly_unimplemented(ormanjhi, reach, source):
    estimator = competitors.get_estimator("lightgbm_density")
    with pytest.raises(NotImplementedError, match="Model ① is not trained yet"):
        estimator.estimate(ormanjhi, reach, "dairy", source)
    with pytest.raises(KeyError, match="unknown competitor estimator"):
        competitors.get_estimator("magic")


def test_demand_is_reported_as_a_band_around_the_state_average(reach, source):
    est = demand.HcesMeanBandEstimator().estimate(reach, "dairy", source)
    per_hh = est.per_household_monthly
    assert per_hh.low < per_hh.point < per_hh.high
    assert per_hh.point == est.baseline_state_average  # the baseline we must beat
    assert est.addressable_market_monthly.point > per_hh.point
    assert "state average applied uniformly" in est.notes[0]
    with pytest.raises(KeyError, match="no consumption profile"):
        demand.HcesMeanBandEstimator().estimate(reach, "space_tourism", source)
    with pytest.raises(KeyError, match="unknown demand estimator"):
        demand.get_estimator("magic")


def test_seasonality_index_finds_the_peak_and_trough(reach, source):
    assessment = threats.assess(reach, "dairy", source)
    index = assessment.seasonality
    assert index is not None
    assert index.commodity == "Maize"
    assert index.peak_month == "Nov"
    assert index.trough_month == "May"
    assert index.peak_to_trough_ratio > 1
    assert index.is_strongly_seasonal is True
    assert assessment.price_band is not None
    assert assessment.price_band.low < assessment.price_band.high


def test_a_category_without_a_commodity_proxy_yields_no_seasonality(reach, source):
    assessment = threats.assess(reach, "tailoring", source)
    assert assessment.seasonality is None
    assert assessment.price_band is None
    assert all(t.id != "seasonal_arrivals" for t in assessment.threats)


def test_single_buyer_threat_fires_on_a_thin_market(reach, source):
    assessment = threats.assess(reach, "dairy", source)
    ids = {t.id for t in assessment.threats}
    if reach.mandis_in_radius < 2:
        assert "single_buyer" in ids
    assert all(t.text_en and t.text_hi for t in assessment.threats)


def test_swot_rules_fire_deterministically_and_cite_sources():
    metrics = {
        "demand_supply_ratio": Decimal("1.4"),
        "competitors_point": Decimal("12"),
        "households_now": 12000,
        "villages_in_radius": 9,
        "villages_with_bank": 4,
        "radius_km": 10.0,
        "literacy_rate": 0.7,
        "literacy_pct": 70.0,
        "road_connected_share": Decimal("0.8"),
        "road_pct": Decimal("80"),
        "dist_to_town_km": 30.0,
        "recommended_min_dscr": Decimal("2.1"),
        "max_loan_min_dscr": Decimal("0.5"),
        "recommended_loan": Decimal("205000"),
        "recommended_loan_fmt": "₹2,05,000",
        "max_loan": Decimal("900000"),
        "max_loan_fmt": "₹9,00,000",
        "capital_shortfall": Decimal("0"),
        "capital_shortfall_fmt": "₹0",
        "seasonality_cv": Decimal("0.6"),
        "in_scope": True,
        "scheme_name": "NSFDC Term Loan Scheme",
        "rate_pct": Decimal("8.0"),
    }
    result = swot.evaluate(metrics)
    fired = {i.id for i in result.items}
    assert "underserved_market" in fired
    assert "large_catchment" in fired
    assert "overborrowing_risk" in fired
    assert "capital_shortfall" not in fired  # shortfall is zero
    assert "thin_catchment" not in fired
    assert all(i.cites for i in result.items)
    assert result.strengths and result.threats
    assert set(result.by_quadrant("opportunity")) <= set(result.items)
    # Evaluating twice must give the same answer — this layer is not a model.
    assert [i.id for i in swot.evaluate(metrics).items] == [i.id for i in result.items]


def test_swot_compound_and_missing_metric_conditions():
    base = {
        "literacy_rate": 0.7,
        "road_connected_share": Decimal("0.9"),
        "literacy_pct": 70.0,
        "road_pct": Decimal("90"),
    }
    assert swot._matches(
        {
            "all": [
                {"metric": "literacy_rate", "op": ">=", "value": 0.65},
                {"metric": "road_connected_share", "op": ">=", "value": 0.6},
            ]
        },
        base,
    )
    assert swot._matches(
        {
            "any": [
                {"metric": "literacy_rate", "op": "<", "value": 0.1},
                {"metric": "road_connected_share", "op": ">=", "value": 0.6},
            ]
        },
        base,
    )
    # A metric the caller never supplied, or supplied as None, must not fire a rule.
    assert not swot._matches({"metric": "not_computed", "op": ">", "value": 0}, base)
    assert not swot._matches(
        {"metric": "literacy_rate", "op": ">", "value": 0}, {"literacy_rate": None}
    )
    with pytest.raises(ValueError, match="unsupported operator"):
        swot._matches({"metric": "literacy_rate", "op": "=~", "value": 1}, base)


def test_sample_data_source_reports_itself_as_synthetic(source):
    assert source.synthetic is True
    assert source.village_by_shrid("does-not-exist") is None
    assert source.block_density("Ranchi", "Nowhere", "dairy") is None
    assert source.district_density_stats("Nowhere", "dairy") is None
    assert source.demand_profile("Nowhere", "dairy") is None
    assert source.income_segments("Nowhere") == ()
    assert source.arrivals("tailoring") is None
    assert "shrug_sample" in source.source_ids()
