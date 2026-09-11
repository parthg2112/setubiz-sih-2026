"""The deterministic layer. This is where a document is judged, and nothing else judges it.

Every verdict here is a comparison against a published figure the project already holds: the
NABARD cost template, the corporation income ceiling, the category-to-corporation routing. A
language model is never consulted. It could only rephrase what this file has already decided.

The quotation check is the one that matters most. An inflated vendor quote raises the project
cost, which raises the loan, which raises the instalment, which is exactly the mechanism this
whole product exists to argue against. So the check does not stop at "that looks high": it
re-runs the finance engine at the quoted cost and reports what happens to the DSCR.
"""

from __future__ import annotations

from decimal import Decimal

from rapidfuzz import fuzz

from setubiz.documents.schemas import (
    CasteCertificateFields,
    CheckResult,
    DocumentKind,
    DocumentReport,
    IncomeCertificateFields,
    MatchedLine,
    QuotationFields,
    Severity,
)
from setubiz.eligibility.rules import SocialCategory, corporation_for
from setubiz.finance.amortization import MoratoriumMode
from setubiz.finance.cost_templates import CostTemplate
from setubiz.finance.rightsizing import min_dscr, right_size
from setubiz.finance.router import route
from setubiz.money import ZERO, format_inr, money, q

#: A quote above the norm by this much is worth mentioning; above the second, worth stopping for.
WARN_ABOVE = Decimal("20")
PROBLEM_ABOVE = Decimal("50")
#: Per line, a little more tolerance: one item being dearer locally is ordinary.
LINE_WARN_ABOVE = Decimal("25")

#: Vendors do not write template item names. These are the words that mean the same thing.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "cows": ("cow", "cattle", "hf", "jersey", "crossbred", "milch", "animal", "गाय", "पशु"),
    "shed": ("shed", "shelter", "civil work", "construction", "platform", "शेड", "निर्माण"),
    "chaff cutter": ("chaff", "cutter", "trough", "equipment", "machine", "चारा", "उपकरण"),
    "milk cans": ("can", "utensil", "bucket", "बर्तन"),
    "insurance": ("insurance", "premium", "बीमा"),
    "transport": ("transport", "freight", "carriage", "परिवहन"),
    "fodder": ("fodder", "feed", "green", "चारा"),
    "mill": ("mill", "chakki", "motor", "starter", "चक्की"),
    "electrical": ("electric", "wiring", "connection", "load", "बिजली"),
    "machines": ("machine", "sewing", "overlock", "interlock", "मशीन"),
    "shelving": ("shelf", "shelving", "rack", "counter", "अलमारी"),
    "stock": ("stock", "inventory", "goods", "माल"),
}

#: A document older than this is stale for a loan file. Stated here rather than inline so it can
#: be argued with, and so a scheme that publishes a different window can override it in one place.
VALIDITY_MONTHS = 12
QUOTATION_VALIDITY_MONTHS = 3


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _match_line(description: str, template: CostTemplate) -> tuple[str, Decimal] | None:
    """Find the template line this quoted description corresponds to, or nothing.

    An unmatched line stays unmatched. Forcing a match would produce a comparison against an
    unrelated norm, which is worse than telling the applicant we could not place the row.
    """
    target = _norm(description)
    if not target:
        return None

    best: tuple[int, str, Decimal] | None = None
    for item in template.fixed_capital:
        item_text = _norm(item.item)
        score = fuzz.token_set_ratio(target, item_text)

        # A synonym hit is worth more than a string that merely looks similar.
        for key, words in SYNONYMS.items():
            if any(w in item_text for w in (key, *words)) and any(w in target for w in words):
                score = max(score, 88)

        if score >= 70 and (best is None or score > best[0]):
            best = (score, item.item, item.amount)

    return (best[1], best[2]) if best else None


