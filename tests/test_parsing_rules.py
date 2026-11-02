from datetime import date
import pytest
from certflow.parsing import InvalidDocument, extract_fields, parse_pdf
from certflow.rules import validate

def test_extract_fields_and_review(demo):
    pdfs, _, _ = demo
    fields=extract_fields(parse_pdf((pdfs/"demo-001.pdf").read_bytes()))
    assert fields["certificate_number"]["value"]=="DEMO-CERT-1000"
    assert fields["certificate_number"]["page"]==1
    status=validate(fields,date(2026,11,2))
    assert status["status"]=="NEEDS_REVIEW"
    assert {item["code"] for item in status["issues"]} >= {"MISSING","EXPIRED"}

def test_bad_pdf_rejected():
    with pytest.raises(InvalidDocument): parse_pdf(b"not a pdf")

def test_no_legal_assertion(demo):
    pdfs, _, _ = demo
    fields=extract_fields(parse_pdf((pdfs/"demo-002.pdf").read_bytes()))
    result=validate(fields,date(2026,11,2))
    assert result["status"]=="FIELDS_COMPLETE"
    assert "no legal" in result["disclaimer"].lower()
