"""
Risk Scoring Engine
Calculates explainable, multi-factor risk scores combining signals from:
- Document field validation (20%)
- Tampering & digital forensics (40%)
- Face similarity matching (30% when selfie provided; redistributed if skipped)
- Completeness and OCR confidence (10%)
"""
from typing import Dict, Any, List, Optional


class RiskService:
    """Calculates weighted, explainable risk assessments across all verification modules."""

    def calculate(
        self,
        ocr_result: Dict[str, Any],
        validation_result: Dict[str, Any],
        tampering_result: Dict[str, Any],
        face_result: Optional[Dict[str, Any]] = None,
        passport_verification: Optional[Dict[str, Any]] = None,
        document_type: str = "passport"
    ) -> Dict[str, Any]:
        """
        Calculate composite risk score and factor explanations.
        Incorporates document validation, digital tampering, biometric verification,
        OCR completeness, and ML passport document-type classification.
        """
        # 1. Validation Risk (0-100)
        failed_checks = validation_result.get("failed_checks", [])
        total_checks = len(validation_result.get("checks", [])) or 5
        val_risk = round((len(failed_checks) / total_checks) * 100, 2)
        if len(failed_checks) == 0:
            val_reason = "All document field validation checks passed."
            val_tone = "pass"
        else:
            val_reason = f"Validation issues: {'; '.join(failed_checks)}"
            val_tone = "warning" if len(failed_checks) == 1 else "fail"

        # 2. Tampering Risk (0-100)
        tampering_score = tampering_result.get("tampering_score", 0.0)
        tamp_risk = round(tampering_score * 100, 2)
        if tamp_risk <= 30:
            tamp_reason = f"Low tampering risk ({tamp_risk:.0f}% manipulation probability)."
            tamp_tone = "pass"
        elif tamp_risk <= 65:
            tamp_reason = f"Moderate tampering risk ({tamp_risk:.0f}% manipulation probability). Manual review recommended."
            tamp_tone = "warning"
        else:
            tamp_reason = f"High tampering risk ({tamp_risk:.0f}% manipulation probability). Flagged visual inconsistencies."
            tamp_tone = "fail"

        # 3. Face Biometric Risk (0-100)
        face_status = face_result.get("status") if face_result else "SKIPPED"
        has_face = face_status == "completed" and face_result.get("similarity") is not None

        if has_face:
            sim = face_result["similarity"]
            threshold = face_result.get("threshold", 0.58)
            is_match = face_result.get("match")
            if is_match is None:
                is_match = (sim >= threshold)

            if is_match:
                # Confirmed biometric match
                face_risk = 0.0
                face_reason = f"Biometric verification confirmed ({sim * 100:.1f}% similarity exceeds calibration threshold {threshold * 100:.0f}%)."
                face_tone = "pass"
            else:
                # Genuine biometric mismatch / impostor risk
                deficit = max(0.0, threshold - sim)
                face_risk = round(min(100.0, 50.0 + (deficit / threshold) * 50.0), 1)
                face_reason = f"Biometric mismatch detected ({sim * 100:.1f}% similarity below threshold {threshold * 100:.0f}%). Possible impersonation."
                face_tone = "fail"
        elif face_status in ("no_face_document", "no_face_presented"):
            # Face not isolated from image - operational inspection required, not necessarily fraud
            face_risk = 15.0
            face_reason = f"Face detector could not reliably isolate portrait from image ({face_status}). Manual photo inspection required."
            face_tone = "warning"
        else:
            face_risk = 0.0
            face_reason = "Face verification skipped (no selfie provided). Does not penalize risk."
            face_tone = "pass"

        # 4. Completeness & OCR Confidence Risk (0-100)
        ocr_conf = ocr_result.get("ocr_confidence", 1.0)
        ocr_conf_risk = max(0.0, 100.0 - (ocr_conf * 100))
        fields = ocr_result.get("fields", {})
        missing_count = sum(1 for v in fields.values() if v is None)
        missing_risk = (missing_count / max(1, len(fields))) * 100
        comp_risk = round((ocr_conf_risk * 0.4) + (missing_risk * 0.6), 2)

        if comp_risk <= 20:
            comp_reason = f"High extraction confidence ({ocr_conf * 100:.0f}%) with complete identity fields."
            comp_tone = "pass"
        elif comp_risk <= 50:
            comp_reason = f"Moderate extraction confidence ({ocr_conf * 100:.0f}%). Some fields require manual inspection."
            comp_tone = "warning"
        else:
            comp_reason = f"Identity fields could not be reliably extracted ({ocr_conf * 100:.0f}%, {missing_count} missing fields) — manual document verification required."
            comp_tone = "warning"

        # 5. Passport Classification Signal (0-100)
        doc_risk = 0.0
        doc_reason = "Passport classification not evaluated."
        doc_tone = "pass"
        has_passport_verification = passport_verification is not None

        if has_passport_verification:
            is_passport = passport_verification.get("is_passport")
            conf = passport_verification.get("confidence", 0.0)
            status = passport_verification.get("status", "UNCERTAIN")

            if document_type.lower() == "passport":
                if not is_passport:
                    if status == "UNCERTAIN":
                        doc_risk = 15.0
                        doc_reason = "Passport classification inconclusive due to scan quality or service limits. Manual inspection advised."
                        doc_tone = "warning"
                    else:
                        doc_risk = 50.0
                        doc_reason = f"Document type classification mismatch: classified as {status} ({conf * 100:.0f}% passport confidence). Expected Passport."
                        doc_tone = "fail"
                else:
                    doc_risk = 0.0
                    doc_reason = f"Passport document layout confirmed by classification model ({conf * 100:.0f}% confidence)."
                    doc_tone = "pass"
            else:
                doc_risk = 0.0
                doc_reason = f"Passport classifier evaluated document (status: {status})."
                doc_tone = "pass"

        # Weighted combination
        if has_face:
            if has_passport_verification:
                w_val, w_tamp, w_face, w_comp, w_doc = 0.20, 0.40, 0.25, 0.05, 0.10
            else:
                w_val, w_tamp, w_face, w_comp, w_doc = 0.20, 0.40, 0.30, 0.10, 0.0
        else:
            # Rebalance weights when selfie is absent
            if has_passport_verification:
                w_val, w_tamp, w_face, w_comp, w_doc = 0.25, 0.50, 0.0, 0.15, 0.10
            else:
                w_val, w_tamp, w_face, w_comp, w_doc = 0.30, 0.55, 0.0, 0.15, 0.0

        final_score = round(
            (val_risk * w_val) +
            (tamp_risk * w_tamp) +
            (face_risk * w_face) +
            (comp_risk * w_comp) +
            (doc_risk * w_doc),
            1
        )
        # Critical fraud flags enforcement:
        # Biometric mismatch, confirmed tampering, or document type mismatch must never pass as LOW risk
        if tampering_result.get("flagged") and has_face and not is_match:
            # Compound fraud: both photo tampering and biometric impostor detected
            final_score = max(final_score, 65.0)
        elif has_face and not is_match:
            final_score = max(final_score, 45.0)
        elif tampering_result.get("flagged"):
            final_score = max(final_score, 50.0)
        elif has_passport_verification and doc_tone == "fail":
            final_score = max(final_score, 45.0)

        final_score = max(0.0, min(100.0, final_score))

        # Risk level
        if final_score <= 25.0:
            level = "LOW"
            overall_status = "pass"
        elif final_score <= 60.0:
            level = "MEDIUM"
            overall_status = "warning"
        else:
            level = "HIGH"
            overall_status = "fail"

        reasons = [
            {"text": val_reason, "tone": val_tone, "module": "validation"},
            {"text": tamp_reason, "tone": tamp_tone, "module": "tampering"},
            {"text": face_reason, "tone": face_tone, "module": "face"},
            {"text": comp_reason, "tone": comp_tone, "module": "ocr"}
        ]
        if has_passport_verification:
            reasons.append({"text": doc_reason, "tone": doc_tone, "module": "passport_verification"})

        factors = [
            {"factor": "Document validation", "contribution": round(val_risk * w_val, 1), "explanation": val_reason},
            {"factor": "Tampering analysis", "contribution": round(tamp_risk * w_tamp, 1), "explanation": tamp_reason},
            {"factor": "Face verification", "contribution": round(face_risk * w_face, 1), "explanation": face_reason},
            {"factor": "Completeness & OCR", "contribution": round(comp_risk * w_comp, 1), "explanation": comp_reason}
        ]
        if has_passport_verification:
            factors.append({"factor": "Passport classification", "contribution": round(doc_risk * w_doc, 1), "explanation": doc_reason})

        return {
            "score": final_score,
            "risk_score": final_score,
            "level": level,
            "risk_level": level,
            "status": overall_status,
            "reasons": reasons,
            "factors": factors
        }


# Singleton instance
risk_service = RiskService()