def check_quotation(
    fields: QuotationFields,
    template: CostTemplate,
    *,
    margin: Decimal | None = None,
    months_old: int | None = None,
) -> DocumentReport:
    """Compare a vendor quotation against the published cost norm for this unit."""
    checks: list[CheckResult] = []
    figures: dict[str, Decimal] = {}

    stated_total = fields.total_amount
    summed = money(sum((li.amount for li in fields.lines), ZERO))
    norm_total = template.fixed_capital_total

    # --- arithmetic ------------------------------------------------------------------------
    if stated_total is not None and fields.lines:
        drift = abs(stated_total - summed)
        if drift > Decimal("1"):
            checks.append(
                CheckResult(
                    id="arithmetic",
                    severity=Severity.PROBLEM,
                    text_en=(
                        f"The lines add up to {format_inr(summed)} but the quotation states "
                        f"{format_inr(stated_total)}. Ask the vendor to correct it before you "
                        f"submit this."
                    ),
                    text_hi=(
                        f"पंक्तियों का जोड़ {format_inr(summed)} है, जबकि कोटेशन में "
                        f"{format_inr(stated_total)} लिखा है। जमा करने से पहले विक्रेता से "
                        f"सुधार कराएँ।"
                    ),
                    figures={"quotation_line_sum": summed, "quotation_stated_total": stated_total},
                )
            )
        else:
            checks.append(
                CheckResult(
                    id="arithmetic",
                    severity=Severity.OK,
                    text_en="The line items add up to the stated total.",
                    text_hi="पंक्तियों का जोड़ कुल राशि से मेल खाता है।",
                )
            )

    total = stated_total if stated_total is not None else summed
    figures["quotation_total"] = total
    figures["template_fixed_capital"] = norm_total

    # --- total against the norm ------------------------------------------------------------
    if norm_total > 0:
        excess = q((total - norm_total) / norm_total * 100, Decimal("0.1"))
        figures["quotation_excess_pct"] = excess
        if excess > PROBLEM_ABOVE:
            severity = Severity.PROBLEM
        elif excess > WARN_ABOVE:
            severity = Severity.WARNING
        else:
            severity = Severity.OK
        if severity is Severity.OK:
            checks.append(
                CheckResult(
                    id="total_vs_norm",
                    severity=severity,
                    text_en=(
                        f"The quotation totals {format_inr(total)}, against the published norm of "
                        f"{format_inr(norm_total)} for this unit. That is within range."
                    ),
                    text_hi=(
                        f"कोटेशन की कुल राशि {format_inr(total)} है, जबकि इस इकाई का प्रकाशित "
                        f"मानक {format_inr(norm_total)} है। यह सीमा के भीतर है।"
                    ),
                    figures={"quotation_total": total, "template_fixed_capital": norm_total},
                )
            )
        else:
            checks.append(
                CheckResult(
                    id="total_vs_norm",
                    severity=severity,
                    text_en=(
                        f"The quotation totals {format_inr(total)}, which is {excess}% above the "
                        f"published norm of {format_inr(norm_total)} for this unit."
                    ),
                    text_hi=(
                        f"कोटेशन की कुल राशि {format_inr(total)} है, जो इस इकाई के प्रकाशित मानक "
                        f"{format_inr(norm_total)} से {excess}% अधिक है।"
                    ),
                    figures={
                        "quotation_total": total,
                        "template_fixed_capital": norm_total,
                        "quotation_excess_pct": excess,
                    },
                )
            )

    # --- per line ---------------------------------------------------------------------------
    matched: list[MatchedLine] = []
    for line in fields.lines:
        hit = _match_line(line.description, template)
        if hit is None:
            matched.append(
                MatchedLine(
                    quoted=line,
                    template_item=None,
                    template_amount=None,
                    excess_pct=None,
                    severity=Severity.WARNING,
                )
            )
            continue
        item, norm = hit
        excess = q((line.amount - norm) / norm * 100, Decimal("0.1")) if norm > 0 else None
        severity = Severity.OK
        if excess is not None and excess > LINE_WARN_ABOVE:
            severity = Severity.PROBLEM if excess > PROBLEM_ABOVE else Severity.WARNING
        matched.append(
            MatchedLine(
                quoted=line,
                template_item=item,
                template_amount=norm,
                excess_pct=excess,
                severity=severity,
            )
        )

    inflated = [m for m in matched if m.severity is not Severity.OK and m.template_item]
    if inflated:
        names = ", ".join(m.template_item or "" for m in inflated)
        checks.append(
            CheckResult(
                id="inflated_lines",
                severity=max(
                    (m.severity for m in inflated),
                    key=lambda s: (s is Severity.PROBLEM, s is Severity.WARNING),
                ),
                text_en=f"These lines are above the published norm: {names}.",
                text_hi=f"ये पंक्तियाँ प्रकाशित मानक से अधिक हैं: {names}।",
            )
        )

    uncategorised = [m for m in matched if m.template_item is None]
    if uncategorised:
        checks.append(
            CheckResult(
                id="uncategorised_lines",
                severity=Severity.WARNING,
                text_en=(
                    f"{len(uncategorised)} line(s) could not be matched to the cost template. "
                    f"Check them yourself; we have not compared them to anything."
                ),
                text_hi=(
                    f"{len(uncategorised)} पंक्तियाँ लागत तालिका से मेल नहीं खा सकीं। इन्हें स्वयं "
                    f"जाँच लें; हमने इनकी किसी से तुलना नहीं की है।"
                ),
            )
        )

    # --- age ----------------------------------------------------------------------------------
    if months_old is not None and months_old > QUOTATION_VALIDITY_MONTHS:
        checks.append(
            CheckResult(
                id="quotation_age",
                severity=Severity.WARNING,
                text_en=(
                    f"This quotation is about {months_old} months old. Most branches want one no "
                    f"more than {QUOTATION_VALIDITY_MONTHS} months old, so ask the vendor for a "
                    f"fresh one."
                ),
                text_hi=(
                    f"यह कोटेशन लगभग {months_old} माह पुराना है। अधिकांश शाखाएँ "
                    f"{QUOTATION_VALIDITY_MONTHS} माह से पुराना स्वीकार नहीं करतीं, इसलिए "
                    f"विक्रेता से नया लें।"
                ),
            )
        )

    # --- what it does to the loan --------------------------------------------------------------
    # The point of the whole feature: an inflated quotation is not a paperwork problem, it is a
    # repayment problem, and the engine that already knows that is re-run at the quoted cost.
    if margin is not None and margin > 0 and total > norm_total and norm_total > 0:
        quoted_template = template.model_copy(
            update={
                "fixed_capital": tuple(
                    li.model_copy(update={"amount": q(li.amount * total / norm_total)})
                    for li in template.fixed_capital
                )
            }
        )
        scheme = route(margin)
        at_norm = right_size(scheme, template, MoratoriumMode.SERVICED)
        at_quote = right_size(scheme, quoted_template, MoratoriumMode.SERVICED)
        figures["dscr_at_norm"] = at_norm.recommended_min_dscr
        figures["quotation_shortfall"] = at_quote.capital_shortfall
        gap = q(at_quote.capital_shortfall - at_norm.capital_shortfall)

        # The number that actually lands: not "the gap grew" but "if you borrowed enough to pay
        # this quotation, here is the coverage the bank would compute". The right-sizing engine
        # would never recommend that loan, which is the point.
        needed = at_quote.debt_need
        threshold = at_quote.dscr_threshold
        if needed > 0:
            coverage = min_dscr(
                template.annual_noi, min(needed, scheme.max_loan), scheme, MoratoriumMode.SERVICED
            )
            figures["dscr_if_quotation_funded"] = coverage
            checks.append(
                CheckResult(
                    id="dscr_impact",
                    severity=Severity.PROBLEM if coverage < threshold else Severity.WARNING,
                    text_en=(
                        f"An inflated quotation raises the project cost, which raises the loan, "
                        f"which raises your instalment. Borrowing enough to pay this quotation "
                        f"puts your worst-year coverage at {coverage}, against the {threshold} "
                        f"that banks require. The gap you would have to fund yourself also grows "
                        f"by {format_inr(gap)}."
                    ),
                    text_hi=(
                        f"बढ़ा हुआ कोटेशन परियोजना लागत बढ़ाता है, जिससे ऋण और किस्त बढ़ती है। "
                        f"इस कोटेशन को चुकाने जितना ऋण लेने पर सबसे कमजोर वर्ष का कवरेज "
                        f"{coverage} रह जाता है, जबकि बैंक {threshold} माँगते हैं। स्वयं जुटाने "
                        f"वाली कमी भी {format_inr(gap)} बढ़ जाती है।"
                    ),
                    figures={
                        "quotation_shortfall_increase": gap,
                        "dscr_if_quotation_funded": coverage,
                    },
                )
            )

    return DocumentReport(
        kind=DocumentKind.QUOTATION,
        checks=tuple(checks),
        matched_lines=tuple(matched),
        figures=figures,
    )


