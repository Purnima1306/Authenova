"""
Regression & Integration Tests for PassportVerificationModel Integration
Validates:
1. Model service loads trained artifact.
2. 33-dimensional feature extraction.
3. Genuine passport classification (is_passport=True).
4. Non-passport document rejection (is_passport=False).
5. Rotated passport handling through pipeline orientation normalization.
6. API endpoint POST /api/v1/screen includes passport_verification.
7. Safe failure handling without crashing.
8. Risk engine multi-factor calibration preserving OCR, tampering, and face signals.
"""
import os
import pytest
import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.services.passport_verification.model import passport_verifier_model, MODEL_SAVE_PATH
from app.services.passport_verification_service import passport_verification_service
from app.services.orchestrator.pipeline import pipeline
from app.services.risk.service import risk_service

client = TestClient(app)


@pytest.fixture
def real_passport_path():
    p = "backend/uploads/DOC-8A14A02C_doc.jpeg"
    if not os.path.exists(p):
        pytest.skip(f"Test image not found at {p}")
    return p


@pytest.fixture
def national_id_path():
    p = "data/samples/generated_ids/alb_id_63.jpg"
    if not os.path.exists(p):
        pytest.skip(f"Test image not found at {p}")
    return p


@pytest.fixture
def real_face_path():
    p = "backend/uploads/DOC-8A14A02C_face.jpg"
    if not os.path.exists(p):
        pytest.skip(f"Test image not found at {p}")
    return p


class TestPassportVerificationModelIntegration:
    """Comprehensive test suite for PassportVerificationModel integration."""

    def test_model_service_loads_artifact(self):
        """1. Verify service loads the trained artifact with 33 features."""
        assert os.path.exists(MODEL_SAVE_PATH), f"Model artifact missing at {MODEL_SAVE_PATH}"
        assert passport_verifier_model.is_trained is True
        assert passport_verifier_model.doc_classifier is not None
        assert passport_verifier_model.doc_classifier.n_estimators == 50

    def test_feature_extraction_dimensions(self, real_passport_path):
        """2. Verify exact 33-dimensional feature vector extraction."""
        img = cv2.imread(real_passport_path)
        assert img is not None
        feats = passport_verifier_model.extract_document_features(img)
        assert isinstance(feats, np.ndarray)
        assert feats.shape == (33,)

    def test_genuine_passport_classified_correctly(self, real_passport_path):
        """3. Real genuine passport must classify as is_passport=True."""
        res = passport_verification_service.classify_document(real_passport_path)
        assert res["is_passport"] is True
        assert res["confidence"] >= 0.50
        assert res["status"] == "PASSPORT_DETECTED"
        assert res["features"] == 33

    def test_non_passport_classified_correctly(self, national_id_path):
        """4. National ID must classify as is_passport=False."""
        res = passport_verification_service.classify_document(national_id_path)
        assert res["is_passport"] is False
        assert res["confidence"] < 0.50
        assert res["status"] == "NON_PASSPORT_DOCUMENT"
        assert res["features"] == 33

    def test_safe_failure_handling_on_corrupt_input(self):
        """5. Invalid image must return safe structured uncertainty state without crashing."""
        res = passport_verification_service.classify_document("non_existent_file.png")
        assert res["is_passport"] is False
        assert res["confidence"] == 0.0
        assert res["status"] == "UNCERTAIN"
        assert "error" in res

    def test_rotated_passport_orientation_preservation(self, real_passport_path):
        """6. Rotated passport processed through canonical orientation maintains passport detection."""
        img = cv2.imread(real_passport_path)
        # Rotate 90 degrees
        rot_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        res = passport_verifier_model.verify_document(rot_img)
        assert res["is_passport"] is True

    def test_screen_api_includes_passport_verification(self, real_passport_path, real_face_path):
        """7. POST /api/v1/screen must return passport_verification in report."""
        with open(real_passport_path, "rb") as f_doc, open(real_face_path, "rb") as f_face:
            response = client.post(
                "/api/v1/screen",
                files={
                    "file": ("passport.jpg", f_doc, "image/jpeg"),
                    "verification_image": ("selfie.jpg", f_face, "image/jpeg")
                },
                data={"document_type": "passport"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "report" in data
        report = data["report"]
        assert "passport_verification" in report
        pv = report["passport_verification"]
        assert pv["is_passport"] is True
        assert pv["confidence"] >= 0.50
        assert pv["status"] == "PASSPORT_DETECTED"
        assert pv["features"] == 33

    def test_risk_engine_preserves_tampering_and_biometric_signals(self):
        """8. Strong fraud signals (tampering/face mismatch) must NOT be suppressed by high passport confidence."""
        mock_ocr = {"ocr_confidence": 0.95, "fields": {"name": "Test", "passport_number": "A1234567"}}
        mock_val = {"failed_checks": [], "checks": [{"status": "PASS"}]}
        mock_tampering_high = {"tampering_score": 0.70, "flagged": True, "level": "HIGH"}
        mock_face_mismatch = {"status": "completed", "similarity": 0.20, "threshold": 0.58, "match": False}
        mock_passport_pass = {"is_passport": True, "confidence": 0.95, "status": "PASSPORT_DETECTED"}

        risk = risk_service.calculate(
            ocr_result=mock_ocr,
            validation_result=mock_val,
            tampering_result=mock_tampering_high,
            face_result=mock_face_mismatch,
            passport_verification=mock_passport_pass,
            document_type="passport"
        )
        # Even with 95% passport confidence, tampering + face mismatch must result in HIGH risk
        assert risk["level"] == "HIGH"
        assert risk["score"] >= 50.0

    def test_risk_engine_penalizes_document_mismatch(self):
        """9. Submitting a non-passport when expecting passport generates risk penalty."""
        mock_ocr = {"ocr_confidence": 0.90, "fields": {"name": "Test"}}
        mock_val = {"failed_checks": [], "checks": [{"status": "PASS"}]}
        mock_tampering = {"tampering_score": 0.05, "flagged": False, "level": "LOW"}
        mock_passport_fail = {"is_passport": False, "confidence": 0.02, "status": "NON_PASSPORT_DOCUMENT"}

        risk = risk_service.calculate(
            ocr_result=mock_ocr,
            validation_result=mock_val,
            tampering_result=mock_tampering,
            face_result=None,
            passport_verification=mock_passport_fail,
            document_type="passport"
        )
        assert any(r["module"] == "passport_verification" and r["tone"] == "fail" for r in risk["reasons"])
        assert risk["score"] >= 40.0
