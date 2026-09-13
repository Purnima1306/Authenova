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
        face_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate composite risk score and factor explanations.
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

        # 3. Face Risk (0-100)
        face_status = face_result.get("status") if face_result else "SKIPPED"
        has_face = face_status == "completed" and face_result.get("similarity") is not None

        if has_face:
            sim = face_result["similarity"]
            face_risk = round(max(0.0, 100.0 - (sim * 100)), 2)
            if face_risk <= 30:
                face_reason = f"High facial similarity ({sim * 100:.0f}% match with presented selfie)."
                face_tone = "pass"
            elif face_risk <= 50:
                face_reason = f"Borderline facial similarity ({sim * 100:.0f}% match). Ambiguous match requires verification."
                face_tone = "warning"
            else:
                face_reason = f"Low facial similarity ({sim * 100:.0f}% match). Possible impersonation."
                face_tone = "fail"
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
        comp_risk = round((ocr_conf_risk * 0.5) + (missing_risk * 0.5), 2)

        if comp_risk <= 25:
            comp_reason = f"High OCR confidence ({ocr_conf * 100:.0f}%) and complete document fields."
            comp_tone = "pass"
        elif comp_risk <= 60:
            comp_reason = f"Moderate OCR confidence ({ocr_conf * 100:.0f}%) or partial missing fields."
            comp_tone = "warning"
        else:
            comp_reason = f"Low OCR extraction confidence ({ocr_conf * 100:.0f}%) with {missing_count} missing fields."
            comp_tone = "fail"

        # Weighted combination
        if has_face:
            w_val, w_tamp, w_face, w_comp = 0.20, 0.40, 0.30, 0.10
        else:
            # Rebalance weights when selfie is absent
            w_val, w_tamp, w_face, w_comp = 0.30, 0.55, 0.0, 0.15

        final_score = round(
            (val_risk * w_val) +
            (tamp_risk * w_tamp) +
            (face_risk * w_face) +
            (comp_risk * w_comp),
            1
        )
        final_score = max(0.0, min(100.0, final_score))

        # Risk level
        if final_score <= 30.0:
            level = "LOW"
            overall_status = "pass"
        elif final_score <= 70.0:
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

        factors = [
            {"factor": "Document validation", "contribution": round(val_risk * w_val, 1), "explanation": val_reason},
            {"factor": "Tampering analysis", "contribution": round(tamp_risk * w_tamp, 1), "explanation": tamp_reason},
            {"factor": "Face verification", "contribution": round(face_risk * w_face, 1), "explanation": face_reason},
            {"factor": "Completeness & OCR", "contribution": round(comp_risk * w_comp, 1), "explanation": comp_reason}
        ]

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
