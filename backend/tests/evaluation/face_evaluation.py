"""
Face Verification Evaluation Suite
Evaluates biometric portrait isolation, FaceNet 512-d embeddings,
and genuine vs impostor match separation.
"""
import os
import pytest
from app.services.face.service import face_service, facenet_embedder, cosine_similarity

REAL_PASSPORT = "backend/uploads/DOC-8A14A02C_doc.jpeg"
REAL_FACE = "backend/uploads/DOC-8A14A02C_face.jpg"
IMPOSTOR_FACE = "face-verification/test_images/different_face.png"
SAMPLE_FACE = "face-verification/test_images/face_image.png"


class TestFaceEvaluation:
    def test_facenet_model_loaded(self):
        assert facenet_embedder is not None

    def test_real_passport_portrait_and_selfie_match(self):
        if not (os.path.exists(REAL_PASSPORT) and os.path.exists(REAL_FACE)):
            pytest.skip("Real passport/face samples not found")

        result = face_service.verify(REAL_PASSPORT, REAL_FACE)
        assert result["status"] == "completed"
        assert result["document_face_detected"] is True
        assert result["presented_face_detected"] is True
        assert result["match"] is True
        # Verified similarity exceeds calibrated threshold
        assert result["similarity"] >= face_service.threshold
        assert result["model"] == "FaceNet 512-d"

    def test_impostor_face_rejection(self):
        if not (os.path.exists(REAL_PASSPORT) and os.path.exists(IMPOSTOR_FACE)):
            pytest.skip("Real passport/impostor face not found")

        result = face_service.verify(REAL_PASSPORT, IMPOSTOR_FACE)
        assert result["status"] == "completed"
        assert result["match"] is False
        assert result["similarity"] < face_service.threshold

    def test_missing_selfie_handling(self):
        if not os.path.exists(REAL_PASSPORT):
            pytest.skip("Real passport image not found")

        result = face_service.verify(REAL_PASSPORT, None)
        assert result["status"] == "SKIPPED"
        assert result["similarity"] is None
        assert result["match"] is None

    def test_cosine_similarity_properties(self):
        import numpy as np
        v1 = np.random.randn(512).astype(np.float32)
        v1 = v1 / np.linalg.norm(v1)
        # Identical vectors
        assert cosine_similarity(v1, v1) >= 0.999
        # Orthogonal vectors
        v2 = np.random.randn(512).astype(np.float32)
        v2 = v2 - np.dot(v1, v2) * v1
        v2 = v2 / np.linalg.norm(v2)
        assert abs(cosine_similarity(v1, v2)) < 0.05
