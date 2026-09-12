"""HTTP surface. Thin: every endpoint delegates to the engines and returns their output."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from setubiz import __version__
from setubiz.config import get_settings
from setubiz.data.loader import get_data_source
from setubiz.documents import (
    CasteCertificateFields,
    DocumentKind,
    IncomeCertificateFields,
    QuotationFields,
    check_caste_certificate,
    check_income_certificate,
    check_names_match,
    check_quotation,
    classify,
    extract_caste_certificate,
    extract_income_certificate,
    extract_quotation,
)
from setubiz.eligibility import comparison_schemes, corporations
from setubiz.facts import build_facts
from setubiz.facts.builder import Facts
from setubiz.finance.amortization import MoratoriumMode, amortize
from setubiz.finance.cost_templates import find_template_for_category, list_templates
from setubiz.finance.rightsizing import right_size
from setubiz.finance.router import ActivityKind, route
from setubiz.matching.village_matcher import match_villages
from setubiz.money import q
from setubiz.narration import CATCH_RATE, local_narrator, narrate, select_narrator
from setubiz.narration.base import Report
from setubiz.narration.validator import ValidationReport
from setubiz.schemas import AdvisoryRequest, Language, VillageMatch

router = APIRouter(prefix="/api/v1")


class AdvisoryResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    facts: Facts
    report: Report
    validation: ValidationReport


class FinanceRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    margin: Decimal = Field(gt=0, description="Promoter margin money in rupees")
    business_category: str = "dairy"
    activity_kind: Literal["general", "plantation", "construction"] = "general"
    moratorium_mode: Literal["serviced", "capitalized"] = "serviced"
    #: Resize the unit before costing it. None keeps the template's published size.
    units: int | None = Field(default=None, gt=0, description="Unit size, e.g. number of animals")
    #: Sensitivity lever: 0.8 asks what happens if revenue comes in 20% under the template.
    #: Bounded because a what-if outside this range is not a sensitivity, it is a different
    #: business, and the cost template stops describing it.
    revenue_factor: Decimal | None = Field(
        default=None, gt=Decimal("0.5"), le=Decimal("1.5"), description="Revenue multiplier"
    )


@router.post("/advisory", response_model=AdvisoryResponse, summary="Run the full advisory pipeline")
def advisory(request: AdvisoryRequest, use_llm: bool | None = None) -> AdvisoryResponse:
    try:
        facts = build_facts(request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = narrate(facts, Language(request.language), use_llm=use_llm)
    return AdvisoryResponse(facts=facts, report=result.report, validation=result.validation)


@router.post("/finance/structure", summary="Finance engine only: max vs recommended loan")
def finance_structure(request: FinanceRequest) -> dict[str, Any]:
    template = find_template_for_category(request.business_category)
    if template is None:
        raise HTTPException(
            status_code=404, detail=f"no cost template for category {request.business_category!r}"
        )
    # Finance only. The feasibility layer (village lookup, competitor and demand estimation) is
    # untouched, which is what lets a slider recompute in milliseconds instead of re-running the
    # whole advisory pipeline.
    if request.units is not None:
        template = template.at_units(request.units)
    if request.revenue_factor is not None:
        template = template.model_copy(
            update={
                "monthly_revenue": tuple(
                    li.model_copy(update={"amount": q(li.amount * request.revenue_factor)})
                    for li in template.monthly_revenue
                )
            }
        )

    scheme = route(request.margin, ActivityKind(request.activity_kind))
    mode = MoratoriumMode(request.moratorium_mode)
    sizing = right_size(scheme, template, mode)

    def _schedule(loan: Decimal) -> dict[str, Any] | None:
        if loan <= 0:
            return None
        result = amortize(
            loan, scheme.annual_rate, scheme.total_quarters, scheme.moratorium_quarters, mode
        )
        return {
            "instalment": result.instalment,
            "final_instalment": result.final_instalment,
            "total_interest": result.total_interest,
            "total_outflow": result.total_outflow,
            "principal_amortized": result.principal_amortized,
            "rows": [row.__dict__ for row in result.schedule],
        }

    return {
        "scheme": scheme,
        "right_sizing": sizing,
        "schedules": {
            "max_loan": _schedule(scheme.max_loan),
            "recommended_loan": _schedule(sizing.recommended_loan),
        },
        "template": template,
    }


@router.get("/villages/search", response_model=list[VillageMatch], summary="Phonetic village match")
def villages_search(
    q: str = Query(min_length=1, description="Village name as spoken, typed or transcribed"),
    state: str | None = None,
    district: str | None = None,
    limit: int = Query(default=3, ge=1, le=10),
) -> list[VillageMatch]:
    return list(match_villages(q, get_data_source(), state=state, district=district, limit=limit))


@router.get("/states", summary="States with village data available")
def states() -> list[dict[str, Any]]:
    """What the wizard's state switcher can offer.

    Driven by the manifest, so a new state appears here the moment its shard is committed:
    the endpoint is the scalability contract for 'only Jharkhand today' being a data fact,
    not a code fact.
    """
    return [dict(s) for s in get_data_source().list_states()]


@router.get("/cost-templates", summary="NABARD-style unit cost templates")
def cost_templates() -> list[dict[str, Any]]:
    return [
        {
            **tpl.model_dump(),
            "fixed_capital_total": tpl.fixed_capital_total,
            "monthly_revenue_total": tpl.monthly_revenue_total,
            "monthly_opex_total": tpl.monthly_opex_total,
            "working_capital": tpl.working_capital,
            "required_capital": tpl.required_capital,
            "annual_noi": tpl.annual_noi,
        }
        for tpl in list_templates()
    ]


@router.get("/schemes", summary="Corporations and comparison schemes")
def schemes() -> dict[str, Any]:
    return {"corporations": corporations(), "comparison": comparison_schemes()}


@router.get("/metrics", summary="Validator catch rate and runtime configuration")
def metrics() -> dict[str, Any]:
    settings = get_settings()
    return {
        "version": __version__,
        "validator": CATCH_RATE.as_dict(),
        # The lane that would actually serve the next request, not the one that is configured.
        "narrator": select_narrator().name,
        "local_llm": local_narrator.describe(),
        "competitor_estimator": settings.competitor_estimator,
        "demand_estimator": settings.demand_estimator,
        "dscr_threshold": settings.dscr_threshold,
        "data_source": "sample" if get_data_source().synthetic else "live",
    }


class DocumentTextRequest(BaseModel):
    """OCR text, not an image.

    The endpoint deliberately cannot accept a file. OCR runs in the applicant's browser, so a
    caste certificate never leaves their device; accepting an upload here would quietly undo that
    and there would be no way to tell from the outside.
    """

    model_config = ConfigDict(frozen=True)

    text: str = Field(min_length=1, max_length=20000)


class DocumentCheckRequest(BaseModel):
    """Fields the applicant has already seen and confirmed."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["quotation", "income_certificate", "caste_certificate"]
    business_category: str = "dairy"
    social_category: str = "sc"
    margin: Decimal | None = Field(default=None, gt=0)
    units: int | None = Field(default=None, gt=0)
    months_old: int | None = Field(default=None, ge=0, le=600)
    quotation: QuotationFields | None = None
    income_certificate: IncomeCertificateFields | None = None
    caste_certificate: CasteCertificateFields | None = None
    #: Names read off other documents, for the cross-document consistency check.
    other_names: dict[str, str] = Field(default_factory=dict)


