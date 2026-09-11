"""Document readiness — the checks are code, and a photograph never decides anything.

The architecture rule from the spec is the thing under test here: OCR and extraction may be
wrong, and the design survives that because every field is confirmed by the applicant and every
verdict is a comparison against a published figure.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from setubiz.documents import (
    CasteCertificateFields,
    DocumentKind,
    IncomeCertificateFields,
    QuotationFields,
    QuotedLine,
    Severity,
    check_caste_certificate,
    check_income_certificate,
    check_names_match,
    check_quotation,
    classify,
    extract_caste_certificate,
    extract_income_certificate,
    extract_quotation,
)
from setubiz.finance import load_template
from setubiz.money import money

FAIR_QUOTATION = """QUOTATION
Vendor: Ranchi Dairy Supplies
GSTIN: 20ABCDE1234F1Z5
Date: 14/03/2026
Semi-pucca cattle shed          1    140000    140000
2 crossbred cows                2     75000    150000
Chaff cutter and equipment      1     25000     25000
Milk cans and utensils          1      8000      8000
Cattle insurance premium        1     12000     12000
Transport of animals            1      6000      6000
Fodder plot development         1      5000      5000
Total                                          346000
"""

INFLATED_QUOTATION = """QUOTATION
Semi-pucca cattle shed          1    240000    240000
2 crossbred cows                2     90000    180000
Chaff cutter and equipment      1     40000     40000
Milk cans and utensils          1     15000     15000
Cattle insurance premium        1     20000     20000
Transport of animals            1     12000     12000
Fodder plot development         1     13000     13000
Total                                          520000
"""

INCOME_CERTIFICATE = """GOVERNMENT OF JHARKHAND
INCOME CERTIFICATE
Name: Sunita Devi
Annual family income: Rs 2,80,000
Certificate No: JH/INC/2026/44821
Date: 14/03/2026
Tehsildar, Ormanjhi
State: Jharkhand
"""

CASTE_CERTIFICATE = """GOVERNMENT OF JHARKHAND
CASTE CERTIFICATE
Name: Sunita Devi
This is to certify that the applicant belongs to the Scheduled Caste category.
Certificate No: JH/CST/2026/1902
Date: 02/02/2026
Tehsildar, Ormanjhi
Seal and signature affixed
"""


# --- classification -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (FAIR_QUOTATION, DocumentKind.QUOTATION),
        (INCOME_CERTIFICATE, DocumentKind.INCOME_CERTIFICATE),
        (CASTE_CERTIFICATE, DocumentKind.CASTE_CERTIFICATE),
    ],
)
def test_documents_are_classified_without_a_model(text, expected):
    kind, scores = classify(text)
    assert kind is expected
    # Every score is reported, so a wrong answer can be argued with rather than just disbelieved.
    assert set(scores) == {k.value for k in DocumentKind if k is not DocumentKind.UNKNOWN}


def test_an_unrecognisable_page_says_so_rather_than_guessing():
    kind, _ = classify("this page is a receipt for two cups of tea")
    assert kind is DocumentKind.UNKNOWN


def test_a_table_of_amounts_reads_as_a_quotation_even_without_a_header():
    kind, _ = classify("Shed 1 140000 140000\nCows 2 75000 150000\nCutter 1 25000 25000")
    assert kind is DocumentKind.QUOTATION


# --- extraction ---------------------------------------------------------------------------


def test_quotation_extraction_skips_header_rows_that_merely_contain_digits():
    """A GSTIN and a date are not purchases, and comparing them to a cost norm is nonsense."""
    fields = extract_quotation(FAIR_QUOTATION)
    descriptions = [li.description for li in fields.lines]
    assert len(fields.lines) == 7
    assert not any("gstin" in d.lower() or "date" in d.lower() for d in descriptions)
    assert fields.vendor_gstin == "20ABCDE1234F1Z5"
    assert fields.quotation_date == "14/03/2026"
    assert fields.total_amount == money(346000)


def test_quantity_is_only_believed_when_it_reconstructs_the_amount():
    fields = extract_quotation(FAIR_QUOTATION)
    cows = next(li for li in fields.lines if "cows" in li.description)
    assert cows.quantity == 2
    assert cows.unit_rate == money(75000)
    assert cows.amount == money(150000)


def test_income_certificate_extraction_finds_the_figure_that_matters():
    fields = extract_income_certificate(INCOME_CERTIFICATE)
    assert fields.annual_family_income == money(280000)
    assert fields.issuing_authority is not None
    assert "Tehsildar" in fields.issuing_authority
    assert fields.certificate_number == "JH/INC/2026/44821"


def test_caste_certificate_extraction_finds_category_and_attestation():
    fields = extract_caste_certificate(CASTE_CERTIFICATE)
    assert fields.category == "sc"
    assert fields.attestation_present is True
    assert fields.issuing_authority is not None and "Tehsildar" in fields.issuing_authority


def test_extraction_returns_nothing_rather_than_guessing():
    """A blank the applicant fills in is a form field; a confident wrong number is a wrong loan."""
    fields = extract_income_certificate("a blurred page with no readable labels")
    assert fields.annual_family_income is None
    assert fields.issuing_authority is None


# --- quotation checks ----------------------------------------------------------------------


def test_a_fair_quotation_passes(dairy):
    report = check_quotation(extract_quotation(FAIR_QUOTATION), dairy, margin=money(100000))
    assert report.kind is DocumentKind.QUOTATION
    assert report.ready is True
    assert report.severity is Severity.OK
    assert all(m.template_item for m in report.matched_lines), "every line should have matched"


def test_an_inflated_quotation_is_caught_line_by_line(dairy):
    report = check_quotation(extract_quotation(INFLATED_QUOTATION), dairy, margin=money(100000))
    assert report.severity is Severity.PROBLEM
    shed = next(m for m in report.matched_lines if "shed" in m.quoted.description.lower())
    assert shed.template_amount == money(140000)
    assert shed.excess_pct == Decimal("71.4")
    assert shed.severity is Severity.PROBLEM


def test_an_inflated_quotation_reports_what_it_does_to_the_loan(dairy):
    """The point of the feature: a photograph connected to the project's core insight."""
    report = check_quotation(extract_quotation(INFLATED_QUOTATION), dairy, margin=money(100000))
    impact = next(c for c in report.checks if c.id == "dscr_impact")
    coverage = report.figures["dscr_if_quotation_funded"]
    assert coverage < Decimal("1.5"), "an inflated quote must show coverage below the norm"
    assert str(coverage) in impact.text_en
    assert impact.text_en and impact.text_hi