def _authority_check(authority: str | None, prefix: str) -> CheckResult:
    """Tehsildar level or above. A village-level officer cannot issue these."""
    from setubiz.documents.extract import COMPETENT_AUTHORITIES, INCOMPETENT_AUTHORITIES

    if not authority:
        return CheckResult(
            id=f"{prefix}_authority",
            severity=Severity.WARNING,
            text_en="We could not read the issuing authority. Check it says Tehsildar or above.",
            text_hi="जारीकर्ता अधिकारी पढ़ा नहीं जा सका। देख लें कि वह तहसीलदार या उससे ऊपर हो।",
        )
    lowered = authority.lower()
    if any(word in lowered for word in INCOMPETENT_AUTHORITIES):
        return CheckResult(
            id=f"{prefix}_authority",
            severity=Severity.PROBLEM,
            text_en=(
                f"This appears to be issued at village level ({authority}). These certificates "
                f"have to come from a Tehsildar or above, and this is a common rejection cause."
            ),
            text_hi=(
                f"यह ग्राम स्तर पर जारी लगता है ({authority})। ये प्रमाण पत्र तहसीलदार या उससे "
                f"ऊपर से बनने चाहिए; यह अस्वीकृति का आम कारण है।"
            ),
        )
    if any(word in lowered for word in COMPETENT_AUTHORITIES):
        return CheckResult(
            id=f"{prefix}_authority",
            severity=Severity.OK,
            text_en=f"Issued by {authority}, which is competent.",
            text_hi=f"{authority} द्वारा जारी, जो सक्षम प्राधिकारी है।",
        )
    return CheckResult(
        id=f"{prefix}_authority",
        severity=Severity.WARNING,
        text_en=f"We could not confirm that {authority} is competent to issue this. Please check.",
        text_hi=f"हम पुष्टि नहीं कर सके कि {authority} इसे जारी करने में सक्षम है। कृपया जाँच लें।",
    )


