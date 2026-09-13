"""
Tampering Detection Evaluation Suite
Evaluates false positive elimination on genuine passports with security patterns
and true positive detection on edited documents using RANSAC homography.
"""
import os
import pytest
from app.services.tampering.service import tampering_service

REAL_PASSPORT = "backend/uploads/DOC-8A14A02C_doc.jpeg"
GENUINE_SAMPLE = "tampering_detection/sample_images/genuine.jpg"
EDITED_SAMPLE = "tampering_detection/sample_images/edited.jpg"


class TestTamperingEvaluation:
    def test_genuine_passport_low_tampering(self):
        if not os.path.exists(REAL_PASSPORT):
            pytest.skip("Real passport image not found")

        result = tampering_service.analyze(REAL_PASSPORT)
        assert result["level"] == "Low"
        assert result["flagged"] is False
        assert result["tampering_score"] <= 0.20
        # Inliers must be below copy-move threshold
        assert result["copy_move"]["detected"] is False

    def test_genuine_sample_low_tampering(self):
        if not os.path.exists(GENUINE_SAMPLE):
            pytest.skip("Genuine sample image not found")

        result = tampering_service.analyze(GENUINE_SAMPLE)
        assert result["level"] == "Low"
        assert result["flagged"] is False
        assert result["copy_move"]["detected"] is False

    def test_edited_sample_tampering_detected(self):
        if not os.path.exists(EDITED_SAMPLE):
            pytest.skip("Edited sample image not found")

        result = tampering_service.analyze(EDITED_SAMPLE)
        assert result["level"] in ("Medium", "High")
        assert result["flagged"] is True
        assert result["copy_move"]["detected"] is True
        # Verified inliers from the cloned region
        assert result["copy_move"]["verified_inliers"] >= 25
        assert result["flaggedRegion"] is not None

    def test_geometric_inliers_distinction(self):
        """Verify that displacement binning and RANSAC separate text repetition from copy-move."""
        if not (os.path.exists(REAL_PASSPORT) and os.path.exists(EDITED_SAMPLE)):
            pytest.skip("Test images not found")

        real_res = tampering_service.analyze(REAL_PASSPORT)
        edit_res = tampering_service.analyze(EDITED_SAMPLE)

        # Genuine passport has many raw matches (security guilloche/text) but few verified inliers
        assert edit_res["copy_move"]["verified_inliers"] > real_res["copy_move"]["verified_inliers"]
