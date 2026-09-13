"""
OCR Evaluation Suite
Evaluates orientation detection, MRZ checksum parsing, visual OCR,
and structured confidence scoring across real documents and variations.
"""
import os
import pytest
from app.services.ocr.engine import ocr_service, normalize_document_orientation, is_tesseract_available

REAL_PASSPORT = "backend/uploads/DOC-8A14A02C_doc.jpeg"
SAMPLE_DOC = "data/samples/documents/test_document.png"
ROTATED_DOC = "data/samples/documents/test_document_rotated.png"


class TestOcrEvaluation:
    def test_tesseract_engine_available(self):
        assert is_tesseract_available() is True

    def test_orientation_detection_and_normalization(self):
        if not os.path.exists(REAL_PASSPORT):
            pytest.skip("Real passport image not found")
        import cv2
        img = cv2.imread(REAL_PASSPORT)
        canon_img, rot_angle, method = normalize_document_orientation(img)
        assert canon_img is not None
        assert rot_angle in (90, 180, 270)  # Correctly identifies non-zero rotation
        # Canonical width should be >= height for TD3 passport layout
        assert canon_img.shape[1] >= canon_img.shape[0]

    def test_mrz_parsing_and_check_digits(self):
        # Real ICAO 9303 TD3 lines from real passport
        line1 = "P<INDMANCHANDA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<<<"
        line2 = "BA103314<9IND0507152M3608120<<<<<<<<<<<<<<00"
        mrz_data = ocr_service.parse_mrz(f"{line1}\n{line2}")
        assert mrz_data is not None
        assert mrz_data["passport_number"] == "BA103314"
        assert mrz_data["passport_number_valid"] is True
        assert mrz_data["date_of_birth"] == "15/07/2005"
        assert mrz_data["date_of_birth_valid"] is True
        assert mrz_data["expiry_date"] == "12/08/2036"
        assert mrz_data["expiry_date_valid"] is True
        assert mrz_data["nationality"] == "INDIAN"
        assert mrz_data["surname"] == "MANCHANDA"
        assert mrz_data["given_names"] == "RAHUL"

    def test_real_passport_ocr_accuracy(self):
        if not os.path.exists(REAL_PASSPORT):
            pytest.skip("Real passport image not found")
        result = ocr_service.extract(REAL_PASSPORT)
        assert result["ocr_confidence"] >= 0.85
        fields = result["fields"]
        assert fields["name"] is not None and "RAHUL" in fields["name"].upper()
        assert fields["passport_number"] == "BA103314"
        assert fields["nationality"] == "INDIAN"
        assert fields["date_of_birth"] == "15/07/2005"
        assert fields["expiry_date"] == "12/08/2036"

    def test_sample_document_ocr(self):
        if not os.path.exists(SAMPLE_DOC):
            pytest.skip("Sample doc not found")
        result = ocr_service.extract(SAMPLE_DOC)
        assert result["ocr_confidence"] >= 0.80
        fields = result["fields"]
        assert fields["name"] == "TEST USER"
        assert fields["passport_number"] == "P1234567"
