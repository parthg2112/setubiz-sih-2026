"""Shared value objects. `Band` and `Source` are the currency of the estimation layer.

Estimates are always bands with a stated method — never bare point numbers. That is the honest
representation of what sparse rural data can support, and it is what the confidence badge renders.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from setubiz.money import ZERO, q


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
    #: The issuing authority. Named explicitly so a reader can see which official body published
    #: the figure, rather than inferring it from a dataset name.
    publisher: str | None = None
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


class GroupMember(BaseModel):
    """One member of a self-help group.

    Each member keeps their own social category and income, because eligibility is assessed per
    person even when the enterprise is shared. Averaging them would hide the member who fails.
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = None
    social_category: str = "sc"
    annual_family_income: Decimal | None = Field(default=None, ge=0)
    contribution: Decimal = Field(gt=0, description="This member's share of the margin money")
    is_woman: bool = False


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

    #: Empty is the single-applicant path, unchanged. A non-empty list turns on group mode, where
    #: pooled contributions become the margin and eligibility is assessed member by member.
    members: tuple[GroupMember, ...] = ()
    #: How the group instalment is shared out. Real SHGs do both.
    liability_split: Literal["equal", "proportional"] = "equal"

    @property
    def is_group(self) -> bool:
        return bool(self.members)

    @property
    def pooled_margin(self) -> Decimal:
        """The margin the finance engine sees. Falls back to `savings` for a single applicant."""
        if not self.members:
            return self.savings
        return q(sum((m.contribution for m in self.members), ZERO))

    @model_validator(mode="after")
    def _needs_a_village(self) -> AdvisoryRequest:
        if not self.village_shrid and not self.village_query:
            raise ValueError("provide either village_shrid or village_query")
        return self

    @model_validator(mode="after")
    def _a_group_needs_more_than_one_member(self) -> AdvisoryRequest:
        if self.members and len(self.members) < 2:
            raise ValueError("a group needs at least two members; omit members for one applicant")
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
