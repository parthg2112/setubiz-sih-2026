"""CLI — a demo path that needs no browser and no network."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from setubiz.data.loader import get_data_source
from setubiz.facts import build_facts
from setubiz.matching.village_matcher import match_villages
from setubiz.money import format_inr, money
from setubiz.narration import narrate
from setubiz.schemas import AdvisoryRequest, Language

app = typer.Typer(help="SetuBiz — rural business advisory and financial structuring.", no_args_is_help=True)
console = Console()


@app.command()
def advise(
    village: Annotated[str, typer.Option(help="Village name, as spoken or typed")],
    savings: Annotated[float, typer.Option(help="Promoter margin money in rupees")],
    category: Annotated[str, typer.Option(help="Business category, e.g. dairy")] = "dairy",
    social_category: Annotated[str, typer.Option(help="sc | safai_karamchari | obc | ebc")] = "sc",
    income: Annotated[float | None, typer.Option(help="Annual family income")] = None,
    state: str = "Jharkhand",
    radius_km: float = 10.0,
    lang: Annotated[str, typer.Option(help="en | hi")] = "en",
    moratorium_mode: str = "serviced",
    out: Annotated[Path | None, typer.Option(help="Write facts.json here")] = None,
) -> None:
    """Produce a full advisory report and optionally lock the facts to disk."""
    request = AdvisoryRequest(
        village_query=village,
        state=state,
        savings=money(savings),
        business_category=category,
        social_category=social_category,
        annual_family_income=None if income is None else money(income),
        radius_km=radius_km,
        moratorium_mode=moratorium_mode,  # type: ignore[arg-type]
        language=Language(lang),
    )
    facts = build_facts(request)
    result = narrate(facts, Language(lang))
    rs = facts.right_sizing

    console.print(
        Panel(
            f"[bold]{facts.village.name}[/bold] · {facts.village.block} block · {facts.village.district}\n"
            f"[red]Maximum permissible loan   {format_inr(rs.max_loan)}[/red]   "
            f"(worst-year DSCR {rs.max_loan_min_dscr})\n"
            f"[green]Right-sized recommendation {format_inr(rs.recommended_loan)}[/green]   "
            f"(worst-year DSCR {rs.recommended_min_dscr}, limited by {rs.binding.value})",
            title="Capacity to borrow is not capacity to repay",
        )
    )

    for section in result.report.sections:
        console.print(f"\n[bold cyan]{section.heading}[/bold cyan]")
        console.print(section.body)

    if rs.recommended_dscr:
        table = Table(title="Debt service coverage by loan year", show_edge=False)
        for column in ("Year", "Net income", "Debt service", "DSCR", "Passes"):
            table.add_column(column)
        for row in rs.recommended_dscr:
            table.add_row(
                str(row.year),
                format_inr(row.noi),
                format_inr(row.debt_service),
                str(row.dscr),
                "yes" if row.passes else "NO",
            )
        console.print()
        console.print(table)

    console.print(
        f"\n[dim]Numeric grounding: {result.validation.grounded}/{result.validation.checked} "
        f"figures grounded · passed={result.validation.passed}[/dim]"
    )
    if facts.contains_synthetic_data:
        console.print("[yellow]Report built on synthetic sample data — not for citation.[/yellow]")

    if out:
        out.write_text(facts.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"[dim]facts written to {out}[/dim]")


@app.command("match")
def match(
    query: Annotated[str, typer.Argument(help="Village name to resolve")],
    state: str | None = None,
    limit: int = 3,
) -> None:
    """Show the phonetic matcher's top candidates, as the confirmation UI would."""
    matches = match_villages(query, get_data_source(), state=state, limit=limit)
    if not matches:
        console.print(f"[red]No village matched {query!r}.[/red]")
        raise typer.Exit(code=1)
    table = Table(title=f"Matches for {query!r}", show_edge=False)
    for column in ("Village", "Block", "District", "Score", "Why"):
        table.add_column(column)
    for m in matches:
        table.add_row(f"{m.name} ({m.name_hi})", m.block, m.district, f"{m.score:.3f}", m.reason)
    console.print(table)


@app.command("templates")
def templates() -> None:
    """List the NABARD-style cost templates and their unit economics."""
    from setubiz.finance.cost_templates import list_templates

    table = Table(title="Cost templates", show_edge=False)
    for column in ("Id", "Unit", "Required capital", "Monthly net", "Annual NOI"):
        table.add_column(column)
    for tpl in list_templates():
        table.add_row(
            tpl.id,
            tpl.unit,
            format_inr(tpl.required_capital),
            format_inr(tpl.monthly_net),
            format_inr(tpl.annual_noi),
        )
    console.print(table)


@app.command("facts")
def facts_command(
    village: str,
    savings: float,
    category: str = "dairy",
    out: Path = Path("facts.json"),
) -> None:
    """Write the locked facts object without narrating it."""
    request = AdvisoryRequest(village_query=village, savings=money(savings), business_category=category)
    payload = json.loads(build_facts(request).model_dump_json())
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"wrote {out} ({len(payload['numeric_index'])} indexed figures)")


if __name__ == "__main__":
    app()
