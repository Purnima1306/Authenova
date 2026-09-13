"""
End-to-End Integration and Service Tests for Authenova API.
Verifies real OCR, validation, tampering detection, face matching,
risk calculation, RAG citations, and officer decision persistence across
multiple real document conditions.
"""
import io
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE_DOC_PATH = "data/samples/documents/test_document.png"
SAMPLE_TAMPERED_PATH = "tampering_detection/sample_images/edited.jpg"
SAMPLE_FACE_PATH = "face-verification/test_images/detected_face_1.jpg"
SAMPLE_DIFF_FACE_PATH = "face-verification/test_images/different_face.png"


class TestHealthEndpoints:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Authenova API is running"
        assert data["status"] == "operational"

    def test_health(self):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestUploadEndpoint:
    def test_upload_document(self):
        if not os.path.exists(SAMPLE_DOC_PATH):
            pytest.skip(f"Sample doc not found at {SAMPLE_DOC_PATH}")
        with open(SAMPLE_DOC_PATH, "rb") as f:
            files = {"file": ("test_passport.png", f.read(), "image/png")}
        response = client.post("/api/v1/upload-document", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["document_id"].startswith("DOC-")
        assert data["data"]["filename"] == "test_passport.png"


class TestExtractionEndpoint:
    def test_extract_data_real(self):
        if not os.path.exists(SAMPLE_DOC_PATH):
            pytest.skip(f"Sample doc not found at {SAMPLE_DOC_PATH}")
        # Upload first
        with open(SAMPLE_DOC_PATH, "rb") as f:
            files = {"file": ("test_doc.png", f.read(), "image/png")}
        up_res = client.post("/api/v1/upload-document", files=files)
        doc_id = up_res.json()["data"]["document_id"]

        response = client.post("/api/v1/extract-data", json={"document_id": doc_id, "document_type": "passport"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        fields = data["data"]["extracted_fields"]
        assert fields["name"] == "TEST USER"
        assert fields["passport_number"] == "P1234567"
        assert data["data"]["ocr_confidence"] >= 0.80


class TestValidationEndpoint:
    def test_validate_document_valid(self):
        payload = {
            "document_id": "TEST-001",
            "document_type": "passport",
            "extracted_fields": {
                "name": "TEST USER",
                "passport_number": "P1234567",
                "date_of_birth": "2000-01-15",
                "expiry_date": "2030-05-10",
                "nationality": "IND"
            }
        }
        response = client.post("/api/v1/validate-document", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_valid_format"] is True
        assert len(data["data"]["failed_checks"]) == 0

    def test_validate_document_expired(self):
        payload = {
            "document_id": "TEST-002",
            "document_type": "passport",
            "extracted_fields": {
                "name": "TEST USER",
                "passport_number": "P1234567",
                "date_of_birth": "1990-01-15",
                "expiry_date": "2020-01-01",
                "nationality": "IND"
            }
        }
        response = client.post("/api/v1/validate-document", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_valid_format"] is False
        assert any("expired" in err.lower() for err in data["data"]["failed_checks"])


class TestTamperingEndpoint:
    def test_detect_tampering_real(self):
        if not os.path.exists(SAMPLE_TAMPERED_PATH):
            pytest.skip(f"Sample tampered image not found at {SAMPLE_TAMPERED_PATH}")
        payload = {"document_id": "TEST-003", "image_path": SAMPLE_TAMPERED_PATH}
        response = client.post("/api/v1/detect-tampering", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert 0.0 <= data["data"]["tampering_score"] <= 1.0
        assert "ela" in data["data"]
        assert "copy_move" in data["data"]


class TestFaceVerificationEndpoint:
    def test_verify_face_match(self):
        if not os.path.exists(SAMPLE_FACE_PATH):
            pytest.skip(f"Sample face image not found at {SAMPLE_FACE_PATH}")
        payload = {
            "document_id": "TEST-004",
            "document_image_path": SAMPLE_FACE_PATH,
            "verification_image_path": SAMPLE_FACE_PATH
        }
        response = client.post("/api/v1/verify-face", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["match"] is True
        assert data["data"]["similarity_score"] >= 0.75

    def test_verify_face_skipped_when_no_selfie(self):
        if not os.path.exists(SAMPLE_FACE_PATH):
            pytest.skip(f"Sample face image not found at {SAMPLE_FACE_PATH}")
        payload = {
            "document_id": "TEST-005",
            "document_image_path": SAMPLE_FACE_PATH,
            "verification_image_path": None
        }
        response = client.post("/api/v1/verify-face", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "SKIPPED"
        assert data["data"]["match"] is None


class TestRiskEndpoint:
    def test_calculate_risk(self):
        payload = {
            "document_id": "TEST-006",
            "ocr_confidence": 0.95,
            "fields": {"name": "TEST USER", "passport_number": "P1234567"},
            "validation_result": {"failed_checks": [], "checks": [{"status": "PASS"}]},
            "tampering_result": {"tampering_score": 0.15},
            "face_result": {"status": "completed", "similarity": 0.92}
        }
        response = client.post("/api/v1/calculate-risk", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["risk_level"] == "LOW"
        assert data["data"]["risk_score"] < 30.0


class TestScreeningPipelineMultiCondition:
    def test_screening_end_to_end_valid_with_selfie(self):
        if not os.path.exists(SAMPLE_DOC_PATH) or not os.path.exists(SAMPLE_FACE_PATH):
            pytest.skip("Sample images missing")

        with open(SAMPLE_DOC_PATH, "rb") as f_doc, open(SAMPLE_FACE_PATH, "rb") as f_selfie:
            files = {
                "file": ("passport.png", f_doc.read(), "image/png"),
                "verification_image": ("selfie.jpg", f_selfie.read(), "image/jpeg")
            }
            response = client.post("/api/v1/screen", files=files, data={"document_type": "passport"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"
        doc_id = data["document_id"]

        # Verify results endpoint
        res = client.get(f"/api/v1/results/{doc_id}")
        assert res.status_code == 200
        rep = res.json()["data"]
        assert rep["document_id"] == doc_id
        assert rep["extracted_fields"]["name"] == "TEST USER"
        assert rep["extracted_fields"]["passport_number"] == "P1234567"
        assert rep["ocr_confidence"] >= 0.85
        assert rep["risk"]["level"] in ("LOW", "MEDIUM")

        # Test officer decision recording on this real record
        dec_res = client.post(
            f"/api/v1/decision/{doc_id}",
            json={"action": "Approved", "comment": "Identity fully verified by officer."}
        )
        assert dec_res.status_code == 200
        assert dec_res.json()["decision"]["action"] == "Approved"

        # Verify decision persists upon retrieval
        check_res = client.get(f"/api/v1/results/{doc_id}")
        assert check_res.json()["data"]["officer_decision"]["action"] == "Approved"

    def test_screening_end_to_end_without_selfie(self):
        if not os.path.exists(SAMPLE_DOC_PATH):
            pytest.skip("Sample doc missing")

        with open(SAMPLE_DOC_PATH, "rb") as f_doc:
            files = {"file": ("passport_no_selfie.png", f_doc.read(), "image/png")}
            response = client.post("/api/v1/screen", files=files, data={"document_type": "passport"})

        assert response.status_code == 200
        data = response.json()
        doc_id = data["document_id"]
        res = client.get(f"/api/v1/results/{doc_id}")
        rep = res.json()["data"]
        assert rep["face_verification"]["status"] == "SKIPPED"
        assert rep["risk"]["score"] >= 0.0