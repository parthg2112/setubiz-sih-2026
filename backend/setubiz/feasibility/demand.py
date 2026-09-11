"""Local demand estimation — PLAN.md §3 Model ②.

v0 is a state mean ± coefficient of variation, which is the honest MVP: it beats the "state average
applied uniformly" baseline only by admitting a band. Fay-Herriot small-area estimation on HCES
2023-24 microdata replaces it behind the same protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from setubiz.data.loader import DataSource
from setubiz.feasibility.market_reach import MarketReach
from setubiz.money import q
from setubiz.schemas import Band, Confidence


@dataclass(frozen=True)
class DemandEstimate:
    per_household_monthly: Band
    addressable_market_monthly: Band
    addressable_share: Decimal
    baseline_state_average: Decimal
    method: str
    notes: tuple[str, ...]


@runtime_checkable
class DemandEstimator(Protocol):
    name: str

    def estimate(self, reach: MarketReach, category: str, source: DataSource) -> DemandEstimate: ...


class HcesMeanBandEstimator:
    name = "hces_mean_band"

    def estimate(self, reach: MarketReach, category: str, source: DataSource) -> DemandEstimate:
        profile = source.demand_profile(reach.centre.state, category)
        if profile is None:
            raise KeyError(
                f"no consumption profile for state {reach.centre.state!r} / category {category!r}"
            )

        mpce = Decimal(str(profile["rural_mpce"]))
        size = Decimal(str(profile["avg_household_size"]))
        share = Decimal(str(profile["share_of_mpce"]))
        cv = Decimal(str(profile["cv"]))
        addressable = Decimal(str(profile["addressable_share"]))

        # MPCE is per person; a household spends mpce × household size on everything.
        per_hh = q(mpce * size * share)
        low = q(per_hh * (1 - cv))
        high = q(per_hh * (1 + cv))

        households = Decimal(reach.households_now)
        tam_point = q(per_hh * households * addressable)
        tam_low = q(low * households * addressable)
        tam_high = q(high * households * addressable)

        return DemandEstimate(
            per_household_monthly=Band(
                low=low,
                point=per_hh,
                high=high,
                unit="₹/household/month",
                method=(
                    f"HCES rural MPCE ₹{mpce} × household size {size} × category share {share}, "
                    f"banded at ±{q(cv * 100, Decimal('1'))}% coefficient of variation"
                ),
                confidence=Confidence.MEDIUM,
                sources=("hces_2023_24",),
            ),
            addressable_market_monthly=Band(
                low=tam_low,
                point=tam_point,
                high=tam_high,
                unit="₹/month",
                method=(
                    f"per-household spend × {reach.households_now} households within "
                    f"{reach.radius_km} km × {addressable} addressable share"
                ),
                confidence=Confidence.MEDIUM,
                sources=("hces_2023_24", "census_pc11", "intercensal_scaling"),
            ),
            addressable_share=addressable,
            baseline_state_average=per_hh,
            method=self.name,
            notes=(
                "Baseline comparison (PLAN.md §3): the state average applied uniformly is the "
                f"point estimate ₹{per_hh}. The band is what this MVP adds; small-area estimation "
                "is what Model ② will add.",
            ),
        )


ESTIMATORS: dict[str, type[DemandEstimator]] = {HcesMeanBandEstimator.name: HcesMeanBandEstimator}


def get_estimator(name: str) -> DemandEstimator:
    if name not in ESTIMATORS:
        raise KeyError(f"unknown demand estimator {name!r}; have {sorted(ESTIMATORS)}")
    return ESTIMATORS[name]()