def _age_check(months_old: int | None, prefix: str) -> CheckResult | None:
    if months_old is None:
        return None
    if months_old > VALIDITY_MONTHS:
        return CheckResult(
            id=f"{prefix}_validity",
            severity=Severity.WARNING,
            text_en=(
                f"This certificate is about {months_old} months old. Most branches want one "
                f"issued within the last {VALIDITY_MONTHS} months."
            ),
            text_hi=(
                f"यह प्रमाण पत्र लगभग {months_old} माह पुराना है। अधिकांश शाखाएँ पिछले "
                f"{VALIDITY_MONTHS} माह में जारी प्रमाण पत्र माँगती हैं।"
            ),
        )
    return CheckResult(
        id=f"{prefix}_validity",
        severity=Severity.OK,
        text_en="The certificate is within the usual validity window.",
        text_hi="प्रमाण पत्र सामान्य वैधता अवधि के भीतर है।",
    )


def check_income_certificate(
    fields: IncomeCertificateFields,
    social_category: str,
    *,
    months_old: int | None = None,
) -> DocumentReport:
    """The ceiling that applies is the one the existing routing already decided."""
    checks: list[CheckResult] = []
    figures: dict[str, Decimal] = {}

    corporation = corporation_for(SocialCategory(social_category))
    income = fields.annual_family_income

    if income is None:
        checks.append(
            CheckResult(
                id="income_read",
                severity=Severity.PROBLEM,
                text_en="We could not read the annual family income. Please type it in.",
                text_hi="वार्षिक पारिवारिक आय पढ़ी नहीं जा सकी। कृपया स्वयं लिखें।",
            )
        )
    else:
        figures["document_annual_family_income"] = income
        ceiling = corporation.income_ceiling if corporation else None
        if corporation is None:
            checks.append(
                CheckResult(
                    id="income_ceiling",
                    severity=Severity.WARNING,
                    text_en=(
                        f"Income reads {format_inr(income)}. Your category is not served by an "
                        f"MoSJE corporation, so no ceiling from this scheme applies."
                    ),
                    text_hi=(
                        f"आय {format_inr(income)} पढ़ी गई। आपकी श्रेणी किसी एमओएसजेई निगम के "
                        f"अंतर्गत नहीं आती, इसलिए इस योजना की कोई सीमा लागू नहीं होती।"
                    ),
                    figures={"document_annual_family_income": income},
                )
            )
        elif ceiling is None:
            checks.append(
                CheckResult(
                    id="income_ceiling",
                    severity=Severity.OK,
                    text_en=(
                        f"Income reads {format_inr(income)}. {corporation.name} sets no ceiling."
                    ),
                    text_hi=(
                        f"आय {format_inr(income)} पढ़ी गई। {corporation.name} कोई सीमा नहीं रखता।"
                    ),
                    figures={"document_annual_family_income": income},
                )
            )
        else:
            figures["document_income_ceiling"] = ceiling
            over = income > ceiling
            checks.append(
                CheckResult(
                    id="income_ceiling",
                    severity=Severity.PROBLEM if over else Severity.OK,
                    text_en=(
                        f"Income reads {format_inr(income)} against a ceiling of "
                        f"{format_inr(ceiling)}. "
                        + ("That is over the limit." if over else "That is within the limit.")
                    ),
                    text_hi=(
                        f"आय {format_inr(income)} पढ़ी गई, सीमा {format_inr(ceiling)} है। "
                        + ("यह सीमा से अधिक है।" if over else "यह सीमा के भीतर है।")
                    ),
                    figures={
                        "document_annual_family_income": income,
                        "document_income_ceiling": ceiling,
                    },
                )
            )

    checks.append(_authority_check(fields.issuing_authority, "income"))
    age = _age_check(months_old, "income")
    if age is not None:
        checks.append(age)

    return DocumentReport(
        kind=DocumentKind.INCOME_CERTIFICATE, checks=tuple(checks), figures=figures
    )


