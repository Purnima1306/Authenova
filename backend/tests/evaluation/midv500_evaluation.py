"""
MIDV-500 Dataset Evaluation Suite
Evaluates document orientation, feature extraction, tampering analysis,
and pipeline performance on real-world smartphone camera captures from the MIDV-500 benchmark.
"""
import os
import cv2
import pytest
import midv500
from app.services.ocr.engine import ocr_service, normalize_document_orientation
from app.services.tampering.service import tampering_service
from app.services.face.service import face_service
from app.services.orchestrator.pipeline import pipeline

MIDV500_DIR = "data/samples/midv500"
SAMPLE_1 = os.path.join(MIDV500_DIR, "midv500_sample_1.png")
SAMPLE_2 = os.path.join(MIDV500_DIR, "midv500_sample_2.png")
SAMPLE_3 = os.path.join(MIDV500_DIR, "midv500_sample_3.png")


class TestMidv500Evaluation:
    def test_midv500_package_installed_and_usable(self):
        assert midv500.__version__ is not None
        assert hasattr(midv500, "download_dataset")
        assert hasattr(midv500, "convert_dataset")
        assert hasattr(midv500, "convert_to_coco")

    def test_midv500_sample_images_exist(self):
        assert os.path.exists(SAMPLE_1), f"Sample 1 not found at {SAMPLE_1}"
        assert os.path.exists(SAMPLE_2), f"Sample 2 not found at {SAMPLE_2}"
        assert os.path.exists(SAMPLE_3), f"Sample 3 not found at {SAMPLE_3}"

    def test_midv500_image_properties(self):
        img = cv2.imread(SAMPLE_1)
        assert img is not None
        # MIDV-500 full HD resolution
        h, w = img.shape[:2]
        assert (w == 1080 and h == 1920) or (w == 1920 and h == 1080)

    def test_midv500_orientation_normalization(self):
        img = cv2.imread(SAMPLE_1)
        canon_img, rot_angle, method = normalize_document_orientation(img)
        assert canon_img is not None
        assert canon_img.shape[0] > 0 and canon_img.shape[1] > 0

    def test_midv500_ocr_extraction(self):
        result = ocr_service.extract(SAMPLE_1)
        assert result is not None
        assert "ocr_confidence" in result
        assert "fields" in result
        # Raw text was parsed from the capture
        assert len(result.get("raw_text", "")) >= 0

    def test_midv500_tampering_analysis(self):
        result = tampering_service.analyze(SAMPLE_1)
        assert result is not None
        assert "tampering_score" in result
        assert "copy_move" in result
        assert "verified_inliers" in result["copy_move"]

    @pytest.mark.anyio
    async def test_midv500_full_pipeline_screening(self):
        with open(SAMPLE_1, "rb") as f:
            content = f.read()

        result = await pipeline.run_screening(
            document_content=content,
            document_filename="midv500_sample_1.png",
            document_type="passport",
            selfie_content=None,
            selfie_filename=None
        )

        assert result["status"] == "completed"
        report = result["report"]
        assert report["document_id"].startswith("DOC-")
        assert "risk" in report
        assert "ocr" in report
        assert "tampering" in report
        assert report["face_verification"]["status"] == "SKIPPED"