def test_arithmetic_that_does_not_add_up_is_a_problem(dairy):
    fields = QuotationFields(
        lines=(
            QuotedLine(description="Cattle shed", amount=money(140000)),
            QuotedLine(description="Crossbred cows", amount=money(150000)),
        ),
        total_amount=money(400000),
    )
    report = check_quotation(fields, dairy)
    arithmetic = next(c for c in report.checks if c.id == "arithmetic")
    assert arithmetic.severity is Severity.PROBLEM
    # Indian digit grouping, so the real sum reads Rs 2,90,000.
    assert "2,90,000" in arithmetic.text_en
    assert arithmetic.figures["quotation_line_sum"] == money(290000)


def test_an_unmatched_line_is_left_unmatched_rather_than_forced(dairy):
    fields = QuotationFields(
        lines=(QuotedLine(description="Ceremonial ribbon cutting", amount=money(9000)),)
    )
    report = check_quotation(fields, dairy)
    assert report.matched_lines[0].template_item is None
    uncategorised = next(c for c in report.checks if c.id == "uncategorised_lines")
    assert uncategorised.severity is Severity.WARNING
    assert "not compared" in uncategorised.text_en


def test_vendor_wording_is_matched_through_synonyms(dairy):
    """Vendors write "HF cattle", not "2 crossbred cows @ Rs 75,000"."""
    fields = QuotationFields(
        lines=(
            QuotedLine(description="HF milch cattle 2 nos", amount=money(150000)),
            QuotedLine(description="Cattle shelter civil work", amount=money(140000)),
        )
    )
    report = check_quotation(fields, dairy)
    assert all(m.template_item is not None for m in report.matched_lines)


