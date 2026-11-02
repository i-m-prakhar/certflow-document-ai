"""Deterministic demonstration checks; do not infer statutory legal validity."""
from datetime import date

REQUIRED = ["certificate_number", "seller", "buyer", "jurisdiction", "issue_date", "expiry_date", "document_type"]
REGIONS = {"CA", "NY", "TX", "WA", "CO", "FL"}

def validate(fields: dict, as_of: date | None = None) -> dict:
    as_of = as_of or date.today()
    missing = [field for field in REQUIRED if not fields.get(field, {}).get("value")]
    issues = [{"field": name, "code": "MISSING", "message": "required demo field absent"} for name in missing]
    typed = {}
    for name in ("issue_date", "expiry_date"):
        val = fields.get(name, {}).get("value")
        if val:
            try: typed[name] = date.fromisoformat(val)
            except ValueError: issues.append({"field": name, "code": "INVALID_DATE", "message": "invalid ISO date"})
    jurisdiction = fields.get("jurisdiction", {}).get("value")
    if jurisdiction and jurisdiction not in REGIONS:
        issues.append({"field": "jurisdiction", "code": "UNKNOWN_REGION", "message": "not in demo supported set"})
    if typed.get("issue_date") and typed["issue_date"] > as_of:
        issues.append({"field": "issue_date", "code": "FUTURE_ISSUE", "message": "issue date in future"})
    if typed.get("expiry_date") and typed["expiry_date"] < as_of:
        issues.append({"field": "expiry_date", "code": "EXPIRED", "message": "expiry before review date"})
    if typed.get("expiry_date") and typed.get("issue_date") and typed["expiry_date"] < typed["issue_date"]:
        issues.append({"field": "expiry_date", "code": "BEFORE_ISSUE", "message": "expiry precedes issue"})
    return {"status": "NEEDS_REVIEW" if issues else "FIELDS_COMPLETE",
            "issues": issues, "as_of": as_of.isoformat(),
            "disclaimer": "Completeness check only; no legal tax or exemption determination"}
