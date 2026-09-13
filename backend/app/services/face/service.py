"""
Face Verification Service
Compares identity photo on the document with live/presented selfie photo.
Handles missing selfie gracefully (status: SKIPPED) without failing verification.
Includes OpenCV Haar face detection and cosine similarity scoring.
"""
import os
from io import BytesIO
from typing import Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

# Initialize Haar Cascade for frontal face detection
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Calculate cosine similarity between two feature vectors."""
    a = np.asarray(v1, dtype=np.float32).flatten()
    b = np.asarray(v2, dtype=np.float32).flatten()
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    sim = float(np.dot(a, b) / (norm_a * norm_b))
    return max(0.0, min(1.0, sim))


class FaceService:
    """Face verification service with optional selfie support and adaptive review threshold."""

    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def _load_cv_image(self, image_input: bytes | str | np.ndarray) -> np.ndarray:
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

    def detect_face(self, cv_image: np.ndarray) -> Tuple[bool, Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """Detect and crop the primary face in an image."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(40, 40)
        )

        if len(faces) == 0:
            return False, None, None

        # Sort by area to pick largest face
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        x, y, w, h = faces[0]
        crop = cv_image[y:y + h, x:x + w]
        return True, crop, (int(x), int(y), int(w), int(h))

    def extract_face_features(self, face_crop: np.ndarray) -> np.ndarray:
        """
        Extract normalized multi-feature face descriptor.
        Uses standardized spatial color/intensity histograms and gradient projections.
        """
        resized = cv2.resize(face_crop, (128, 128))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Color histograms across channels
        hist_b = cv2.calcHist([resized], [0], None, [32], [0, 256])
        hist_g = cv2.calcHist([resized], [1], None, [32], [0, 256])
        hist_r = cv2.calcHist([resized], [2], None, [32], [0, 256])

        # Spatial grid histograms (4x4 cells)
        grid_features = []
        cell_h, cell_w = 32, 32
        for row in range(4):
            for col in range(4):
                cell = gray[row * cell_h:(row + 1) * cell_h, col * cell_w:(col + 1) * cell_w]
                cell_hist = cv2.calcHist([cell], [0], None, [16], [0, 256])
                grid_features.append(cell_hist)

        # Gradients (Sobel)
        sobelx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, _ = cv2.cartToPolar(sobelx, sobely)
        hist_mag = cv2.calcHist([mag.astype(np.uint8)], [0], None, [32], [0, 256])

        feature_vector = np.concatenate(
            [hist_b.flatten(), hist_g.flatten(), hist_r.flatten(), hist_mag.flatten()] +
            [gf.flatten() for gf in grid_features]
        )

        norm = np.linalg.norm(feature_vector)
        if norm > 0:
            feature_vector = feature_vector / norm
        return feature_vector

    def verify(
        self,
        document_image: bytes | str | np.ndarray,
        selfie_image: Optional[bytes | str | np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Verify facial identity between document and presented photo.
        If selfie is omitted, returns status: SKIPPED without failing verification.
        """
        if selfie_image is None:
            return {
                "status": "SKIPPED",
                "reason": "No selfie provided",
                "face_detected_document": False,
                "face_detected_verification": False,
                "similarity": None,
                "threshold": self.threshold,
                "match": None,
                "verification_status": "skipped",
                "adaptive_actions": []
            }

        # Load images
        doc_cv = self._load_cv_image(document_image)
        selfie_cv = self._load_cv_image(selfie_image)

        doc_found, doc_crop, doc_box = self.detect_face(doc_cv)
        selfie_found, selfie_crop, selfie_box = self.detect_face(selfie_cv)

        if not doc_found or doc_crop is None:
            return {
                "status": "FAIL",
                "reason": "No face detected in document image.",
                "face_detected_document": False,
                "face_detected_verification": selfie_found,
                "similarity": 0.0,
                "threshold": self.threshold,
                "match": False,
                "verification_status": "no_face_document",
                "adaptive_actions": []
            }

        if not selfie_found or selfie_crop is None:
            return {
                "status": "FAIL",
                "reason": "No face detected in verification selfie.",
                "face_detected_document": True,
                "face_detected_verification": False,
                "similarity": 0.0,
                "threshold": self.threshold,
                "match": False,
                "verification_status": "no_face_selfie",
                "adaptive_actions": []
            }

        # Extract features and compare
        feat_doc = self.extract_face_features(doc_crop)
        feat_selfie = self.extract_face_features(selfie_crop)

        sim = cosine_similarity(feat_doc, feat_selfie)
        sim_pct = round(sim * 100, 1)

        # Check threshold
        matched = sim >= self.threshold
        adaptive_actions = []

        # Adaptive trigger: borderline match
        if abs(sim - self.threshold) <= 0.05:
            verification_status = "ambiguous_review"
            adaptive_actions.append({
                "action": "FACE_BORDERLINE_FLAG",
                "reason": f"Face similarity ({sim:.2f}) is close to threshold ({self.threshold:.2f}). Flagged for manual facial review.",
                "similarity": sim,
                "threshold": self.threshold
            })
        elif matched:
            verification_status = "high_similarity"
        else:
            verification_status = "low_similarity"

        return {
            "status": "completed",
            "face_detected_document": True,
            "face_detected_verification": True,
            "similarity": round(float(sim), 4),
            "similarity_percent": sim_pct,
            "threshold": self.threshold,
            "match": matched,
            "verification_status": verification_status,
            "document_face_box": doc_box,
            "selfie_face_box": selfie_box,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
face_service = FaceService()
