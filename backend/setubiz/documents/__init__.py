"""Document readiness checking (OCR_Document_Checker_Spec.md).

Images never reach this package. OCR runs in the applicant's browser, the applicant confirms
every extracted field, and only confirmed text arrives here. The checks are ordinary Python
comparisons against published figures the project already holds.
"""

from setubiz.documents.checks import (
    check_caste_certificate,
    check_income_certificate,
    check_names_match,
    check_quotation,
)
from setubiz.documents.classify import classify
from setubiz.documents.extract import (
    extract_caste_certificate,
    extract_income_certificate,
    extract_quotation,
)
from setubiz.documents.schemas import (
    CasteCertificateFields,
    CheckResult,
    DocumentKind,
    DocumentReport,
    IncomeCertificateFields,
    MatchedLine,
    QuotationFields,
    QuotedLine,
    Severity,
)

__all__ = [
    "CasteCertificateFields",
    "CheckResult",
    "DocumentKind",
    "DocumentReport",
    "IncomeCertificateFields",
    "MatchedLine",
    "QuotationFields",
    "QuotedLine",
    "Severity",
    "check_caste_certificate",
    "check_income_certificate",
    "check_names_match",
    "check_quotation",
    "classify",
    "extract_caste_certificate",
    "extract_income_certificate",
    "extract_quotation",
]
