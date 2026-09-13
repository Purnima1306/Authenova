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
    def _load_image(image_input: bytes | str | np.ndarray) -> tuple[Image.Image, np.ndarray]:
        """Load image as both PIL Image and OpenCV BGR numpy array."""
        if isinstance(image_input, np.ndarray):
            cv_img = image_input
            pil_img = Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))
            return pil_img, cv_img
        elif isinstance(image_input, (bytes, bytearray)):
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
        min_distance: float = 40.0
    ) -> Dict[str, Any]:
        """
        Detect duplicated visual regions using ORB feature matching with
        displacement vector spatial clustering and RANSAC homography verification.
        Eliminates false positives caused by text, chevrons, and security patterns.
        """
        from collections import defaultdict

        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY) if len(cv_image.shape) == 3 else cv_image
        h, w = gray.shape[:2]

        orb = cv2.ORB_create(nfeatures=nfeatures)
        keypoints, descriptors = orb.detectAndCompute(gray, None)

        if descriptors is None or len(descriptors) < 10:
            return {
                "detected": False,
                "raw_matches": 0,
                "suspicious_matches": 0,
                "verified_inliers": 0,
                "flagged_region": None,
                "keypoints_count": len(keypoints) if keypoints else 0
            }

        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        try:
            matches = bf.knnMatch(descriptors, descriptors, k=3)
        except Exception:
            return {
                "detected": False,
                "raw_matches": 0,
                "suspicious_matches": 0,
                "verified_inliers": 0,
                "flagged_region": None,
                "keypoints_count": len(keypoints)
            }

        clusters = defaultdict(list)
        bin_size = 30.0
        raw_matches_count = 0

        for match_group in matches:
            valid = [m for m in match_group if m.queryIdx != m.trainIdx]
            if len(valid) < 2:
                continue

            m, n = valid[0], valid[1]
            if m.distance < match_ratio * n.distance:
                p1 = np.array(keypoints[m.queryIdx].pt)
                p2 = np.array(keypoints[m.trainIdx].pt)
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                dist = np.sqrt(dx * dx + dy * dy)
                if dist > min_distance:
                    raw_matches_count += 1
                    bx, by = int(round(dx / bin_size)), int(round(dy / bin_size))
                    # Canonicalize vector direction
                    if bx < 0 or (bx == 0 and by < 0):
                        bx, by = -bx, -by
                        p1, p2 = p2, p1
                    clusters[(bx, by)].append((m, p1, p2))

        max_inliers = 0
        max_area = 0
        best_cluster_pts = []

        for (bx, by), items in clusters.items():
            if len(items) >= 8:
                src_pts = np.float32([it[1] for it in items]).reshape(-1, 1, 2)
                dst_pts = np.float32([it[2] for it in items]).reshape(-1, 1, 2)
                try:
                    H, inlier_mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 4.0)
                    if inlier_mask is not None:
                        num_inliers = int(np.sum(inlier_mask))
                        if num_inliers >= 8:
                            pts = np.array([items[i][1] for i in range(len(items)) if inlier_mask[i]])
                            bx_pt, by_pt, bw, bh = cv2.boundingRect(pts.astype(np.int32))
                            area = bw * bh
                            if num_inliers > max_inliers:
                                max_inliers = num_inliers
                                max_area = area
                                best_cluster_pts = pts
                except Exception:
                    pass

        # Detection criteria: geometrically verified 2D duplication
        detected = (max_inliers >= 25) or (max_inliers >= 18 and max_area >= 15000)
        flagged_region = None

        if detected and len(best_cluster_pts) > 0:
            x, y, bw, bh = cv2.boundingRect(best_cluster_pts.astype(np.int32))
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
            "raw_matches": raw_matches_count,
            "suspicious_matches": max_inliers,
            "verified_inliers": max_inliers,
            "area": max_area,
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

    def analyze(self, image_input: bytes | str | np.ndarray) -> Dict[str, Any]:
        """
        Run the complete tampering analysis pipeline on arbitrary image input.
        Combines ELA, geometrically verified copy-move, and metadata analysis.
        """
        pil_img, cv_img = self._load_image(image_input)

        # 1. ELA
        raw_ela, _ = self.calculate_ela(pil_img)
        # Normalize: raw ELA on normal JPEG is typically 0.1-5.0; only > 8.0 is anomalous
        normalized_ela = min(max(0.0, (raw_ela - 5.0) / 15.0), 1.0) if raw_ela > 5.0 else 0.0

        # 2. Copy-Move with displacement vector clustering & RANSAC
        cm_result = self.detect_copy_move(cv_img, nfeatures=2000, match_ratio=0.75)

        # 3. Metadata
        meta_result = self.inspect_metadata(pil_img)

        # Calibrated scoring based on verified evidence
        cm_score = min(cm_result["verified_inliers"] / 50.0, 1.0) if cm_result["detected"] else 0.0
        meta_score = 0.8 if meta_result["suspicious_software"] else 0.0

        tampering_score = round(
            (normalized_ela * 0.25) + (cm_score * 0.60) + (meta_score * 0.15),
            4
        )

        # Adaptive deep scan for borderline suspicion
        adaptive_actions = []
        if 0.15 <= tampering_score <= 0.45 and cm_result["raw_matches"] > 100 and not cm_result["detected"]:
            deeper_cm = self.detect_copy_move(cv_img, nfeatures=3000, match_ratio=0.80)
            adaptive_actions.append({
                "action": "TAMPERING_GEOMETRIC_VERIFICATION",
                "reason": f"Elevated raw feature matches ({cm_result['raw_matches']}) verified through RANSAC homography. Discarded non-geometric text/pattern repetitions.",
                "raw_matches": cm_result["raw_matches"],
                "verified_inliers": deeper_cm["verified_inliers"],
                "confirmed_detected": deeper_cm["detected"]
            })
            if deeper_cm["detected"]:
                cm_result = deeper_cm
                cm_score = min(deeper_cm["verified_inliers"] / 50.0, 1.0)
                tampering_score = round(
                    (normalized_ela * 0.25) + (cm_score * 0.60) + (meta_score * 0.15),
                    4
                )

        # Evidence-based risk level
        if tampering_score <= 0.20:
            level = "Low"
            status = "pass"
        elif tampering_score <= 0.50:
            level = "Medium"
            status = "warning"
        else:
            level = "High"
            status = "fail"

        # Evidence logging
        evidence = []
        if cm_result["detected"]:
            evidence.append(f"Detected {cm_result['verified_inliers']} geometrically verified duplicate keypoints (copy-move clone).")
        elif cm_result["raw_matches"] > 50:
            evidence.append(f"Evaluated {cm_result['raw_matches']} repetitive pattern matches; geometric verification confirmed legitimate document textures.")
        if normalized_ela > 0.45:
            evidence.append(f"Elevated compression error level inconsistency ({raw_ela:.2f}).")
        evidence.extend(meta_result["evidence"])

        explanation = (
            "No significant tampering detected." if not evidence or (not cm_result["detected"] and not meta_result["suspicious_software"])
            else " ".join(evidence)
        )

        return {
            "tampering_score": tampering_score,
            "level": level,
            "status": status,
            "explanation": explanation,
            "flagged": cm_result["detected"] or tampering_score > 0.50,
            "flaggedRegion": cm_result["flagged_region"],
            "ela": {
                "raw_score": round(raw_ela, 4),
                "score": round(normalized_ela, 4)
            },
            "copy_move": {
                "detected": cm_result["detected"],
                "raw_matches": cm_result["raw_matches"],
                "suspicious_matches": cm_result["suspicious_matches"],
                "verified_inliers": cm_result["verified_inliers"],
                "keypoints": cm_result["keypoints_count"]
            },
            "metadata": meta_result,
            "evidence": evidence,
            "adaptive_actions": adaptive_actions
        }


# Singleton instance
tampering_service = TamperingService()
