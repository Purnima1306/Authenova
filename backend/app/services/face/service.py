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
# Cascades for robust face & eye detection
CASCADE_ALT2 = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
CASCADE_ALT = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt.xml")
CASCADE_DEFAULT = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
EYE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

try:
    from keras_facenet import FaceNet
    facenet_embedder = FaceNet()
except Exception:
    facenet_embedder = None


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
    """
    Production-grade biometric face verification service.
    Isolates passport portrait, aligns eyes, extracts FaceNet 512-d embeddings,
    and calculates empirically calibrated cross-domain similarity.
    """

    def __init__(self, threshold: float = 0.58):
        # Calibrated threshold for ID-halftone vs live webcam comparison (0.58)
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

    def detect_and_align_face(
        self,
        cv_image: np.ndarray,
        is_document: bool = False
    ) -> Tuple[bool, Optional[np.ndarray], Optional[Dict[str, int]]]:
        """
        Detect, align, and crop the primary face.
        Uses multi-cascade detection, portrait ROI heuristics, eye horizontal alignment,
        and adds a 20% margin for natural facial structure.
        """
        img = cv_image.copy()

        # If document is vertical/portrait (h > w), rotate 270 degrees to upright landscape
        if is_document and img.shape[0] > img.shape[1]:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Multi-cascade cascade detection strategy
        faces = []
        for cascade, sf, mn in [
            (CASCADE_ALT2, 1.05, 3),
            (CASCADE_ALT, 1.10, 4),
            (CASCADE_DEFAULT, 1.10, 4),
        ]:
            detected = cascade.detectMultiScale(gray, scaleFactor=sf, minNeighbors=mn, minSize=(50, 50))
            if len(detected) > 0:
                faces = detected
                break

        # Fallback for passport document: scan standard ICAO portrait region
        if len(faces) == 0 and is_document:
            roi_x = int(0.05 * w)
            roi_y = int(0.15 * h)
            roi_w = int(0.45 * w)
            roi_h = int(0.70 * h)
            roi_gray = gray[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
            roi_faces = CASCADE_ALT2.detectMultiScale(roi_gray, scaleFactor=1.05, minNeighbors=2, minSize=(40, 40))
            if len(roi_faces) > 0:
                rx, ry, rw, rh = sorted(roi_faces, key=lambda f: f[2] * f[3], reverse=True)[0]
                faces = [[roi_x + rx, roi_y + ry, rw, rh]]

        if len(faces) == 0:
            return False, None, None

        # Select largest face candidate
        faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
        fx, fy, fw, fh = [int(v) for v in faces[0]]

        # Add 20% margin around bounding box
        pad_x = int(0.20 * fw)
        pad_y = int(0.20 * fh)
        x1 = max(0, fx - pad_x)
        y1 = max(0, fy - pad_y)
        x2 = min(w, fx + fw + pad_x)
        y2 = min(h, fy + fh + pad_y)

        crop = img[y1:y2, x1:x2]

        # Optional eye alignment
        try:
            crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            eyes = EYE_CASCADE.detectMultiScale(crop_gray, 1.1, 3, minSize=(20, 20))
            if len(eyes) >= 2:
                # Sort eyes left-to-right
                eyes = sorted(eyes, key=lambda e: e[0])
                ex1, ey1 = eyes[0][0] + eyes[0][2] // 2, eyes[0][1] + eyes[0][3] // 2
                ex2, ey2 = eyes[1][0] + eyes[1][2] // 2, eyes[1][1] + eyes[1][3] // 2
                dy = ey2 - ey1
                dx = ex2 - ex1
                angle = float(np.degrees(np.arctan2(dy, dx)))
                if abs(angle) < 30.0:  # Only correct small head tilts
                    center = (crop.shape[1] // 2, crop.shape[0] // 2)
                    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
                    crop = cv2.warpAffine(crop, rot_mat, (crop.shape[1], crop.shape[0]), flags=cv2.INTER_CUBIC)
        except Exception:
            pass

        # Resize to canonical FaceNet model input (160, 160) RGB
        rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        aligned_160 = cv2.resize(rgb_crop, (160, 160), interpolation=cv2.INTER_AREA)

        bbox_dict = {"x": fx, "y": fy, "width": fw, "height": fh}
        return True, aligned_160, bbox_dict

    def extract_descriptor_fallback(self, face_160: np.ndarray) -> np.ndarray:
        """Fallback multi-channel spatial histogram descriptor if FaceNet is unavailable."""
        gray = cv2.cvtColor(face_160, cv2.COLOR_RGB2GRAY)
        hsv = cv2.cvtColor(face_160, cv2.COLOR_RGB2HSV)
        hist_hsv = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256]).flatten()

        grid = []
        for r in range(4):
            for c in range(4):
                cell = gray[r * 40:(r + 1) * 40, c * 40:(c + 1) * 40]
                cell_hist = cv2.calcHist([cell], [0], None, [16], [0, 256]).flatten()
                grid.append(cell_hist)

        vec = np.concatenate([hist_hsv] + grid)
        norm = np.linalg.norm(vec)
        return (vec / norm) if norm > 0 else vec

    def verify(
        self,
        document_image: bytes | str | np.ndarray,
        selfie_image: Optional[bytes | str | np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Verify facial identity between document portrait and presented selfie photo.
        If selfie is omitted, returns status: SKIPPED without failing verification.
        """
        if selfie_image is None:
            return {
                "status": "SKIPPED",
                "reason": "No selfie provided",
                "face_detected_document": False,
                "face_detected_verification": False,
                "document_face_detected": False,
                "presented_face_detected": False,
                "similarity": None,
                "threshold": self.threshold,
                "match": None,
                "model": "None",
                "verification_status": "skipped",
                "adaptive_actions": []
            }

        # Load images
        doc_cv = self._load_cv_image(document_image)
        selfie_cv = self._load_cv_image(selfie_image)

        doc_found, doc_crop, doc_box = self.detect_and_align_face(doc_cv, is_document=True)
        selfie_found, selfie_crop, selfie_box = self.detect_and_align_face(selfie_cv, is_document=False)

        if not doc_found or doc_crop is None:
            return {
                "status": "FAIL",
                "reason": "No face detected in document image portrait region.",
                "face_detected_document": False,
                "face_detected_verification": selfie_found,
                "similarity": 0.0,
                "threshold": self.threshold,
                "match": False,
                "model": "FaceNet 512-d" if facenet_embedder is not None else "Fallback",
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
                "model": "FaceNet 512-d" if facenet_embedder is not None else "Fallback",
                "verification_status": "no_face_selfie",
                "adaptive_actions": []
            }

        # Embedding generation
        model_name = "FaceNet 512-d"
        if facenet_embedder is not None:
            try:
                embs = facenet_embedder.embeddings([doc_crop, selfie_crop])
                v1 = embs[0] / np.linalg.norm(embs[0])
                v2 = embs[1] / np.linalg.norm(embs[1])
                sim = float(np.dot(v1, v2))
            except Exception as e:
                v1 = self.extract_descriptor_fallback(doc_crop)
                v2 = self.extract_descriptor_fallback(selfie_crop)
                sim = cosine_similarity(v1, v2)
                model_name = f"Fallback (Error: {str(e)[:30]})"
        else:
            v1 = self.extract_descriptor_fallback(doc_crop)
            v2 = self.extract_descriptor_fallback(selfie_crop)
            sim = cosine_similarity(v1, v2)
            model_name = "Fallback Histogram Descriptor"

        sim = max(0.0, min(1.0, float(sim)))
        sim_pct = round(sim * 100, 1)
        matched = sim >= self.threshold

        adaptive_actions = []
        if abs(sim - self.threshold) <= 0.06:
            verification_status = "ambiguous_review"
            adaptive_actions.append({
                "action": "FACE_BORDERLINE_FLAG",
                "reason": f"Face similarity ({sim:.2f}) is close to calibrated threshold ({self.threshold:.2f}). Flagged for manual facial review.",
                "similarity": sim,
                "threshold": self.threshold
            })
        elif matched:
            verification_status = "high_similarity"
        else:
            verification_status = "low_similarity"

        return {
            "status": "completed",
            "document_face_detected": True,
            "presented_face_detected": True,
            "face_detected_document": True,
            "face_detected_verification": True,
            "similarity": round(sim, 4),
            "similarity_percent": sim_pct,
            "threshold": self.threshold,
            "match": matched,
            "model": model_name,
            "verification_status": verification_status,
            "document_face_bbox": doc_box,
            "presented_face_bbox": selfie_box,
            "document_face_box": doc_box,
            "selfie_face_box": selfie_box,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
face_service = FaceService()

