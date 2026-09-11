"""Document readiness: what a checker may say, and about what.

Images never reach this layer. The browser does OCR on the device, the applicant confirms every
extracted field, and only the confirmed text arrives here. That is not an implementation detail:
it is the reason a caste certificate can be checked without it ever leaving the phone.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DocumentKind(str, Enum):
    QUOTATION = "quotation"
    INCOME_CERTIFICATE = "income_certificate"
    CASTE_CERTIFICATE = "caste_certificate"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    """Red, amber, green. Nothing is ever auto-rejected; red means stop and fix, not refused."""

    OK = "ok"
    WARNING = "warning"
    PROBLEM = "problem"


class CheckResult(BaseModel):
    """One deterministic finding. Bilingual at source, like every other engine output."""

    model_config = ConfigDict(frozen=True)

    id: str
    severity: Severity
    text_en: str
    text_hi: str
    #: Figures this finding quotes, so they can be grounded rather than trusted.
    figures: dict[str, Decimal] = Field(default_factory=dict)


class QuotedLine(BaseModel):
    """One line of an applicant's quotation, after they have confirmed it."""

    model_config = ConfigDict(frozen=True)

    description: str
    quantity: Decimal = Decimal(1)
    unit_rate: Decimal | None = None
    amount: Decimal


class MatchedLine(BaseModel):
    """A quoted line set against the template line it corresponds to."""

    model_config = ConfigDict(frozen=True)

    quoted: QuotedLine
    #: None when nothing matched. Unmatched lines are shown to the applicant, never forced.
    template_item: str | None
    template_amount: Decimal | None
    #: Positive means the quote is above the norm, as a percentage of the norm.
    excess_pct: Decimal | None
    severity: Severity


class QuotationFields(BaseModel):
    model_config = ConfigDict(frozen=True)

    vendor_name: str | None = None
    vendor_gstin: str | None = None
    quotation_date: str | None = None
    lines: tuple[QuotedLine, ...] = ()
    total_amount: Decimal | None = None


class IncomeCertificateFields(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicant_name: str | None = None
    annual_family_income: Decimal | None = None
    issue_date: str | None = None
    issuing_authority: str | None = None
    certificate_number: str | None = None
    state: str | None = None


class CasteCertificateFields(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicant_name: str | None = None
    category: str | None = None
    sub_caste: str | None = None
    issuing_authority: str | None = None
    issue_date: str | None = None
    certificate_number: str | None = None
    attestation_present: bool = False


class DocumentReport(BaseModel):
    """The verdict on one document. Advisory only: a human always decides."""

    model_config = ConfigDict(frozen=True)

    kind: DocumentKind
    checks: tuple[CheckResult, ...]
    matched_lines: tuple[MatchedLine, ...] = ()
    #: Extracted figures, keyed for the facts object.
    figures: dict[str, Decimal] = Field(default_factory=dict)
    sources: tuple[str, ...] = ("applicant_document",)

    @property
    def severity(self) -> Severity:
        """The worst finding. A document is only as ready as its weakest check."""
        if any(c.severity is Severity.PROBLEM for c in self.checks):
            return Severity.PROBLEM
        if any(c.severity is Severity.WARNING for c in self.checks):
            return Severity.WARNING
        return Severity.OK

    @property
    def ready(self) -> bool:
        return self.severity is Severity.OK
