"""
Pipeline Evaluation Suite
Tests the complete end-to-end production screening pipeline
on the exact supplied real passport and real webcam face image.
"""
import os
import pytest
from app.services.orchestrator.pipeline import pipeline

REAL_PASSPORT = "backend/uploads/DOC-8A14A02C_doc.jpeg"
REAL_FACE = "backend/uploads/DOC-8A14A02C_face.jpg"


@pytest.mark.anyio
class TestPipelineEvaluation:
    async def test_supplied_real_passport_and_face(self):
        if not (os.path.exists(REAL_PASSPORT) and os.path.exists(REAL_FACE)):
            pytest.skip("Supplied real passport and face images not found")

        with open(REAL_PASSPORT, "rb") as f:
            doc_bytes = f.read()
        with open(REAL_FACE, "rb") as f:
            face_bytes = f.read()

        result = await pipeline.run_screening(
            document_content=doc_bytes,
            document_filename="DOC-8A14A02C_doc.jpeg",
            document_type="passport",
            selfie_content=face_bytes,
            selfie_filename="DOC-8A14A02C_face.jpg"
        )

        assert result["status"] == "completed"
        report = result["report"]

        # 1. OCR verification
        assert report["ocr_confidence"] >= 0.85
        ocr = report["ocr"]
        assert ocr["name"]["value"] is not None and "RAHUL" in ocr["name"]["value"].upper()
        assert ocr["idNumber"]["value"] == "BA103314"
        assert ocr["nationality"]["value"] == "INDIAN"
        assert ocr["dateOfBirth"]["value"] == "15/07/2005"
        assert ocr["expiryDate"]["value"] == "12/08/2036"

        # 2. Validation verification
        failed_checks = [c for c in report["validation"] if c["status"] == "fail"]
        assert len(failed_checks) == 0

        # 3. Tampering verification
        tampering = report["tampering"]
        assert tampering["level"] == "Low"
        assert tampering["flagged"] is False
        assert tampering["tampering_score"] <= 0.20

        # 4. Face verification
        face = report["face_verification"]
        assert face["status"] == "completed"
        assert face["document_face_detected"] is True
        assert face["presented_face_detected"] is True
        assert face["match"] is True
        assert face["similarity"] >= 58

        # 5. Composite Risk
        assert report["risk"]["level"] == "LOW"
        assert report["risk"]["score"] <= 25

        # 6. Diagnostics & Persistence
        assert report["mrz"] is not None
        assert "diagnostics" in report
        saved = pipeline.get_screening(report["document_id"])
        assert saved is not None
