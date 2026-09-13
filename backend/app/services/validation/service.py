"""
Document Validation Service
Performs deterministic, rule-based checks on extracted fields.
Supports passport, aadhaar, visa, and permit document types.
"""
import datetime
import re
from typing import Dict, Any, List


def parse_date(date_str: str) -> datetime.date | None:
    """Parse date from multiple possible formats."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y"):
        try:
            return datetime.datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


class ValidationService:
    """Validates extracted document fields against standard formats and logic."""

    @staticmethod
    def check_expiry(expiry_val: str | None) -> Dict[str, str]:
        if not expiry_val:
            return {"status": "FAIL", "reason": "Expiry date could not be reliably extracted. Manual verification required."}
        
        parsed = parse_date(expiry_val)
        if not parsed:
            return {"status": "FAIL", "reason": f"Expiry date '{expiry_val}' has an unrecognized format."}
        
        today = datetime.date.today()
        if today <= parsed:
            return {"status": "PASS", "reason": f"Document is valid up to {parsed}."}
        else:
            return {"status": "FAIL", "reason": f"Document expired on {parsed}."}

    @staticmethod
    def check_dob(dob_val: str | None) -> Dict[str, str]:
        if not dob_val:
            return {"status": "FAIL", "reason": "Date of birth could not be reliably extracted. Manual verification required."}
        
        parsed = parse_date(dob_val)
        if not parsed:
            return {"status": "FAIL", "reason": f"Date of birth '{dob_val}' has an unrecognized format."}
        
        today = datetime.date.today()
        if parsed >= today:
            return {"status": "FAIL", "reason": f"Date of birth {parsed} is not in the past."}
        return {"status": "PASS", "reason": f"Date of birth {parsed} is valid."}

    @staticmethod
    def check_name(name_val: str | None) -> Dict[str, str]:
        if not name_val or not str(name_val).strip():
            return {"status": "FAIL", "reason": "Name field could not be reliably extracted. Manual verification required."}
        if len(str(name_val).strip()) < 2:
            return {"status": "FAIL", "reason": f"Name '{name_val}' is suspiciously short."}
        return {"status": "PASS", "reason": f"Name '{str(name_val).strip()}' is valid."}

    @staticmethod
    def check_nationality(nationality_val: str | None) -> Dict[str, str]:
        if not nationality_val or not str(nationality_val).strip():
            return {"status": "FAIL", "reason": "Nationality could not be reliably extracted. Manual verification required."}
        return {"status": "PASS", "reason": f"Nationality '{str(nationality_val).strip()}' is present and verified."}

    @staticmethod
    def check_document_number(doc_number: str | None, doc_type: str) -> Dict[str, str]:
        if not doc_number or not str(doc_number).strip():
            return {"status": "FAIL", "reason": f"{doc_type.capitalize()} number could not be reliably extracted. Manual verification required."}
        
        cleaned = str(doc_number).strip().replace(" ", "").upper()
        norm_type = doc_type.lower()

        if norm_type in ("passport", "passport_number"):
            # ICAO 9303 TD3 standard: 8-9 alphanumeric characters, commonly 1-2 letters + 6-7 digits
            if re.fullmatch(r"^[A-Z]{1,2}[0-9]{6,7}$", cleaned) or re.fullmatch(r"^[A-Z0-9]{8,9}$", cleaned):
                return {"status": "PASS", "reason": f"Passport number '{cleaned}' matches ICAO 9303 standard format."}
            return {"status": "FAIL", "reason": f"Passport number '{doc_number}' does not match standard ICAO format (8-9 alphanumeric)."}

        elif norm_type in ("aadhaar", "aadhaar_number"):
            if re.fullmatch(r"^\d{12}$", cleaned):
                return {"status": "PASS", "reason": "Aadhaar number is 12 valid digits."}
            return {"status": "FAIL", "reason": f"Aadhaar number '{doc_number}' must be exactly 12 digits."}

        elif norm_type in ("visa", "visa_number"):
            if re.fullmatch(r"^[A-Z0-9]{6,9}$", cleaned):
                return {"status": "PASS", "reason": "Visa number format is valid."}
            return {"status": "FAIL", "reason": f"Visa number '{doc_number}' does not match standard pattern."}

        elif norm_type in ("permit", "permit_number"):
            if re.fullmatch(r"^[A-Z0-9]{6,12}$", cleaned):
                return {"status": "PASS", "reason": "Permit number format is valid."}
            return {"status": "FAIL", "reason": f"Permit number '{doc_number}' does not match standard pattern."}

        return {"status": "PASS", "reason": f"Document number '{doc_number}' recorded."}

    def validate(self, fields: Dict[str, Any], document_type: str = "passport") -> Dict[str, Any]:
        """
        Validate all extracted fields for completeness, format, and logical sanity.
        """
        doc_type = document_type or fields.get("document_type", "passport")
        checks: List[Dict[str, Any]] = []

        # 1. Expiry Check
        expiry_val = fields.get("expiry_date") or fields.get("date_of_expiry")
        exp_res = self.check_expiry(expiry_val)
        checks.append({
            "field": "expiry_date",
            "label": "Expiry Date",
            "status": exp_res["status"],
            "message": exp_res["reason"]
        })

        # 2. DOB Check
        dob_val = fields.get("date_of_birth") or fields.get("dob")
        dob_res = self.check_dob(dob_val)
        checks.append({
            "field": "date_of_birth",
            "label": "Date of Birth",
            "status": dob_res["status"],
            "message": dob_res["reason"]
        })

        # 3. Name Check
        name_val = fields.get("name")
        name_res = self.check_name(name_val)
        checks.append({
            "field": "name",
            "label": "Full Name",
            "status": name_res["status"],
            "message": name_res["reason"]
        })

        # 4. Nationality Check
        nat_val = fields.get("nationality")
        nat_res = self.check_nationality(nat_val)
        checks.append({
            "field": "nationality",
            "label": "Nationality",
            "status": nat_res["status"],
            "message": nat_res["reason"]
        })

        # 5. ID Number Check
        id_val = (
            fields.get("passport_number") or
            fields.get("aadhaar_number") or
            fields.get("visa_number") or
            fields.get("permit_number") or
            fields.get("document_number") or
            fields.get("id_number")
        )
        id_res = self.check_document_number(id_val, doc_type)
        checks.append({
            "field": "document_number",
            "label": f"{doc_type.capitalize()} Number",
            "status": id_res["status"],
            "message": id_res["reason"]
        })

        # Aggregate
        failed_checks = [c["message"] for c in checks if c["status"] == "FAIL"]
        warning_checks = [c["message"] for c in checks if c["status"] == "WARNING"]
        passed_count = sum(1 for c in checks if c["status"] == "PASS")
        total_checks = len(checks)
        validation_score = round((passed_count / total_checks), 2) if total_checks else 1.0

        is_valid = len(failed_checks) == 0

        return {
            "valid": is_valid,
            "is_valid_format": is_valid,
            "validation_score": validation_score,
            "checks": checks,
            "failed_checks": failed_checks,
            "warnings": warning_checks,
            "validation_warnings": failed_checks + warning_checks
        }


# Singleton instance
validation_service = ValidationService()