def check_caste_certificate(
    fields: CasteCertificateFields,
    social_category: str,
    *,
    months_old: int | None = None,
) -> DocumentReport:
    """The category on the certificate decides which corporation the application goes to."""
    checks: list[CheckResult] = []

    claimed = corporation_for(SocialCategory(social_category))
    if fields.category is None:
        checks.append(
            CheckResult(
                id="category_read",
                severity=Severity.PROBLEM,
                text_en="We could not read the category. Please select it yourself.",
                text_hi="श्रेणी पढ़ी नहीं जा सकी। कृपया स्वयं चुनें।",
            )
        )
    else:
        on_document = corporation_for(SocialCategory(fields.category))
        if fields.category != social_category:
            checks.append(
                CheckResult(
                    id="category_match",
                    severity=Severity.PROBLEM,
                    text_en=(
                        f"The certificate says {fields.category.upper()} but the application says "
                        f"{social_category.upper()}. A wrong category sends the whole application "
                        f"to the wrong corporation."
                    ),
                    text_hi=(
                        f"प्रमाण पत्र में {fields.category.upper()} लिखा है, जबकि आवेदन में "
                        f"{social_category.upper()} है। गलत श्रेणी से पूरा आवेदन गलत निगम में "
                        f"चला जाता है।"
                    ),
                )
            )
        elif on_document is not None:
            checks.append(
                CheckResult(
                    id="category_match",
                    severity=Severity.OK,
                    text_en=(
                        f"Category {fields.category.upper()} matches the application, and routes "
                        f"to {on_document.name}."
                    ),
                    text_hi=(
                        f"श्रेणी {fields.category.upper()} आवेदन से मेल खाती है, और "
                        f"{on_document.name} के अंतर्गत जाती है।"
                    ),
                )
            )
        else:
            checks.append(
                CheckResult(
                    id="category_match",
                    severity=Severity.WARNING,
                    text_en=(
                        f"Category {fields.category.upper()} is not served by an MoSJE apex "
                        f"corporation, so this application would have to go elsewhere."
                    ),
                    text_hi=(
                        f"श्रेणी {fields.category.upper()} किसी एमओएसजेई शीर्ष निगम के अंतर्गत "
                        f"नहीं आती, इसलिए यह आवेदन कहीं और भेजना होगा।"
                    ),
                )
            )

    checks.append(
        CheckResult(
            id="attestation",
            severity=Severity.OK if fields.attestation_present else Severity.WARNING,
            text_en=(
                "A seal or signature was detected."
                if fields.attestation_present
                else "No seal or signature was detected. Check the certificate is attested."
            ),
            text_hi=(
                "मुहर या हस्ताक्षर मिला।"
                if fields.attestation_present
                else "कोई मुहर या हस्ताक्षर नहीं मिला। देख लें कि प्रमाण पत्र अभिप्रमाणित है।"
            ),
        )
    )
    checks.append(_authority_check(fields.issuing_authority, "caste"))
    age = _age_check(months_old, "caste")
    if age is not None:
        checks.append(age)

    _ = claimed  # routing is reported through category_match above
    return DocumentReport(kind=DocumentKind.CASTE_CERTIFICATE, checks=tuple(checks))