def test_a_stale_quotation_is_flagged_as_needing_a_fresh_one(dairy):
    report = check_quotation(extract_quotation(FAIR_QUOTATION), dairy, months_old=8)
    age = next(c for c in report.checks if c.id == "quotation_age")
    assert age.severity is Severity.WARNING


def test_a_recent_quotation_raises_no_age_flag(dairy):
    report = check_quotation(extract_quotation(FAIR_QUOTATION), dairy, months_old=1)
    assert not any(c.id == "quotation_age" for c in report.checks)


# --- income certificate --------------------------------------------------------------------


def test_income_within_the_ceiling_is_a_real_verdict_not_a_presence_check():
    fields = extract_income_certificate(INCOME_CERTIFICATE)
    report = check_income_certificate(fields, "sc")
    ceiling = next(c for c in report.checks if c.id == "income_ceiling")
    assert ceiling.severity is Severity.OK
    assert report.figures["document_annual_family_income"] == money(280000)
    assert report.figures["document_income_ceiling"] == money(500000)


def test_income_over_the_ceiling_is_a_problem():
    fields = IncomeCertificateFields(
        annual_family_income=money(620000), issuing_authority="Tehsildar, Ormanjhi"
    )
    report = check_income_certificate(fields, "sc")
    assert report.severity is Severity.PROBLEM


def test_the_ceiling_applied_is_the_one_the_routing_already_decided():
    """NBCFDC is Rs 3.00 L, not NSFDC's Rs 5.00 L, and the rule engine already knows that."""
    fields = IncomeCertificateFields(
        annual_family_income=money(400000), issuing_authority="Tehsildar, Ormanjhi"
    )
    assert check_income_certificate(fields, "sc").severity is Severity.OK
    assert check_income_certificate(fields, "obc").severity is Severity.PROBLEM


def test_a_corporation_without_a_ceiling_says_so():
    fields = IncomeCertificateFields(
        annual_family_income=money(900000), issuing_authority="Tehsildar, Ormanjhi"
    )
    report = check_income_certificate(fields, "safai_karamchari")
    ceiling = next(c for c in report.checks if c.id == "income_ceiling")
    assert ceiling.severity is Severity.OK
    assert "no ceiling" in ceiling.text_en.lower()


def test_an_unrouted_category_has_no_scheme_ceiling_to_apply():
    fields = IncomeCertificateFields(
        annual_family_income=money(400000), issuing_authority="Tehsildar, Ormanjhi"
    )
    report = check_income_certificate(fields, "general")
    ceiling = next(c for c in report.checks if c.id == "income_ceiling")
    assert ceiling.severity is Severity.WARNING


def test_an_unreadable_income_is_a_problem_not_a_pass():
    report = check_income_certificate(IncomeCertificateFields(), "sc")
    assert report.severity is Severity.PROBLEM
    assert any(c.id == "income_read" for c in report.checks)


@pytest.mark.parametrize(
    ("authority", "severity"),
    [
        ("Tehsildar, Ormanjhi", Severity.OK),
        ("Sub Divisional Magistrate, Ranchi", Severity.OK),
        ("Gram Panchayat, Ormanjhi", Severity.PROBLEM),
        ("Mukhiya, Ormanjhi", Severity.PROBLEM),
        ("Office of the Notary", Severity.WARNING),
        (None, Severity.WARNING),
    ],
)
def test_the_issuing_authority_must_be_competent(authority, severity):
    """A village-level officer cannot issue these, and that is a common rejection cause."""
    fields = IncomeCertificateFields(
        annual_family_income=money(280000), issuing_authority=authority
    )
    report = check_income_certificate(fields, "sc")
    assert next(c for c in report.checks if c.id == "income_authority").severity is severity


