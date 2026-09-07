"""Shared value objects. `Band` and `Source` are the currency of the estimation layer.

Estimates are always bands with a stated method — never bare point numbers. That is the honest
representation of what sparse rural data can support, and it is what the confidence badge renders.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceKind(str, Enum):
    CENSUS = "census"
    OSM = "osm"
    ECONOMIC_CENSUS = "economic_census"
    CONSUMPTION_SURVEY = "consumption_survey"
    MARKET_PRICES = "market_prices"
    SCHEME = "scheme"
    COST_TEMPLATE = "cost_template"
    COMPUTED = "computed"


class Source(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    kind: SourceKind
    url: str | None = None
    year: str | None = None
    #: True when the underlying rows are the committed synthetic placeholders.
    synthetic: bool = False
    note: str | None = None


class Band(BaseModel):
    """A low/point/high estimate with the method that produced it."""

    model_config = ConfigDict(frozen=True)

    low: Decimal
    point: Decimal
    high: Decimal
    unit: str
    method: str
    confidence: Confidence = Confidence.MEDIUM
    sources: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _ordered(self) -> Band:
        if not (self.low <= self.point <= self.high):
            raise ValueError(f"band must satisfy low ≤ point ≤ high, got {self}")
        return self

    @property
    def width_ratio(self) -> Decimal:
        """How wide the band is relative to its centre — the uncertainty we are admitting."""
        if self.point == 0:
            return Decimal("0")
        return (self.high - self.low) / self.point


class Language(str, Enum):
    EN = "en"
    HI = "hi"


class Advisory(BaseModel):
    """A bilingual note the engines emit. Both languages are written at source — a report must
    never fall back to showing English text under a Hindi heading."""

    model_config = ConfigDict(frozen=True)

    id: str
    text_en: str
    text_hi: str

    def text(self, language: Language | str = Language.EN) -> str:
        return self.text_hi if Language(language) is Language.HI else self.text_en


class AdvisoryRequest(BaseModel):
    """What the voice/PWA layer collects before anything is computed."""

    model_config = ConfigDict(frozen=True)

    village_shrid: str | None = None
    village_query: str | None = None
    state: str = "Jharkhand"
    savings: Decimal = Field(gt=0, description="Promoter margin money in rupees")
    business_category: str
    social_category: str = "sc"
    annual_family_income: Decimal | None = Field(default=None, ge=0)
    is_woman: bool = False
    has_prior_experience: bool = True
    radius_km: float = Field(default=10.0, gt=0, le=50)
    moratorium_mode: Literal["serviced", "capitalized"] = "serviced"
    activity_kind: Literal["general", "plantation", "construction"] = "general"
    language: Language = Language.EN

    @model_validator(mode="after")
    def _needs_a_village(self) -> AdvisoryRequest:
        if not self.village_shrid and not self.village_query:
            raise ValueError("provide either village_shrid or village_query")
        return self


class VillageMatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    shrid: str
    name: str
    name_hi: str | None
    block: str
    district: str
    state: str
    score: float
    reason: str
