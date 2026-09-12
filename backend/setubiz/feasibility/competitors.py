"""Competitor density estimation — PLAN.md §3 Model ①.

The v0 shipped here is the deterministic EC13 z-score fallback the plan calls demo-safe. The
LightGBM model slots in behind the same protocol; the estimator name is recorded in the facts so a
report always states which method produced its band.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from setubiz.data.loader import DataSource, Village
from setubiz.finance.cost_templates import display_name
from setubiz.feasibility.market_reach import MarketReach
from setubiz.money import q
from setubiz.schemas import Advisory, Band, Confidence


@dataclass(frozen=True)
class CompetitorEstimate:
    band: Band
    osm_observed: int
    density_per_1k_households: Decimal
    district_mean_per_1k: Decimal | None
    z_score: Decimal | None
    method: str
    notes: tuple[Advisory, ...]


@runtime_checkable
class CompetitorEstimator(Protocol):
    name: str

    def estimate(
        self, centre: Village, reach: MarketReach, category: str, source: DataSource
    ) -> CompetitorEstimate: ...


class Ec13ZScoreEstimator:
    """Block enterprise density (EC13) × households in radius, floored by observed OSM POIs.

    Baseline to beat (PLAN.md §3): the raw OSM count alone. We report both, so the gap is visible.
    """

    name = "ec13_zscore"
    #: Band half-width as a share of the point estimate. Sparse rural data does not support
    #: anything tighter than a ±35% band, and pretending otherwise would be the dishonest move.
    BAND_SPREAD = Decimal("0.35")

    def estimate(
        self, centre: Village, reach: MarketReach, category: str, source: DataSource
    ) -> CompetitorEstimate:
        observed = len(source.pois_near(centre.lat, centre.lon, reach.radius_km, category))
        density = source.block_density(centre.state, centre.district, centre.block, category)
        stats = source.district_density_stats(centre.state, centre.district, category)
        notes: list[Advisory] = []

        if density is None:
            # No EC13 row for this block: fall back to the observed count as the point estimate.
            notes.append(
                Advisory(
                    id="no_ec13_row",
                    text_en=(
                        f"No Economic Census density for block {centre.block} and category "
                        f"{(display_name(category) or (category, category))[0]}; "
                        "falling back to the observed OSM count, which under-counts."
                    ),
                    text_hi=(
                        f"{centre.block} प्रखंड एवं {(display_name(category) or (category, category))[1]} "
                        "श्रेणी के लिए आर्थिक जनगणना का "
                        "घनत्व उपलब्ध नहीं; OSM की गिनती पर आधारित अनुमान, जो कम आँकता है।"
                    ),
                )
            )
            point = Decimal(observed)
            confidence = Confidence.LOW
            z = None
            mean = None
        else:
            per_1k = Decimal(str(density))
            point = q(per_1k * Decimal(reach.households_now) / 1000, Decimal("1"))
            if stats:
                mean, std = Decimal(str(stats[0])), Decimal(str(stats[1]))
                z = q((per_1k - mean) / std, Decimal("0.01")) if std else Decimal("0")
            else:
                mean, z = None, None
            confidence = Confidence.MEDIUM

        if point < observed:
            notes.append(
                Advisory(
                    id="raised_to_observed",
                    text_en=(
                        f"Estimate raised to the {observed} enterprises actually mapped in "
                        "OpenStreetMap. An observed count is a hard floor."
                    ),
                    text_hi=(
                        f"अनुमान बढ़ाकर {observed} किया गया, क्योंकि OpenStreetMap में इतनी इकाइयाँ "
                        "दर्ज हैं। देखी गई गिनती न्यूनतम सीमा है।"
                    ),
                )
            )
            point = Decimal(observed)

        low = q(point * (1 - self.BAND_SPREAD), Decimal("1"))
        high = q(point * (1 + self.BAND_SPREAD), Decimal("1"))
        low = max(low, Decimal(observed))

        density_per_1k = (
            q(point * 1000 / Decimal(reach.households_now), Decimal("0.01"))
            if reach.households_now
            else Decimal("0")
        )

        return CompetitorEstimate(
            band=Band(
                low=low,
                point=point,
                high=high,
                unit="enterprises",
                method=(
                    "Economic Census 2013 block density × households in radius, floored by "
                    "observed OSM points of interest"
                ),
                confidence=confidence,
                sources=("economic_census_2013", "openstreetmap", "census_pc11"),
            ),
            osm_observed=observed,
            density_per_1k_households=density_per_1k,
            district_mean_per_1k=mean,
            z_score=z,
            method=self.name,
            notes=tuple(notes),
        )


class LightgbmDensityEstimator:
    """PLAN.md §3 Model ① — LightGBM on log(enterprises/1k households), states held out.

    Deliberately unimplemented in the MVP: it needs Udyam district×activity labels whose
    granularity is still unverified. Registered so the swap is a config change, not a refactor.
    """

    name = "lightgbm_density"

    def estimate(
        self, centre: Village, reach: MarketReach, category: str, source: DataSource
    ) -> CompetitorEstimate:
        raise NotImplementedError(
            "Model ① is not trained yet (PLAN.md §3). Set SETUBIZ_COMPETITOR_ESTIMATOR="
            "ec13_zscore to use the deterministic fallback."
        )


ESTIMATORS: dict[str, type[CompetitorEstimator]] = {
    Ec13ZScoreEstimator.name: Ec13ZScoreEstimator,
    LightgbmDensityEstimator.name: LightgbmDensityEstimator,
}


def get_estimator(name: str) -> CompetitorEstimator:
    if name not in ESTIMATORS:
        raise KeyError(f"unknown competitor estimator {name!r}; have {sorted(ESTIMATORS)}")
    return ESTIMATORS[name]()