def test_a_stale_certificate_is_flagged_and_a_fresh_one_is_not():
    fields = IncomeCertificateFields(
        annual_family_income=money(280000), issuing_authority="Tehsildar, Ormanjhi"
    )
    stale = check_income_certificate(fields, "sc", months_old=18)
    fresh = check_income_certificate(fields, "sc", months_old=2)
    assert next(c for c in stale.checks if c.id == "income_validity").severity is Severity.WARNING
    assert next(c for c in fresh.checks if c.id == "income_validity").severity is Severity.OK


# --- caste certificate ---------------------------------------------------------------------


def test_a_matching_category_routes_to_the_right_corporation():
    report = check_caste_certificate(extract_caste_certificate(CASTE_CERTIFICATE), "sc")
    match = next(c for c in report.checks if c.id == "category_match")
    assert match.severity is Severity.OK
    assert "National Scheduled Castes" in match.text_en


def test_a_category_mismatch_is_a_problem_because_it_misroutes_the_application():
    report = check_caste_certificate(extract_caste_certificate(CASTE_CERTIFICATE), "obc")
    match = next(c for c in report.checks if c.id == "category_match")
    assert match.severity is Severity.PROBLEM
    assert "wrong corporation" in match.text_en


def test_a_category_no_corporation_serves_is_reported_as_such():
    fields = CasteCertificateFields(
        category="st", issuing_authority="Tehsildar, Ormanjhi", attestation_present=True
    )
    report = check_caste_certificate(fields, "st")
    match = next(c for c in report.checks if c.id == "category_match")
    assert match.severity is Severity.WARNING


def test_an_unreadable_category_is_a_problem():
    report = check_caste_certificate(CasteCertificateFields(), "sc")
    assert any(c.id == "category_read" and c.severity is Severity.PROBLEM for c in report.checks)


def test_a_missing_seal_is_flagged():
    with_seal = CasteCertificateFields(category="sc", attestation_present=True)
    without = CasteCertificateFields(category="sc", attestation_present=False)
    assert (
        next(
            c for c in check_caste_certificate(with_seal, "sc").checks if c.id == "attestation"
        ).severity
        is Severity.OK
    )
    assert (
        next(
            c for c in check_caste_certificate(without, "sc").checks if c.id == "attestation"
        ).severity
        is Severity.WARNING
    )


def test_caste_certificate_validity_is_checked_too():
    fields = CasteCertificateFields(category="sc", attestation_present=True)
    stale = check_caste_certificate(fields, "sc", months_old=24)
    assert next(c for c in stale.checks if c.id == "caste_validity").severity is Severity.WARNING


# --- cross document ------------------------------------------------------------------------


def test_a_name_mismatch_across_documents_is_flagged():
    """Sunita Devi against Sunita Kumari is exactly the case the spec names."""
    result = check_names_match(
        {"income certificate": "Sunita Devi", "caste certificate": "Sunita Kumari"}
    )
    assert result is not None and result.severity is Severity.WARNING
    assert "Sunita Devi" in result.text_en


def test_a_consistent_name_passes():
    result = check_names_match(
        {"income certificate": "Sunita Devi", "caste certificate": "  sunita  devi "}
    )
    assert result is not None and result.severity is Severity.OK


def test_one_document_alone_cannot_contradict_itself():
    assert check_names_match({"income certificate": "Sunita Devi"}) is None
    assert check_names_match({"income certificate": None, "caste certificate": ""}) is None


def test_every_finding_is_written_in_both_languages(dairy):
    """A Hindi report must never fall back to English under a Hindi heading."""
    reports = [
        check_quotation(extract_quotation(INFLATED_QUOTATION), dairy, margin=money(100000)),
        check_income_certificate(extract_income_certificate(INCOME_CERTIFICATE), "sc"),
        check_caste_certificate(extract_caste_certificate(CASTE_CERTIFICATE), "obc"),
    ]
    for report in reports:
        for check in report.checks:
            assert check.text_en.strip(), f"{check.id} has no English"
            assert check.text_hi.strip(), f"{check.id} has no Hindi"


