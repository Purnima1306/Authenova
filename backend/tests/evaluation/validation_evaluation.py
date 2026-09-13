"""
Validation Engine Evaluation Suite
Evaluates format checks, date plausibility, and distinction between
missing fields, OCR extraction issues, and invalid formats.
"""
from app.services.validation.service import validation_service


class TestValidationEvaluation:
    def test_valid_passport_format_icao(self):
        fields = {
            "name": "RAHUL",
            "passport_number": "BA103314",
            "date_of_birth": "15/07/2005",
            "expiry_date": "12/08/2036",
            "nationality": "INDIAN"
        }
        res = validation_service.validate(fields, document_type="passport")
        assert res["valid"] is True
        assert len(res["failed_checks"]) == 0
        assert res["validation_score"] == 1.0

    def test_expired_document_detected(self):
        fields = {
            "name": "TEST USER",
            "passport_number": "A1234567",
            "date_of_birth": "15/07/1990",
            "expiry_date": "01/01/2020",
            "nationality": "INDIAN"
        }
        res = validation_service.validate(fields, document_type="passport")
        assert res["valid"] is False
        assert any("expired" in chk.lower() for chk in res["failed_checks"])

    def test_future_dob_detected(self):
        fields = {
            "name": "TEST USER",
            "passport_number": "A1234567",
            "date_of_birth": "15/07/2099",
            "expiry_date": "01/01/2030",
            "nationality": "INDIAN"
        }
        res = validation_service.validate(fields, document_type="passport")
        assert res["valid"] is False
        assert any("not in the past" in chk.lower() for chk in res["failed_checks"])

    def test_distinguish_unextracted_field_from_invalid(self):
        fields = {
            "name": "TEST USER",
            "passport_number": None,
            "date_of_birth": "15/07/1990",
            "expiry_date": "01/01/2030",
            "nationality": "INDIAN"
        }
        res = validation_service.validate(fields, document_type="passport")
        assert res["valid"] is False
        # Confirms wording explicitly distinguishes extraction failure
        assert any("could not be reliably extracted" in chk for chk in res["failed_checks"])