def check_names_match(names: dict[str, str | None]) -> CheckResult | None:
    """Cross-document name consistency. Cheap, and catches a genuinely common rejection.

    Deliberately fuzzy: "Sunita Devi" and "Sunita Kumari" must be flagged, but a transliteration
    wobble or a missing middle name should not be, because a false alarm here teaches the
    applicant to ignore the warning.
    """
    present = {k: v for k, v in names.items() if v and v.strip()}
    if len(present) < 2:
        return None

    labels = list(present)
    worst = 100
    for i, a in enumerate(labels):
        for b in labels[i + 1 :]:
            worst = min(worst, int(fuzz.token_sort_ratio(_norm(present[a]), _norm(present[b]))))

    if worst >= 85:
        return CheckResult(
            id="name_match",
            severity=Severity.OK,
            text_en="The name is consistent across the documents you uploaded.",
            text_hi="आपके दस्तावेज़ों में नाम एक जैसा है।",
        )
    shown = " / ".join(f"{present[k]}" for k in labels)
    return CheckResult(
        id="name_match",
        severity=Severity.WARNING,
        text_en=(
            f"The name is not identical across your documents ({shown}). Confirm before "
            f"submitting; a name mismatch is a common rejection cause."
        ),
        text_hi=(
            f"आपके दस्तावेज़ों में नाम एक जैसा नहीं है ({shown})। जमा करने से पहले पुष्टि करें; "
            f"नाम का अंतर अस्वीकृति का आम कारण है।"
        ),
    )
