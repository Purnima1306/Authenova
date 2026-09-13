"""
OCR Extraction Engine
Performs document preprocessing (deskewing, denoising, thresholding),
Tesseract text recognition, confidence scoring, and regex-based field parsing.
Supports configurable TESSERACT_CMD and adaptive retry for low-confidence scans.
"""
import os
import shutil
import re
from io import BytesIO
from typing import Dict, Any, Tuple, Optional
import numpy as np
import cv2
from PIL import Image
import pytesseract
from pytesseract import Output

# Configure Tesseract binary path if provided in env
TESSERACT_CMD = os.getenv("TESSERACT_CMD")
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")


def is_tesseract_available() -> bool:
    """Check whether Tesseract binary is executable."""
    cmd = pytesseract.pytesseract.tesseract_cmd
    return bool(shutil.which(cmd) or os.path.exists(cmd))


# Preprocessing utilities
def deskew_image(image: np.ndarray) -> np.ndarray:
    """Detect and correct small skew angles in a document image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    elif angle > 45:
        angle = -(angle - 90)
    else:
        angle = -angle

    if abs(angle) < 0.5 or abs(angle) > 20.0:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )


def mrz_check_digit(s: str) -> str:
    """Calculate ICAO 9303 7-3-1 weight check digit for a string."""
    weights = [7, 3, 1]
    total = 0
    for i, c in enumerate(s):
        if '0' <= c <= '9':
            v = int(c)
        elif 'A' <= c <= 'Z':
            v = ord(c) - 55
        else:
            v = 0
        total += v * weights[i % 3]
    return str(total % 10)


def normalize_document_orientation(image: np.ndarray) -> Tuple[np.ndarray, int, str]:
    """
    Detect and correct document orientation (0°, 90°, 180°, 270°).
    Uses Tesseract OSD and MRZ/keyword scoring, accounting for passport landscape geometry.
    """
    h, w = image.shape[:2]

    # Try Tesseract OSD first
    suggested_rot = 0
    try:
        osd = pytesseract.image_to_osd(image)
        rot_m = re.search(r"Rotate:\s*(\d+)", osd)
        if rot_m:
            suggested_rot = int(rot_m.group(1))
    except Exception:
        suggested_rot = 0

    # If OSD suggests a rotation, prioritize testing that angle
    candidate_angles = [0, 90, 180, 270]
    if suggested_rot in [90, 180, 270]:
        # Tesseract OSD "Rotate: 90" means rotate 90 degrees counter-clockwise or clockwise
        candidate_angles = [suggested_rot, (360 - suggested_rot) % 360, 0, 180]

    # If aspect ratio is portrait (h > w), standard passport data pages are landscape (w > h),
    # so angles 90 and 270 must be evaluated ahead of 0
    if h > w and suggested_rot == 0:
        candidate_angles = [270, 90, 0, 180]

    best_score = -100
    best_img = image
    best_angle = 0

    for angle in candidate_angles:
        if angle == 90:
            rotated = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            rotated = cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            rotated = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            rotated = image

        rh, rw = rotated.shape[:2]
        txt = pytesseract.image_to_string(rotated)

        score = 0
        if "P<" in txt:
            score += 25
        if "<<<" in txt:
            score += 15
        if "PASSPORT" in txt.upper():
            score += 10
        if "GIVEN NAME" in txt.upper() or "SURNAME" in txt.upper():
            score += 8
        if "DATE OF BIRTH" in txt.upper() or "NATIONALITY" in txt.upper():
            score += 6
        if rw > rh:
            # Passport data pages are landscape
            score += 5

        # Check for vertical text penalty (if words are taller than they are wide)
        try:
            d = pytesseract.image_to_data(rotated, output_type=Output.DICT)
            widths = [w for i, w in enumerate(d["width"]) if d["text"][i].strip()]
            heights = [h for i, h in enumerate(d["height"]) if d["text"][i].strip()]
            if widths and heights:
                mean_w = sum(widths) / len(widths)
                mean_h = sum(heights) / len(heights)
                if mean_w > mean_h:
                    score += 10  # Natural horizontal text
                else:
                    score -= 10  # Sideways vertical text
        except Exception:
            pass

        if score > best_score:
            best_score = score
            best_img = rotated
            best_angle = angle

        if score >= 40:
            break

    return best_img, best_angle, f"scored_{best_angle}deg"



def preprocess_standard(image: np.ndarray) -> np.ndarray:
    """Standard preprocessing: deskew -> grayscale -> denoise -> Otsu threshold."""
    deskewed = deskew_image(image)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY) if len(deskewed.shape) == 3 else deskewed
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresholded


def preprocess_adaptive_clahe(image: np.ndarray) -> np.ndarray:
    """Alternate preprocessing: CLAHE contrast enhancement -> adaptive thresholding."""
    deskewed = deskew_image(image)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY) if len(deskewed.shape) == 3 else deskewed
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return adaptive


NATIONALITY_MAP = {
    "IND": "INDIAN",
    "INDIA": "INDIAN",
    "INDIAN": "INDIAN",
    "USA": "AMERICAN",
    "UNITED STATES": "AMERICAN",
    "GBR": "BRITISH",
    "CAN": "CANADIAN",
    "AUS": "AUSTRALIAN",
    "DEU": "GERMAN",
    "FRA": "FRENCH",
    "CHN": "CHINESE",
    "JPN": "JAPANESE",
}


class OcrService:
    """Production-grade OCR service with orientation normalization, ICAO 9303 MRZ parsing, and cross-validation."""

    def _to_cv_image(self, image_input: bytes | str | np.ndarray) -> np.ndarray:
        if isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(BytesIO(image_input)).convert("RGB")
            return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found at {image_input}")
            img = cv2.imread(image_input)
            if img is None:
                pil_img = Image.open(image_input).convert("RGB")
                return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            return img
        elif isinstance(image_input, np.ndarray):
            return image_input
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

    def extract_text_and_confidence(self, preprocessed_image: np.ndarray) -> Tuple[str, float]:
        if not is_tesseract_available():
            raise RuntimeError("Tesseract OCR is not installed or not in PATH.")

        extracted_text = pytesseract.image_to_string(preprocessed_image)
        data = pytesseract.image_to_data(preprocessed_image, output_type=Output.DICT)

        confidences = []
        for i in range(len(data["text"])):
            word = data["text"][i].strip()
            conf = float(data["conf"][i])
            if word and conf >= 0:
                confidences.append(conf)

        average_confidence = round(sum(confidences) / len(confidences) / 100, 2) if confidences else 0.0
        return extracted_text, average_confidence

    def parse_mrz(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse ICAO 9303 TD3 Passport MRZ (2 lines x 44 chars).
        Performs 7-3-1 weight check-digit validation on passport number, DOB, and expiry.
        """
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        mrz_candidates = []
        for line in lines:
            cleaned = line.replace(" ", "")
            if len(cleaned) >= 25 and ("<" in cleaned or "P<" in cleaned):
                mrz_candidates.append(cleaned)

        # Look for 2 consecutive or near-consecutive MRZ lines
        l1, l2 = None, None
        for i in range(len(mrz_candidates)):
            if mrz_candidates[i].startswith("P<") or mrz_candidates[i].startswith("P"):
                l1 = mrz_candidates[i]
                if i + 1 < len(mrz_candidates):
                    l2 = mrz_candidates[i + 1]
                break

        if not l1 or not l2:
            return None

        # Ensure minimum length with filler chevrons
        l1 = (l1 + "<" * 44)[:44]
        l2 = (l2 + "<" * 44)[:44]

        # Line 1 parsing: Type (0..2), Issuing country (2..5), Name (5..44)
        doc_type = l1[0:2].replace("<", "")
        issuing_country = l1[2:5].replace("<", "")
        name_raw = l1[5:44]
        # Clean filler sequences at end of name
        clean_name_raw = re.split(r"<{3,}", name_raw)[0]
        name_parts = [p.replace("<", " ").strip() for p in clean_name_raw.split("<<") if p.replace("<", " ").strip()]
        surname = name_parts[0] if len(name_parts) > 0 else ""
        given_names = name_parts[1] if len(name_parts) > 1 else ""
        full_name = f"{given_names} {surname}".strip() if given_names else surname


        # Line 2 parsing:
        # 0..9: Passport number
        pass_raw = l2[0:9].replace("<", "")
        pass_cd = l2[9]
        pass_valid = mrz_check_digit(pass_raw) == pass_cd

        # 10..13: Nationality (character confusion 1 -> I, 0 -> O)
        nat_code = l2[10:13].replace("1", "I").replace("0", "O")
        nationality = NATIONALITY_MAP.get(nat_code, nat_code)

        # 13..19: DOB (YYMMDD)
        dob_raw = l2[13:19]
        dob_cd = l2[19]
        dob_valid = mrz_check_digit(dob_raw) == dob_cd
        try:
            y, m, d = int(dob_raw[:2]), dob_raw[2:4], dob_raw[4:6]
            century = "19" if y > 30 else "20"
            dob_formatted = f"{d}/{m}/{century}{dob_raw[:2]}"
        except Exception:
            dob_formatted = None

        # 20: Sex
        sex = l2[20] if l2[20] in ["M", "F"] else None

        # 21..27: Expiry date (YYMMDD)
        exp_raw = l2[21:27]
        exp_cd = l2[27]
        exp_valid = mrz_check_digit(exp_raw) == exp_cd
        try:
            ey, em, ed = int(exp_raw[:2]), exp_raw[2:4], exp_raw[4:6]
            exp_formatted = f"{ed}/{em}/20{exp_raw[:2]}"
        except Exception:
            exp_formatted = None

        return {
            "mrz_detected": True,
            "document_type": doc_type or "P",
            "issuing_country": issuing_country,
            "name": full_name,
            "surname": surname,
            "given_names": given_names,
            "passport_number": pass_raw,
            "passport_number_valid": pass_valid,
            "nationality": nationality,
            "nationality_code": nat_code,
            "date_of_birth": dob_formatted,
            "date_of_birth_valid": dob_valid,
            "sex": sex,
            "expiry_date": exp_formatted,
            "expiry_date_valid": exp_valid,
            "raw_line1": l1,
            "raw_line2": l2
        }

    @staticmethod
    def extract_visual_fields(text: str) -> Dict[str, Optional[str]]:
        """Extract identity fields using context-aware bilingual layout patterns."""
        fields = {}

        # 1. Given name / Full name
        name_m = re.search(r"(?:Given Name\(s\)|Given Name|Name|NAME)[:\s\S]*?\n([A-Z\s]{2,35})\n", text, re.IGNORECASE)
        if name_m:
            clean_name = name_m.group(1).split("\n")[0].strip()
            # Avoid matching subsequent headers
            if not any(hdr in clean_name.upper() for hdr in ["SEX", "BIRTH", "DATE", "PLACE"]):
                fields["name"] = clean_name
        if not fields.get("name"):
            direct_name_m = re.search(r"NAME[:\s]+([A-Z\s]{2,30})", text)
            if direct_name_m:
                fields["name"] = direct_name_m.group(1).split("\n")[0].strip()

        # 2. Passport number (supports 1 or 2 prefix letters + 6 to 8 digits)
        pass_m = re.search(r"(?:Passport No|Passport Number)[\s\S]*?\b([A-Z]{1,2}\d{6,8})\b", text, re.IGNORECASE)
        if pass_m:
            fields["passport_number"] = pass_m.group(1)
        else:
            standalone_pass = re.search(r"\b([A-Z]{1,2}\d{7})\b", text)
            if standalone_pass:
                fields["passport_number"] = standalone_pass.group(1)

        # 3. Date of Birth
        dob_m = re.search(r"(?:Date of Birth|DOB)[\s\S]*?(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if dob_m:
            fields["date_of_birth"] = dob_m.group(1)

        # 4. Date of Expiry
        exp_m = re.search(r"(?:Date of Expiry|Expiry Date|EXPIRY)[\s\S]*?(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if exp_m:
            fields["expiry_date"] = exp_m.group(1)

        # 5. Date of Issue
        iss_m = re.search(r"(?:Date of Issue|Issue Date|ISSUE)[\s\S]*?(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        if iss_m:
            fields["date_of_issue"] = iss_m.group(1)

        # 6. Nationality
        nat_m = re.search(r"(?:Nationality)[\s\S]*?\b(INDIAN|IND|AMERICAN|USA|BRITISH|GBR|CANADIAN|CAN)\b", text, re.IGNORECASE)
        if nat_m:
            code = nat_m.group(1).upper()
            fields["nationality"] = NATIONALITY_MAP.get(code, code)
        elif "INDIAN" in text.upper():
            fields["nationality"] = "INDIAN"

        return fields

    def extract(self, image_input: bytes | str | np.ndarray) -> Dict[str, Any]:
        """
        Run the complete OCR pipeline:
        1. Orientation normalization (0°, 90°, 180°, 270°)
        2. Image deskewing & preprocessing
        3. ICAO 9303 MRZ extraction & check-digit verification
        4. Bilingual layout visual field parsing
        5. Visual <-> MRZ cross-validation and structured confidence scoring
        """
        raw_cv = self._to_cv_image(image_input)
        adaptive_actions = []

        # 1. Orientation Normalization
        canonical_img, angle_rotated, orient_method = normalize_document_orientation(raw_cv)
        if angle_rotated != 0:
            adaptive_actions.append({
                "action": "ORIENTATION_CORRECTION",
                "reason": f"Detected {angle_rotated}° orientation offset ({orient_method}). Automatically rotated image to canonical upright reading position.",
                "rotation_angle": angle_rotated
            })

        # 2. Text Recognition on Canonical Upright Image
        preprocessed = preprocess_standard(canonical_img)
        text, confidence = self.extract_text_and_confidence(preprocessed)

        # Adaptive trigger: low confidence retry with CLAHE
        if confidence < 0.70 and len(text.strip()) > 0:
            alt_preprocessed = preprocess_adaptive_clahe(canonical_img)
            alt_text, alt_confidence = self.extract_text_and_confidence(alt_preprocessed)
            adaptive_actions.append({
                "action": "OCR_RETRY",
                "reason": f"Initial OCR confidence ({confidence:.2f}) was below 0.70 threshold. Retried with adaptive CLAHE preprocessing.",
                "previous_confidence": confidence,
                "new_confidence": alt_confidence
            })
            if alt_confidence > confidence or len(alt_text) > len(text):
                text = alt_text
                confidence = max(confidence, alt_confidence)

        # 3. MRZ Parsing
        mrz_data = self.parse_mrz(text)

        # 4. Visual Field Parsing
        visual_fields = self.extract_visual_fields(text)

        # 5. Field Fusion & Cross-Validation
        fields = {
            "document_type": "PASSPORT",
            "name": None,
            "passport_number": None,
            "nationality": None,
            "date_of_birth": None,
            "date_of_issue": visual_fields.get("date_of_issue"),
            "expiry_date": None
        }

        field_sources = {}
        field_confidences = {}

        # Cross-validation logic
        # Name:
        if mrz_data and mrz_data.get("name"):
            fields["name"] = mrz_data["name"]
            field_sources["name"] = "MRZ"
            field_confidences["name"] = 0.98 if mrz_data["name"] == visual_fields.get("name") else 0.94
        elif visual_fields.get("name"):
            fields["name"] = visual_fields["name"]
            field_sources["name"] = "Visual"
            field_confidences["name"] = 0.85

        # Passport Number:
        if mrz_data and mrz_data.get("passport_number"):
            fields["passport_number"] = mrz_data["passport_number"]
            field_sources["passport_number"] = "MRZ (Checksum Validated)" if mrz_data.get("passport_number_valid") else "MRZ"
            field_confidences["passport_number"] = 0.99 if mrz_data.get("passport_number_valid") else 0.90
        elif visual_fields.get("passport_number"):
            fields["passport_number"] = visual_fields["passport_number"]
            field_sources["passport_number"] = "Visual"
            field_confidences["passport_number"] = 0.85

        # Nationality:
        if mrz_data and mrz_data.get("nationality"):
            fields["nationality"] = mrz_data["nationality"]
            field_sources["nationality"] = "MRZ"
            field_confidences["nationality"] = 0.98
        elif visual_fields.get("nationality"):
            fields["nationality"] = visual_fields["nationality"]
            field_sources["nationality"] = "Visual"
            field_confidences["nationality"] = 0.88

        # Date of Birth:
        if mrz_data and mrz_data.get("date_of_birth"):
            fields["date_of_birth"] = mrz_data["date_of_birth"]
            field_sources["date_of_birth"] = "MRZ (Checksum Validated)" if mrz_data.get("date_of_birth_valid") else "MRZ"
            field_confidences["date_of_birth"] = 0.99 if mrz_data.get("date_of_birth_valid") else 0.90
        elif visual_fields.get("date_of_birth"):
            fields["date_of_birth"] = visual_fields["date_of_birth"]
            field_sources["date_of_birth"] = "Visual"
            field_confidences["date_of_birth"] = 0.85

        # Expiry Date:
        if mrz_data and mrz_data.get("expiry_date"):
            fields["expiry_date"] = mrz_data["expiry_date"]
            field_sources["expiry_date"] = "MRZ (Checksum Validated)" if mrz_data.get("expiry_date_valid") else "MRZ"
            field_confidences["expiry_date"] = 0.99 if mrz_data.get("expiry_date_valid") else 0.90
        elif visual_fields.get("expiry_date"):
            fields["expiry_date"] = visual_fields["expiry_date"]
            field_sources["expiry_date"] = "Visual"
            field_confidences["expiry_date"] = 0.85

        # Issue Date:
        if visual_fields.get("date_of_issue"):
            fields["date_of_issue"] = visual_fields["date_of_issue"]
            field_sources["date_of_issue"] = "Visual"
            field_confidences["date_of_issue"] = 0.85

        # Structured composite confidence
        valid_fields = [v for k, v in fields.items() if v is not None and k != "document_type"]
        if mrz_data and mrz_data.get("passport_number_valid") and mrz_data.get("expiry_date_valid"):
            overall_confidence = 0.96
        elif len(valid_fields) >= 4:
            overall_confidence = max(0.85, confidence)
        else:
            overall_confidence = confidence

        return {
            "document_type": "PASSPORT",
            "fields": fields,
            "field_sources": field_sources,
            "confidence": field_confidences,
            "ocr_confidence": overall_confidence,
            "mrz_data": mrz_data,
            "raw_text": text,
            "canonical_image": canonical_img,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
ocr_service = OcrService()


# Legacy standalone helper
def extract_document(image_path: str) -> Dict[str, Any]:
    res = ocr_service.extract(image_path)
    res["fields"]["ocr_confidence"] = res["ocr_confidence"]
    return res["fields"]