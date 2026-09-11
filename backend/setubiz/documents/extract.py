"""Pull named fields out of OCR text.

Read this before trusting anything in here.

The spec is explicit that extraction rules cannot be written properly until real photographs
exist, and none do yet. These rules are calibrated against typed and synthetic text only. They
will be wrong on a creased, glare-lit phone photograph of a laminated certificate, and they are
built on the assumption that **every field is shown to the applicant for confirmation before it
reaches a check**. Nothing here is permitted to produce a verdict on its own.

That is why extraction returns `None` freely rather than guessing: a blank the applicant fills in
is a working form field, while a confidently wrong number is a wrong loan.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from setubiz.documents.schemas import (
    CasteCertificateFields,
    IncomeCertificateFields,
    QuotationFields,
    QuotedLine,
)
from setubiz.money import money

#: Indian digit grouping, with or without a currency mark. Also matches plain integers.
_AMOUNT = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
_DATE = re.compile(r"\b(\d{1,2})[-/.\s]+(\d{1,2}|[a-z]{3,9})[-/.\s]+(\d{2,4})\b", re.IGNORECASE)
_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]\b")

#: Authorities competent to issue income and caste certificates. Village-level officers are not,
#: and that is one of the most common rejection causes, so the list is explicit rather than fuzzy.
COMPETENT_AUTHORITIES = (
    "tehsildar",
    "tahsildar",
    "sdm",
    "sub divisional magistrate",
    "sub-divisional magistrate",
    "district magistrate",
    "collector",
    "revenue officer",
    "circle officer",
    "naib tehsildar",
    "तहसीलदार",
    "अनुमंडल पदाधिकारी",
    "जिला पदाधिकारी",
    "अंचल अधिकारी",
)

#: Seen on certificates but not competent to issue them.
INCOMPETENT_AUTHORITIES = (
    "gram panchayat",
    "sarpanch",
    "mukhiya",
    "panchayat secretary",
    "ward member",
    "ग्राम पंचायत",
    "सरपंच",
    "मुखिया",
)

_CATEGORY_WORDS: tuple[tuple[str, str], ...] = (
    ("safai karamchari", "safai_karamchari"),
    ("सफाई कर्मचारी", "safai_karamchari"),
    ("scheduled caste", "sc"),
    ("अनुसूचित जाति", "sc"),
    ("scheduled tribe", "st"),
    ("अनुसूचित जनजाति", "st"),
    ("extremely backward", "ebc"),
    ("अत्यंत पिछड़ा", "ebc"),
    ("other backward", "obc"),
    ("अन्य पिछड़ा", "obc"),
    ("backward class", "obc"),
    ("पिछड़ा वर्ग", "obc"),
)

_ATTESTATION_WORDS = (
    "seal",
    "signature",
    "signed",
    "attested",
    "digitally signed",
    "मुहर",
    "हस्ताक्षर",
    "अभिप्रमाणित",
)


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return money(raw.replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _amounts(line: str) -> list[Decimal]:
    out = []
    for match in _AMOUNT.finditer(line):
        value = _to_decimal(match.group(1))
        if value is not None:
            out.append(value)
    return out


def _labelled_amount(text: str, labels: tuple[str, ...]) -> Decimal | None:
    """The first amount on a line carrying one of these labels."""
    for line in text.splitlines():
        lowered = line.lower()
        if any(label in lowered for label in labels):
            found = _amounts(line)
            if found:
                return max(found)
    return None


def _labelled_value(text: str, labels: tuple[str, ...]) -> str | None:
    """Whatever follows a label on its line, trimmed of separators."""
    for line in text.splitlines():
        lowered = line.lower()
        for label in labels:
            if label in lowered:
                tail = line[lowered.index(label) + len(label) :]
                cleaned = tail.strip(" :\t-.–—")
                if cleaned:
                    return cleaned
    return None


def _first_date(text: str) -> str | None:
    match = _DATE.search(text)
    return match.group(0).strip() if match else None


def _authority(text: str) -> str | None:
    """The designation, not just a name. Returns whichever authority word appears, with context."""
    for line in text.splitlines():
        lowered = line.lower()
        for word in (*COMPETENT_AUTHORITIES, *INCOMPETENT_AUTHORITIES):
            if word in lowered:
                return line.strip(" :\t-")
    return None


#: Header and footer rows that carry digits but are not purchases. A GSTIN, a phone number and a
#: date all look like a line item to a naive amount scan, and each one would otherwise be compared
#: against the cost template as if the applicant had bought it.
_METADATA_LABELS = (
    "gstin",
    "gst no",
    "pan",
    "date",
    "dated",
    "quotation no",
    "quotation number",
    "invoice no",
    "ref",
    "phone",
    "mobile",
    "contact",
    "address",
    "pin",
    "vendor",
    "supplier",
    "दिनांक",
    "फोन",
    "मोबाइल",
    "पता",
)

#: Below this, an "amount" in a capital quotation is a row number, a quantity or OCR noise.
_MIN_LINE_AMOUNT = money(100)


def extract_quotation(text: str) -> QuotationFields:
    """Line items are rows carrying at least one amount and some description text."""
    lines: list[QuotedLine] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        # The total is captured separately; treating it as a line item would double-count it.
        if lowered.startswith(("total", "grand total", "कुल", "योग")):
            continue
        if any(label in lowered for label in _METADATA_LABELS):
            continue
        if _GSTIN.search(stripped):
            continue
        found = _amounts(stripped)
        if not found:
            continue
        description = _AMOUNT.sub("", stripped).strip(" :|\t-.")
        # A row of nothing but numbers is a page number or a column ruler, not a purchase.
        if len(description) < 3:
            continue
        amount = found[-1]
        if amount < _MIN_LINE_AMOUNT:
            continue
        rate = found[-2] if len(found) >= 2 else None
        quantity = Decimal(1)
        if rate is not None and rate > 0:
            ratio = (amount / rate).quantize(Decimal("1"))
            # Only believe a quantity that actually reconstructs the amount.
            if ratio > 0 and abs(rate * ratio - amount) <= Decimal("1"):
                quantity = ratio
        lines.append(
            QuotedLine(description=description, quantity=quantity, unit_rate=rate, amount=amount)
        )

    total = _labelled_amount(text, ("grand total", "total", "कुल", "योग"))
    gstin = _GSTIN.search(text)
    return QuotationFields(
        vendor_name=_labelled_value(text, ("vendor", "supplier", "from", "विक्रेता")),
        vendor_gstin=gstin.group(0) if gstin else None,
        quotation_date=_first_date(text),
        lines=tuple(lines),
        total_amount=total,
    )


def extract_income_certificate(text: str) -> IncomeCertificateFields:
    return IncomeCertificateFields(
        applicant_name=_labelled_value(text, ("name", "applicant", "नाम", "आवेदक")),
        annual_family_income=_labelled_amount(
            text, ("annual income", "family income", "income", "वार्षिक आय", "पारिवारिक आय", "आय")
        ),
        issue_date=_first_date(text),
        issuing_authority=_authority(text),
        certificate_number=_labelled_value(
            text, ("certificate no", "certificate number", "प्रमाण पत्र संख्या", "क्रमांक")
        ),
        state=_labelled_value(text, ("state", "राज्य")),
    )


def extract_caste_certificate(text: str) -> CasteCertificateFields:
    lowered = text.lower()
    category = None
    for word, value in _CATEGORY_WORDS:
        if word in lowered:
            category = value
            break
    return CasteCertificateFields(
        applicant_name=_labelled_value(text, ("name", "applicant", "नाम", "आवेदक")),
        category=category,
        sub_caste=_labelled_value(text, ("sub caste", "sub-caste", "उप जाति")),
        issuing_authority=_authority(text),
        issue_date=_first_date(text),
        certificate_number=_labelled_value(
            text, ("certificate no", "certificate number", "प्रमाण पत्र संख्या", "क्रमांक")
        ),
        attestation_present=any(word in lowered for word in _ATTESTATION_WORDS),
    )