@router.post("/documents/read", summary="Classify OCR text and propose fields for confirmation")
def documents_read(request: DocumentTextRequest) -> dict[str, Any]:
    """Turn OCR text into proposed fields. Proposed, never applied: the applicant confirms.

    No verdict is returned here. Extraction is calibrated on typed text, not on photographs, so
    anything it produces has to pass through a human before it can mean anything.
    """
    kind, scores = classify(request.text)
    proposed: dict[str, Any] = {}
    if kind is DocumentKind.QUOTATION:
        proposed = extract_quotation(request.text).model_dump()
    elif kind is DocumentKind.INCOME_CERTIFICATE:
        proposed = extract_income_certificate(request.text).model_dump()
    elif kind is DocumentKind.CASTE_CERTIFICATE:
        proposed = extract_caste_certificate(request.text).model_dump()
    return {"kind": kind.value, "scores": scores, "proposed": proposed, "confirmed": False}


@router.post("/documents/check", summary="Deterministic checks on confirmed document fields")
def documents_check(request: DocumentCheckRequest) -> dict[str, Any]:
    """Judge a document against the published rules. Advisory only; nothing is auto-rejected."""
    if request.kind == "quotation":
        if request.quotation is None:
            raise HTTPException(status_code=422, detail="quotation fields are required")
        template = find_template_for_category(request.business_category)
        if template is None:
            raise HTTPException(
                status_code=404,
                detail=f"no cost template for category {request.business_category!r}",
            )
        if request.units is not None:
            template = template.at_units(request.units)
        report = check_quotation(
            request.quotation,
            template,
            margin=request.margin,
            months_old=request.months_old,
        )
    elif request.kind == "income_certificate":
        if request.income_certificate is None:
            raise HTTPException(status_code=422, detail="income certificate fields are required")
        report = check_income_certificate(
            request.income_certificate, request.social_category, months_old=request.months_old
        )
    else:
        if request.caste_certificate is None:
            raise HTTPException(status_code=422, detail="caste certificate fields are required")
        report = check_caste_certificate(
            request.caste_certificate, request.social_category, months_old=request.months_old
        )

    names = dict(request.other_names)
    for label, fields in (
        ("income certificate", request.income_certificate),
        ("caste certificate", request.caste_certificate),
    ):
        if fields is not None and fields.applicant_name:
            names[label] = fields.applicant_name
    name_check = check_names_match(names)

    checks = list(report.checks)
    if name_check is not None:
        checks.append(name_check)

    return {
        "kind": report.kind.value,
        "severity": report.severity.value,
        "ready": report.ready and (name_check is None or name_check.severity.value == "ok"),
        "checks": checks,
        "matched_lines": report.matched_lines,
        "figures": report.figures,
        "sources": report.sources,
    }
