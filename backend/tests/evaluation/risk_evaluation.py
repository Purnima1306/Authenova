"""
Risk Engine Evaluation Suite
Evaluates calibrated multi-factor risk scoring, ensures processing errors
are distinguished from fraud, and confirms missing selfie does not penalize risk.
"""
from app.services.risk.service import risk_service


class TestRiskEvaluation:
    def test_low_risk_genuine_passport(self):
        ocr_result = {
            "ocr_confidence": 0.96,
            "fields": {
                "name": "RAHUL",
                "passport_number": "BA103314",
                "date_of_birth": "15/07/2005",
                "expiry_date": "12/08/2036",
                "nationality": "INDIAN"
            }
        }
        validation_result = {"failed_checks": [], "checks": [1, 2, 3, 4, 5]}
        tampering_result = {"tampering_score": 0.0, "flagged": False}
        face_result = {"status": "completed", "similarity": 0.64, "threshold": 0.58, "match": True}

        res = risk_service.calculate(ocr_result, validation_result, tampering_result, face_result)
        assert res["level"] == "LOW"
        assert res["score"] <= 20.0
        assert res["status"] == "pass"

    def test_high_risk_impostor_face(self):
        ocr_result = {
            "ocr_confidence": 0.90,
            "fields": {
                "name": "RAHUL",
                "passport_number": "BA103314",
                "date_of_birth": "15/07/2005",
                "expiry_date": "12/08/2036",
                "nationality": "INDIAN"
            }
        }
        validation_result = {"failed_checks": [], "checks": [1, 2, 3, 4, 5]}
        tampering_result = {"tampering_score": 0.0, "flagged": False}
        face_result = {"status": "completed", "similarity": 0.35, "threshold": 0.58, "match": False}

        res = risk_service.calculate(ocr_result, validation_result, tampering_result, face_result)
        # Face mismatch produces significant risk contribution
        assert res["level"] in ("MEDIUM", "HIGH")
        assert any("mismatch" in r["text"].lower() or "impersonation" in r["text"].lower() for r in res["reasons"])

    def test_skipped_selfie_no_penalty(self):
        ocr_result = {
            "ocr_confidence": 0.95,
            "fields": {
                "name": "TEST USER",
                "passport_number": "A1234567",
                "date_of_birth": "15/07/2000",
                "expiry_date": "12/08/2030",
                "nationality": "INDIAN"
            }
        }
        validation_result = {"failed_checks": [], "checks": [1, 2, 3, 4, 5]}
        tampering_result = {"tampering_score": 0.0, "flagged": False}
        face_result = {"status": "SKIPPED", "similarity": None, "match": None}

        res = risk_service.calculate(ocr_result, validation_result, tampering_result, face_result)
        assert res["level"] == "LOW"
        assert res["score"] <= 15.0
        face_reason = next(r for r in res["reasons"] if r["module"] == "face")
        assert "does not penalize" in face_reason["text"].lower()
