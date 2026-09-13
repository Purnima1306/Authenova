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


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Detect and correct text rotation in a document image."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255)
    )
    return deskewed


def preprocess_standard(image: np.ndarray) -> np.ndarray:
    """Standard preprocessing: deskew -> grayscale -> denoise -> Otsu threshold."""
    deskewed = deskew_image(image)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    _, thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresholded


def preprocess_adaptive_clahe(image: np.ndarray) -> np.ndarray:
    """Alternate preprocessing: CLAHE contrast enhancement -> adaptive thresholding."""
    deskewed = deskew_image(image)
    gray = cv2.cvtColor(deskewed, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    adaptive = cv2.adaptiveThreshold(
        enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    return adaptive


class OcrService:
    """Service wrapping OCR execution and field extraction with adaptive retry."""

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

        if confidences:
            average_confidence = round(sum(confidences) / len(confidences) / 100, 2)
        else:
            average_confidence = 0.0

        return extracted_text, average_confidence

    @staticmethod
    def extract_passport_number(text: str) -> Optional[str]:
        match = re.search(r"\b[A-Z]\d{7}\b", text)
        return match.group() if match else None

    @staticmethod
    def extract_name(text: str) -> Optional[str]:
        match = re.search(r"NAME:\s*([A-Za-z\s]+)", text)
        if match:
            clean = match.group(1).split("\n")[0].strip()
            return clean if clean else None
        return None

    @staticmethod
    def extract_dob(text: str) -> Optional[str]:
        match = re.search(r"(?:DATE OF BIRTH|DOB)[\s:]+(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def extract_expiry(text: str) -> Optional[str]:
        match = re.search(r"(?:DATE OF EXPIRY|EXPIRY)[\s:]+(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def extract_nationality(text: str) -> Optional[str]:
        match = re.search(r"NATIONALITY[:\s]+([A-Z]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    @staticmethod
    def extract_issue_date(text: str) -> Optional[str]:
        match = re.search(r"(?:DATE OF ISSUE|ISSUE)[\s:]+(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
        return match.group(1) if match else None

    @staticmethod
    def extract_document_type(text: str) -> str:
        if re.search(r"\bPASSPORT\b", text, re.IGNORECASE):
            return "PASSPORT"
        if re.search(r"\bAADHAAR\b", text, re.IGNORECASE):
            return "AADHAAR"
        if re.search(r"\bVISA\b", text, re.IGNORECASE):
            return "VISA"
        if re.search(r"\bPERMIT\b", text, re.IGNORECASE):
            return "PERMIT"
        return "UNKNOWN"

    def extract(self, image_input: bytes | str | np.ndarray) -> Dict[str, Any]:
        """
        Run OCR extraction with adaptive retry if initial confidence is low.
        """
        cv_img = self._to_cv_image(image_input)

        # First pass: standard preprocessing
        preprocessed = preprocess_standard(cv_img)
        text, confidence = self.extract_text_and_confidence(preprocessed)

        adaptive_actions = []

        # Adaptive trigger: low confidence retry
        if confidence < 0.70 and len(text.strip()) > 0:
            alt_preprocessed = preprocess_adaptive_clahe(cv_img)
            alt_text, alt_confidence = self.extract_text_and_confidence(alt_preprocessed)
            adaptive_actions.append({
                "action": "OCR_RETRY",
                "reason": f"Initial OCR confidence ({confidence}) was below 0.70 threshold. Retried with adaptive CLAHE preprocessing.",
                "previous_confidence": confidence,
                "new_confidence": alt_confidence
            })
            if alt_confidence > confidence:
                text = alt_text
                confidence = alt_confidence

        doc_type = self.extract_document_type(text)
        name = self.extract_name(text)
        passport_num = self.extract_passport_number(text)
        nationality = self.extract_nationality(text)
        dob = self.extract_dob(text)
        issue_date = self.extract_issue_date(text)
        expiry_date = self.extract_expiry(text)

        fields = {
            "document_type": doc_type,
            "name": name,
            "passport_number": passport_num,
            "nationality": nationality,
            "date_of_birth": dob,
            "date_of_issue": issue_date,
            "expiry_date": expiry_date
        }

        # Field level confidences (heuristic: present fields inherit overall confidence)
        field_confidences = {
            k: (confidence if v is not None else 0.0)
            for k, v in fields.items()
        }

        return {
            "document_type": doc_type,
            "fields": fields,
            "confidence": field_confidences,
            "ocr_confidence": confidence,
            "raw_text": text,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
ocr_service = OcrService()


# Legacy standalone helper
def extract_document(image_path: str) -> Dict[str, Any]:
    res = ocr_service.extract(image_path)
    res["fields"]["ocr_confidence"] = res["ocr_confidence"]
    return res["fields"]


if __name__ == "__main__":
    import sys
    import json

    img = sys.argv[1] if len(sys.argv) > 1 else "data/samples/documents/test_document.png"
    result = ocr_service.extract(img)
    print(json.dumps(result, indent=4, default=str))