"""Data access behind one protocol, so real SHRUG/Overpass/AGMARKNET adapters drop in later.

The MVP ships `SampleDataSource` (synthetic files — see data/sample/README.md). Nothing above this
module knows or cares where the rows came from; it only reads `Source.synthetic` for provenance.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from setubiz.config import get_settings
from setubiz.geo import haversine_km


class Village(BaseModel):
    model_config = ConfigDict(frozen=True)

    shrid: str
    name: str
    name_hi: str | None = None
    state: str
    district: str
    block: str
    lat: float
    lon: float
    households_2011: int
    population_2011: int
    literacy_rate: float
    sc_pct: float
    st_pct: float
    workers_pct: float
    has_bank: bool
    has_pucca_road: bool
    has_power: bool
    dist_to_town_km: float


class Poi(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    category: str
    osm_tag: str
    lat: float
    lon: float


class NeighbourVillage(BaseModel):
    model_config = ConfigDict(frozen=True)

    village: Village
    distance_km: float


@runtime_checkable
class DataSource(Protocol):
    """The seam between the estimation layer and whatever is actually supplying rows."""

    synthetic: bool

    def village_by_shrid(self, shrid: str) -> Village | None: ...
    def all_villages(self) -> tuple[Village, ...]: ...
    def villages_within(self, lat: float, lon: float, radius_km: float) -> tuple[NeighbourVillage, ...]: ...
    def pois_near(self, lat: float, lon: float, radius_km: float, category: str | None = None) -> tuple[Poi, ...]: ...
    def block_density(self, district: str, block: str, category: str) -> float | None: ...
    def district_density_stats(self, district: str, category: str) -> tuple[float, float] | None: ...
    def demand_profile(self, state: str, category: str) -> dict[str, Any] | None: ...
    def income_segments(self, state: str) -> tuple[dict[str, Any], ...]: ...
    def arrivals(self, category: str) -> dict[str, Any] | None: ...
    def source_ids(self) -> tuple[str, ...]: ...


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class SampleDataSource:
    """Reads the committed synthetic dataset. Deterministic, offline, zero dependencies."""

    synthetic = True

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().data_dir
        self._villages = tuple(
            Village.model_validate(v) for v in _read_json(self.root / "villages.json")["villages"]
        )
        self._pois = tuple(Poi.model_validate(p) for p in _read_json(self.root / "pois.json")["pois"])
        self._ec13 = _read_json(self.root / "ec13_density.json")
        self._hces = _read_json(self.root / "hces_demand.json")
        self._arrivals = _read_json(self.root / "arrivals.json")

    # --- geography ---

    def all_villages(self) -> tuple[Village, ...]:
        return self._villages

    def village_by_shrid(self, shrid: str) -> Village | None:
        return next((v for v in self._villages if v.shrid == shrid), None)

    def villages_within(
        self, lat: float, lon: float, radius_km: float
    ) -> tuple[NeighbourVillage, ...]:
        hits = [
            NeighbourVillage(village=v, distance_km=round(haversine_km(lat, lon, v.lat, v.lon), 2))
            for v in self._villages
        ]
        inside = [h for h in hits if h.distance_km <= radius_km]
        return tuple(sorted(inside, key=lambda h: h.distance_km))

    def pois_near(
        self, lat: float, lon: float, radius_km: float, category: str | None = None
    ) -> tuple[Poi, ...]:
        return tuple(
            p
            for p in self._pois
            if (category is None or p.category == category)
            and haversine_km(lat, lon, p.lat, p.lon) <= radius_km
        )

    # --- enterprise density (Economic Census 2013) ---

    def block_density(self, district: str, block: str, category: str) -> float | None:
        block_row = self._ec13["blocks"].get(block)
        if not block_row:
            return None
        return block_row.get(category)

    def district_density_stats(self, district: str, category: str) -> tuple[float, float] | None:
        stats = self._ec13["district_stats"].get(district, {}).get(category)
        if not stats:
            return None
        return float(stats["mean"]), float(stats["std"])

    # --- consumption (HCES) ---

    def demand_profile(self, state: str, category: str) -> dict[str, Any] | None:
        state_row = self._hces["states"].get(state)
        if not state_row:
            return None
        cat = state_row["categories"].get(category)
        if not cat:
            return None
        return {
            "rural_mpce": state_row["rural_mpce"],
            "avg_household_size": state_row["avg_household_size"],
            "all_india_rural_mpce": self._hces["all_india_rural_mpce"],
            **cat,
        }

    def income_segments(self, state: str) -> tuple[dict[str, Any], ...]:
        return tuple(self._hces["income_segments"].get(state, ()))

    # --- market arrivals (AGMARKNET) ---

    def arrivals(self, category: str) -> dict[str, Any] | None:
        commodity = self._arrivals["category_commodity_proxy"].get(category)
        if not commodity:
            return None
        series = self._arrivals["series"].get(commodity)
        if not series:
            return None
        return {
            "commodity": commodity,
            "market": self._arrivals["market"],
            "months": self._arrivals["months"],
            "monsoon_dependent": category in self._arrivals["monsoon_dependent_categories"],
            **series,
        }

    def source_ids(self) -> tuple[str, ...]:
        return ("shrug_sample", "osm_sample", "ec13_sample", "hces_sample", "agmarknet_sample")


@lru_cache
def get_data_source() -> DataSource:
    return SampleDataSource()
