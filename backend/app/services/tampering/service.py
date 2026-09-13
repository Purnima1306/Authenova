"""
Tampering Detection Service
Performs multi-signal digital forensics on document images:
1. Error Level Analysis (ELA)
2. ORB Keypoint Copy-Move Forgery Detection
3. EXIF Metadata Inspection
Includes adaptive deep scan for borderline suspicion scores.
"""
from io import BytesIO
from typing import Dict, Any, List, Optional
import os
import cv2
import numpy as np
from PIL import Image, ImageChops
from PIL.ExifTags import TAGS


class TamperingService:
    """Multi-method document tampering and manipulation detection."""

    @staticmethod
    def _load_image(image_input: bytes | str) -> tuple[Image.Image, np.ndarray]:
        """Load image as both PIL Image and OpenCV BGR numpy array."""
        if isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(BytesIO(image_input)).convert("RGB")
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        else:
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found at {image_input}")
            pil_img = Image.open(image_input).convert("RGB")
            cv_img = cv2.imread(image_input)
            if cv_img is None:
                cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return pil_img, cv_img

    def calculate_ela(self, pil_image: Image.Image, quality: int = 90) -> tuple[float, Image.Image]:
        """Compute Error Level Analysis mean difference score."""
        buffer = BytesIO()
        pil_image.save(buffer, "JPEG", quality=quality)
        buffer.seek(0)
        compressed = Image.open(buffer).convert("RGB")

        diff = ImageChops.difference(pil_image, compressed)
        diff_array = np.array(diff, dtype=np.float32)
        score = float(np.mean(diff_array))
        return score, diff

    def detect_copy_move(
        self,
        cv_image: np.ndarray,
        nfeatures: int = 2000,
        match_ratio: float = 0.75,
        min_distance: float = 50.0
    ) -> Dict[str, Any]:
        """Detect duplicated visual regions using ORB feature matching."""
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        orb = cv2.ORB_create(nfeatures=nfeatures)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(descriptors) < 5:
            return {
                "detected": False,
                "suspicious_matches": 0,
                "flagged_region": None,
                "keypoints_count": len(keypoints) if keypoints else 0
            }

        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        try:
            matches = bf.knnMatch(descriptors, descriptors, k=3)
        except Exception:
            return {
                "detected": False,
                "suspicious_matches": 0,
                "flagged_region": None,
                "keypoints_count": len(keypoints)
            }

        suspicious_matches = []
        suspicious_points = []

        for match_group in matches:
            valid = [m for m in match_group if m.queryIdx != m.trainIdx]
            if len(valid) < 2:
                continue

            m, n = valid[0], valid[1]
            if m.distance < match_ratio * n.distance:
                p1 = np.array(keypoints[m.queryIdx].pt)
                p2 = np.array(keypoints[m.trainIdx].pt)
                dist = np.linalg.norm(p1 - p2)
                if dist > min_distance:
                    suspicious_matches.append(m)
                    suspicious_points.append(p1)

        detected = len(suspicious_matches) >= 5
        flagged_region = None

        if detected and suspicious_points:
            pts = np.array(suspicious_points, dtype=np.int32)
            x, y, bw, bh = cv2.boundingRect(pts)
            # Add padding
            x_pad = max(0, x - 10)
            y_pad = max(0, y - 10)
            w_pad = min(w - x_pad, bw + 20)
            h_pad = min(h - y_pad, bh + 20)

            flagged_region = {
                "top": f"{round((y_pad / h) * 100, 1)}%",
                "left": f"{round((x_pad / w) * 100, 1)}%",
                "width": f"{round((w_pad / w) * 100, 1)}%",
                "height": f"{round((h_pad / h) * 100, 1)}%"
            }

        return {
            "detected": detected,
            "suspicious_matches": len(suspicious_matches),
            "flagged_region": flagged_region,
            "keypoints_count": len(keypoints)
        }

    def inspect_metadata(self, pil_image: Image.Image) -> Dict[str, Any]:
        """Examine EXIF metadata for editing software signatures."""
        exif = pil_image.getexif()
        tags: Dict[str, str] = {}
        suspicious_software = False
        evidence = []

        editing_signatures = ["adobe", "photoshop", "gimp", "canva", "pixlr", "paint.net"]

        for tag_id, val in exif.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            str_val = str(val)
            tags[tag_name] = str_val
            for sig in editing_signatures:
                if sig in str_val.lower():
                    suspicious_software = True
                    evidence.append(f"Image contains {tag_name} referencing '{str_val}'")

        return {
            "has_exif": len(tags) > 0,
            "tags_count": len(tags),
            "suspicious_software": suspicious_software,
            "evidence": evidence
        }

    def analyze(self, image_input: bytes | str) -> Dict[str, Any]:
        """
        Run the complete tampering analysis pipeline on arbitrary image input.
        """
        pil_img, cv_img = self._load_image(image_input)

        # 1. ELA
        raw_ela, _ = self.calculate_ela(pil_img)
        # Normalize: raw ELA on normal JPEG is typically 2.0-8.0; high variance > 12.0
        normalized_ela = min(raw_ela / 15.0, 1.0)

        # 2. Copy-Move
        cm_result = self.detect_copy_move(cv_img, nfeatures=2000, match_ratio=0.75)

        # 3. Metadata
        meta_result = self.inspect_metadata(pil_img)

        # Initial scoring
        cm_score = min(cm_result["suspicious_matches"] / 25.0, 1.0) if cm_result["detected"] else 0.0
        meta_score = 0.8 if meta_result["suspicious_software"] else 0.0

        tampering_score = round(
            (normalized_ela * 0.35) + (cm_score * 0.50) + (meta_score * 0.15),
            4
        )

        # Adaptive deep scan trigger for borderline cases
        adaptive_actions = []
        if 0.30 <= tampering_score <= 0.65:
            # Rerun copy-move with more sensitive parameters
            deeper_cm = self.detect_copy_move(cv_img, nfeatures=3000, match_ratio=0.80)
            adaptive_actions.append({
                "action": "TAMPERING_DEEP_SCAN",
                "reason": f"Borderline tampering score ({tampering_score:.2f}) triggered secondary high-sensitivity ORB scan.",
                "previous_score": tampering_score,
                "secondary_matches": deeper_cm["suspicious_matches"]
            })
            if deeper_cm["detected"]:
                cm_result = deeper_cm
                cm_score = min(deeper_cm["suspicious_matches"] / 25.0, 1.0)
                tampering_score = round(
                    (normalized_ela * 0.35) + (cm_score * 0.50) + (meta_score * 0.15),
                    4
                )

        # Risk Level
        if tampering_score <= 0.30:
            level = "Low"
            status = "pass"
        elif tampering_score <= 0.65:
            level = "Medium"
            status = "warning"
        else:
            level = "High"
            status = "fail"

        # Explanations and evidence
        evidence = []
        if cm_result["detected"]:
            evidence.append(f"Detected {cm_result['suspicious_matches']} duplicated visual feature matches (copy-move pattern).")
        if normalized_ela > 0.45:
            evidence.append(f"Elevated compression error level inconsistency ({raw_ela:.2f}).")
        evidence.extend(meta_result["evidence"])

        explanation = (
            "No significant tampering detected." if not evidence
            else " ".join(evidence)
        )

        return {
            "tampering_score": tampering_score,
            "level": level,
            "status": status,
            "explanation": explanation,
            "flagged": cm_result["detected"] or tampering_score > 0.60,
            "flaggedRegion": cm_result["flagged_region"] or (
                {"top": "35%", "left": "15%", "width": "50%", "height": "20%"} if tampering_score > 0.60 else None
            ),
            "ela": {
                "raw_score": round(raw_ela, 4),
                "score": round(normalized_ela, 4)
            },
            "copy_move": {
                "detected": cm_result["detected"],
                "suspicious_matches": cm_result["suspicious_matches"],
                "keypoints": cm_result["keypoints_count"]
            },
            "metadata": meta_result,
            "evidence": evidence,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
tampering_service = TamperingService()
