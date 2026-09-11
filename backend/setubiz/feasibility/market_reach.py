"""Market reach — who is actually within reach, scaled from 2011 to today (PLAN.md §4)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from setubiz.config import get_settings
from setubiz.data.loader import DataSource, NeighbourVillage, Village
from setubiz.money import q


@dataclass(frozen=True)
class IncomeSegment:
    label: str
    share: Decimal
    households: int


@dataclass(frozen=True)
class MarketReach:
    centre: Village
    radius_km: float
    neighbours: tuple[NeighbourVillage, ...]
    villages_in_radius: int
    households_2011: int
    population_2011: int
    growth_factor: Decimal
    households_now: int
    population_now: int
    reference_year: int
    income_segments: tuple[IncomeSegment, ...]
    mandis_in_radius: int
    villages_with_bank: int
    road_connected_share: Decimal
    sources: tuple[str, ...]


def growth_factor_for(district: str) -> Decimal:
    """2011 is the only village-level base that exists; scale it, and say so (PLAN.md §10)."""
    table = get_settings().intercensal_growth
    key = district.strip().lower()
    return Decimal(str(table.get(key, table["_default"])))


def compute(
    centre: Village,
    source: DataSource,
    radius_km: float | None = None,
    reference_year: int = 2026,
) -> MarketReach:
    settings = get_settings()
    radius = radius_km if radius_km is not None else settings.default_radius_km
    neighbours = source.villages_within(centre.lat, centre.lon, radius)

    households_2011 = sum(n.village.households_2011 for n in neighbours)
    population_2011 = sum(n.village.population_2011 for n in neighbours)
    factor = growth_factor_for(centre.district)
    households_now = int(Decimal(households_2011) * factor)
    population_now = int(Decimal(population_2011) * factor)

    segments = tuple(
        IncomeSegment(
            label=row["label"],
            share=Decimal(str(row["share"])),
            households=int(Decimal(households_now) * Decimal(str(row["share"]))),
        )
        for row in source.income_segments(centre.state)
    )

    mandis = len(source.pois_near(centre.lat, centre.lon, radius, "mandi"))
    banks = sum(1 for n in neighbours if n.village.has_bank)
    road_share = (
        q(
            Decimal(sum(1 for n in neighbours if n.village.has_pucca_road)) / len(neighbours),
            Decimal("0.01"),
        )
        if neighbours
        else Decimal("0")
    )

    return MarketReach(
        centre=centre,
        radius_km=radius,
        neighbours=neighbours,
        villages_in_radius=len(neighbours),
        households_2011=households_2011,
        population_2011=population_2011,
        growth_factor=factor,
        households_now=households_now,
        population_now=population_now,
        reference_year=reference_year,
        income_segments=segments,
        mandis_in_radius=mandis,
        villages_with_bank=banks,
        road_connected_share=road_share,
        sources=(
            "census_pc11",
            "mission_antyodaya",  # bank / pucca road flags below come from the 2019 survey
            "intercensal_scaling",
            "openstreetmap",
            "hces_2023_24",
        ),
    )