def test_a_report_is_only_as_ready_as_its_weakest_check(dairy):
    report = check_quotation(extract_quotation(INFLATED_QUOTATION), dairy)
    assert report.ready is False
    assert report.severity is Severity.PROBLEM


def test_the_template_is_the_only_source_of_the_norm(dairy):
    """No figure in a verdict may be invented; every one traces to the cost template."""
    report = check_quotation(extract_quotation(FAIR_QUOTATION), dairy)
    assert report.figures["template_fixed_capital"] == dairy.fixed_capital_total
    assert report.sources == ("applicant_document",)


def test_a_quotation_with_no_stated_total_falls_back_to_the_line_sum(dairy):
    fields = QuotationFields(
        lines=(QuotedLine(description="Semi-pucca cattle shed", amount=money(140000)),)
    )
    report = check_quotation(fields, dairy)
    assert report.figures["quotation_total"] == money(140000)
    assert not any(c.id == "arithmetic" for c in report.checks)


def test_a_quotation_at_or_below_the_norm_triggers_no_loan_warning(dairy):
    report = check_quotation(extract_quotation(FAIR_QUOTATION), dairy, margin=money(100000))
    assert not any(c.id == "dscr_impact" for c in report.checks)


def test_the_dairy_template_is_the_one_being_compared_against():
    assert load_template("dairy_2_animal").fixed_capital_total == money(346000)


# --- the edges that decide whether a bad photograph becomes a bad verdict -------------------


def test_rows_that_are_not_purchases_are_skipped():
    """Blank lines, column rulers, page numbers and stray totals are not line items."""
    text = """QUOTATION

    |    |    |
    1
    Semi-pucca cattle shed          1    140000    140000
    Tea for the meeting                              40
    """
    fields = extract_quotation(text)
    assert [li.description for li in fields.lines] == ["Semi-pucca cattle shed"]


def test_a_gstin_on_its_own_line_is_not_a_purchase():
    """Without a label to catch it, the GSTIN pattern itself has to."""
    fields = extract_quotation("20ABCDE1234F1Z5\nSemi-pucca cattle shed 1 140000 140000")
    assert [li.description for li in fields.lines] == ["Semi-pucca cattle shed"]


def test_an_unreadable_amount_is_dropped_rather_than_guessed():
    from setubiz.documents.extract import _to_decimal

    assert _to_decimal("1,40,000") == money(140000)
    assert _to_decimal("") is None
    assert _to_decimal("....") is None


def test_a_line_with_no_description_cannot_be_matched(dairy):
    from setubiz.documents.checks import _match_line

    assert _match_line("   ", dairy) is None


def test_a_moderately_high_quotation_is_amber_not_red(dairy):
    """Between 20% and 50% above the norm is worth saying, not worth stopping for."""
    # The lines must add up, or the arithmetic check fires and masks what is being tested.
    fields = QuotationFields(
        # Every line 30% above its norm, so no single line crosses the 50% red line either.
        lines=(
            QuotedLine(description="Semi-pucca cattle shed", amount=money(182000)),
            QuotedLine(description="2 crossbred cows", amount=money(195000)),
            QuotedLine(description="Chaff cutter and equipment", amount=money(32500)),
            QuotedLine(description="Milk cans and utensils", amount=money(10400)),
            QuotedLine(description="Cattle insurance premium", amount=money(15600)),
            QuotedLine(description="Transport of animals", amount=money(7800)),
            QuotedLine(description="Fodder plot development", amount=money(6500)),
        ),
        total_amount=money(449800),
    )
    report = check_quotation(fields, dairy)
    total = next(c for c in report.checks if c.id == "total_vs_norm")
    assert total.severity is Severity.WARNING
    assert report.figures["quotation_excess_pct"] == Decimal("30.0")
    # Amber overall: worth telling the applicant, not worth stopping the application.
    assert report.severity is Severity.WARNING
    assert report.ready is False
