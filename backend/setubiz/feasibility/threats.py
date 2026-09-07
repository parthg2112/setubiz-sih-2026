"""Threats — seasonality, monsoon exposure, buyer concentration (PLAN.md §4).

Arrivals volatility is the signal: a commodity whose mandi arrivals swing 4× across the year is a
cash-flow risk for anyone whose input or output rides on it.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from decimal import Decimal

from setubiz.data.loader import DataSource
from setubiz.feasibility.market_reach import MarketReach
from setubiz.money import q
from setubiz.schemas import Band, Confidence

#: Coefficient of variation above which arrivals count as strongly seasonal.
STRONG_SEASONALITY_CV = Decimal("0.45")


@dataclass(frozen=True)
class SeasonalityIndex:
    commodity: str
    market: str
    months: tuple[str, ...]
    arrivals: tuple[int, ...]
    modal_price: tuple[int, ...]
    coefficient_of_variation: Decimal
    peak_month: str
    trough_month: str
    peak_to_trough_ratio: Decimal
    is_strongly_seasonal: bool


@dataclass(frozen=True)
class Threat:
    id: str
    severity: str  # low | medium | high
    text_en: str
    text_hi: str
    cites: tuple[str, ...]


@dataclass(frozen=True)
class ThreatAssessment:
    threats: tuple[Threat, ...]
    seasonality: SeasonalityIndex | None
    price_band: Band | None
    mandis_in_radius: int
    sources: tuple[str, ...]


def _index(raw: dict) -> SeasonalityIndex:
    arrivals = [int(a) for a in raw["arrivals"]]
    mean = statistics.fmean(arrivals)
    cv = Decimal(str(statistics.pstdev(arrivals) / mean)) if mean else Decimal("0")
    peak_i = arrivals.index(max(arrivals))
    trough_i = arrivals.index(min(arrivals))
    ratio = Decimal(max(arrivals)) / Decimal(min(arrivals)) if min(arrivals) else Decimal("0")
    return SeasonalityIndex(
        commodity=raw["commodity"],
        market=raw["market"]["name"],
        months=tuple(raw["months"]),
        arrivals=tuple(arrivals),
        modal_price=tuple(int(p) for p in raw["modal_price"]),
        coefficient_of_variation=q(cv, Decimal("0.001")),
        peak_month=raw["months"][peak_i],
        trough_month=raw["months"][trough_i],
        peak_to_trough_ratio=q(ratio, Decimal("0.01")),
        is_strongly_seasonal=q(cv, Decimal("0.001")) >= STRONG_SEASONALITY_CV,
    )


def _price_band(index: SeasonalityIndex) -> Band:
    prices = [Decimal(p) for p in index.modal_price]
    return Band(
        low=min(prices),
        point=q(sum(prices) / len(prices), Decimal("1")),
        high=max(prices),
        unit=f"₹/quintal ({index.commodity})",
        method=f"12-month modal price spread at {index.market}",
        confidence=Confidence.MEDIUM,
        sources=("agmarknet_sample",),
    )


def assess(reach: MarketReach, category: str, source: DataSource) -> ThreatAssessment:
    raw = source.arrivals(category)
    index = _index(raw) if raw else None
    threats: list[Threat] = []

    if index and index.is_strongly_seasonal:
        threats.append(
            Threat(
                id="seasonal_arrivals",
                severity="high" if index.peak_to_trough_ratio >= 4 else "medium",
                text_en=(
                    f"{index.commodity} arrivals at {index.market} swing "
                    f"{index.peak_to_trough_ratio}× between {index.trough_month} and "
                    f"{index.peak_month}. Working capital must cover the lean months."
                ),
                text_hi=(
                    f"{index.market} में {index.commodity} की आवक {index.trough_month} से "
                    f"{index.peak_month} के बीच {index.peak_to_trough_ratio} गुना बदलती है। "
                    "कमजोर महीनों के लिए कार्यशील पूंजी रखें।"
                ),
                cites=("agmarknet_sample",),
            )
        )
    if raw and raw.get("monsoon_dependent"):
        threats.append(
            Threat(
                id="monsoon_dependency",
                severity="medium",
                text_en=(
                    "Input costs for this activity track the monsoon through fodder and feed "
                    "prices. A deficient year raises operating cost without raising revenue."
                ),
                text_hi=(
                    "इस व्यवसाय की लागत चारा एवं दाना के कारण मानसून पर निर्भर है। "
                    "कमजोर मानसून में लागत बढ़ती है पर आय नहीं।"
                ),
                cites=("agmarknet_sample",),
            )
        )
    if reach.mandis_in_radius < 2:
        threats.append(
            Threat(
                id="single_buyer",
                severity="high",
                text_en=(
                    f"Only {reach.mandis_in_radius} organised market within "
                    f"{reach.radius_km} km. Buyer concentration gives you little price bargaining "
                    "power. Line up a second buyer before scaling."
                ),
                text_hi=(
                    f"{reach.radius_km} किमी में केवल {reach.mandis_in_radius} बाज़ार है। "
                    "मोल-भाव की शक्ति कम रहेगी। विस्तार से पहले दूसरा खरीदार तय करें।"
                ),
                cites=("osm_sample",),
            )
        )
    if reach.road_connected_share < Decimal("0.6"):
        threats.append(
            Threat(
                id="road_access",
                severity="medium",
                text_en=(
                    f"Only {q(reach.road_connected_share * 100, Decimal('1'))}% of villages in "
                    "the catchment have a pucca road. Monsoon months will cut effective reach."
                ),
                text_hi=(
                    f"क्षेत्र के केवल {q(reach.road_connected_share * 100, Decimal('1'))}% गाँवों में "
                    "पक्की सड़क है। बरसात में पहुँच घट जाएगी।"
                ),
                cites=("shrug_sample",),
            )
        )

    return ThreatAssessment(
        threats=tuple(threats),
        seasonality=index,
        price_band=_price_band(index) if index else None,
        mandis_in_radius=reach.mandis_in_radius,
        sources=("agmarknet_sample", "osm_sample", "shrug_sample"),
    )
