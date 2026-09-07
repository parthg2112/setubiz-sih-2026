"""HTTP surface. Thin: every endpoint delegates to the engines and returns their output."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from setubiz import __version__
from setubiz.config import get_settings
from setubiz.data.loader import get_data_source
from setubiz.eligibility import comparison_schemes, corporations
from setubiz.facts import build_facts
from setubiz.facts.builder import Facts
from setubiz.finance.amortization import MoratoriumMode, amortize
from setubiz.finance.cost_templates import find_template_for_category, list_templates
from setubiz.finance.rightsizing import right_size
from setubiz.finance.router import ActivityKind, route
from setubiz.matching.village_matcher import match_villages
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
