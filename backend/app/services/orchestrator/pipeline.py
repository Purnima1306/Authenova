"""
Screening Orchestrator Pipeline
Coordinates all AI and computer vision verification services:
Storage -> OCR -> Validation -> Tampering -> Face Verification -> RAG -> Risk -> DB Persistence.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.storage.files import file_storage
from app.services.ocr.engine import ocr_service
from app.services.passport_verification_service import passport_verification_service
from app.services.validation.service import validation_service
from app.services.tampering.service import tampering_service
from app.services.face.service import face_service
from app.services.rag.service import rag_service
from app.services.risk.service import risk_service
from app.database.session import SessionLocal
from app.models.screening import ScreeningRecord

logger = logging.getLogger("authenova.pipeline")


class ScreeningPipeline:
    """End-to-end orchestration of document analysis and risk assessment."""

    def __init__(self):
        self.screenings: Dict[str, Dict[str, Any]] = {}

    async def run_screening(
        self,
        document_content: bytes,
        document_filename: str,
        document_type: str = "passport",
        selfie_content: Optional[bytes] = None,
        selfie_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the end-to-end verification pipeline.
        """
        logger.info("Starting screening for %s (type: %s)", document_filename, document_type)

        # 1. Storage & Validation
        doc_id, doc_path, selfie_path = file_storage.save_upload(
            document_content=document_content,
            document_filename=document_filename,
            selfie_content=selfie_content,
            selfie_filename=selfie_filename
        )

        orchestration_logs = []

        # 2. Stage 1: OCR Extraction
        logger.info("[%s] Running OCR extraction...", doc_id)
        ocr_result = ocr_service.extract(doc_path)
        if ocr_result.get("adaptive_actions"):
            orchestration_logs.extend(ocr_result["adaptive_actions"])

        # Forward canonical orientation-normalized image to downstream vision models
        canonical_img = ocr_result.get("canonical_image")
        proc_doc = canonical_img if canonical_img is not None else doc_path

        # Stage 1.5: Document-Level Passport Classification (ML Model)
        logger.info("[%s] Running PassportVerificationModel...", doc_id)
        passport_verification_res = passport_verification_service.classify_document(proc_doc)
        if passport_verification_res.get("is_passport"):
            orchestration_logs.append({
                "stage": "passport_verification",
                "action": "DOCUMENT_TYPE_CONFIRMED",
                "reason": f"PassportVerificationModel confirmed passport structure ({passport_verification_res.get('confidence', 0.0) * 100:.0f}% confidence)."
            })
        elif passport_verification_res.get("status") == "UNCERTAIN":
            orchestration_logs.append({
                "stage": "passport_verification",
                "action": "DOCUMENT_TYPE_UNCERTAIN",
                "reason": "Passport classification inconclusive. Manual officer inspection required."
            })
        else:
            orchestration_logs.append({
                "stage": "passport_verification",
                "action": "DOCUMENT_TYPE_MISMATCH",
                "reason": f"Input document classified as {passport_verification_res.get('status')} ({passport_verification_res.get('confidence', 0.0) * 100:.0f}% passport confidence)."
            })

        # 3. Stage 2: Document Field Validation
        logger.info("[%s] Running document validation...", doc_id)
        validation_result = validation_service.validate(
            fields=ocr_result["fields"],
            document_type=document_type
        )

        # 4. Stage 3: Tampering Detection
        logger.info("[%s] Running tampering detection...", doc_id)
        tampering_result = tampering_service.analyze(proc_doc)
        if tampering_result.get("adaptive_actions"):
            orchestration_logs.extend(tampering_result["adaptive_actions"])

        # 5. Stage 4: Face Verification
        logger.info("[%s] Running face verification...", doc_id)
        face_result = face_service.verify(
            document_image=proc_doc,
            selfie_image=selfie_path if selfie_path else None
        )
        if face_result.get("adaptive_actions"):
            orchestration_logs.extend(face_result["adaptive_actions"])

        # 6. Stage 5: RAG Grounded Explanations with LLM Prompt Engineering
        logger.info("[%s] Retrieving grounded RAG explanations with prompt engineering...", doc_id)
        flagged_issues = list(validation_result.get("failed_checks", []))
        if passport_verification_res.get("is_passport") is False and document_type.lower() == "passport":
            flagged_issues.append("Document visual layout mismatch: expected passport format.")
        if tampering_result.get("flagged"):
            flagged_issues.append("High tampering risk (probability of digital editing).")
        if face_result.get("status") == "completed" and face_result.get("match") is False:
            flagged_issues.append("Low face similarity score between document and selfie.")

        doc_context = {
            "document_id": doc_id,
            "document_type": document_type,
            "ocr_confidence": int(ocr_result.get("ocr_confidence", 0.0) * 100),
            "tampering_flagged": tampering_result.get("flagged", False),
            "tampering_score": tampering_result.get("tampering_score", 0.0),
            "face_match": face_result.get("match"),
            "face_status": face_result.get("status", "skipped"),
        }
        rag_explanations = await rag_service.explain_all_flags_async(flagged_issues, context=doc_context)

        # 7. Stage 6: Weighted Risk Scoring
        logger.info("[%s] Calculating composite risk...", doc_id)
        risk_result = risk_service.calculate(
            ocr_result=ocr_result,
            validation_result=validation_result,
            tampering_result=tampering_result,
            face_result=face_result,
            passport_verification=passport_verification_res,
            document_type=document_type
        )

        # 8. Compile Unified Frontend-Compatible Screening Report
        overall_conf_pct = int(ocr_result["ocr_confidence"] * 100)
        fields = ocr_result["fields"]
        sources = ocr_result.get("field_sources", {})

        # Format validation items for frontend checklist
        frontend_validation = []
        for chk in validation_result["checks"]:
            frontend_validation.append({
                "field": chk["label"],
                "status": chk["status"].lower(),
                "explanation": chk["message"]
            })

        # Format OCR fields with confidence bars and extraction source
        frontend_ocr = {
            "name": {
                "value": fields.get("name") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("name", 0) * 100) if fields.get("name") else 0,
                "source": sources.get("name", "OCR")
            },
            "idNumber": {
                "value": fields.get("passport_number") or fields.get("document_number") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("passport_number", 0) * 100) if fields.get("passport_number") else 0,
                "source": sources.get("passport_number", "OCR")
            },
            "dateOfBirth": {
                "value": fields.get("date_of_birth") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("date_of_birth", 0) * 100) if fields.get("date_of_birth") else 0,
                "source": sources.get("date_of_birth", "OCR")
            },
            "nationality": {
                "value": fields.get("nationality") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("nationality", 0) * 100) if fields.get("nationality") else 0,
                "source": sources.get("nationality", "OCR")
            },
            "expiryDate": {
                "value": fields.get("expiry_date") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("expiry_date", 0) * 100) if fields.get("expiry_date") else 0,
                "source": sources.get("expiry_date", "OCR")
            }
        }

        # Face verification block
        face_match = face_result.get("match")
        sim_val = face_result.get("similarity")
        frontend_face = {
            "similarity": int(sim_val * 100) if sim_val is not None else 0,
            "threshold": int(face_result.get("threshold", 0.58) * 100),
            "match": face_match if face_match is not None else False,
            "status": face_result.get("status", "SKIPPED"),
            "verification_status": face_result.get("verification_status", "not_performed"),
            "model": face_result.get("model", "FaceNet"),
            "document_face_detected": face_result.get("document_face_detected", False),
            "presented_face_detected": face_result.get("presented_face_detected", False),
            "document_face_bbox": face_result.get("document_face_bbox")
        }

        report = {
            "document_id": doc_id,
            "document_type": document_type,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "extracted_fields": fields,
            "ocr_confidence": ocr_result["ocr_confidence"],
            "ocr": frontend_ocr,
            "mrz": ocr_result.get("mrz_data"),
            "passport_verification": {
                "is_passport": passport_verification_res["is_passport"],
                "confidence": passport_verification_res["confidence"],
                "confidence_pct": int(round(passport_verification_res["confidence"] * 100)),
                "status": passport_verification_res["status"],
                "model": passport_verification_res.get("model", "passport_verifier"),
                "model_version": passport_verification_res.get("model_version", "1.0.0"),
                "features": passport_verification_res.get("features", 33)
            },
            "validation": frontend_validation,
            "tampering": {
                "level": tampering_result["level"],
                "score": int(tampering_result["tampering_score"] * 100),
                "tampering_score": tampering_result["tampering_score"],
                "explanation": tampering_result["explanation"],
                "flagged": tampering_result["flagged"],
                "flaggedRegion": tampering_result["flaggedRegion"],
                "raw_matches": tampering_result.get("copy_move", {}).get("raw_matches", 0),
                "verified_inliers": tampering_result.get("copy_move", {}).get("verified_inliers", 0),
                "indicators": [k for k, v in tampering_result.get("copy_move", {}).items() if v]
            },
            "face_verification": frontend_face,
            "faceVerification": frontend_face,
            "risk": {
                "score": int(risk_result["score"]),
                "level": risk_result["level"],
                "reasons": risk_result["reasons"]
            },
            "risk_assessment": {
                "risk_score": risk_result["score"],
                "risk_level": risk_result["level"],
                "factors": risk_result["factors"]
            },
            "rag_explanations": rag_explanations,
            "orchestration_logs": orchestration_logs,
            "diagnostics": {
                "ocr_sources": sources,
                "mrz_validity": {
                    "passport_number": ocr_result.get("mrz_data", {}).get("passport_number_valid", False) if ocr_result.get("mrz_data") else False,
                    "date_of_birth": ocr_result.get("mrz_data", {}).get("date_of_birth_valid", False) if ocr_result.get("mrz_data") else False,
                    "expiry_date": ocr_result.get("mrz_data", {}).get("expiry_date_valid", False) if ocr_result.get("mrz_data") else False,
                },
                "passport_verification": {
                    "is_passport": passport_verification_res["is_passport"],
                    "confidence": passport_verification_res["confidence"],
                    "status": passport_verification_res["status"],
                    "features": passport_verification_res.get("features", 33),
                    "model": passport_verification_res.get("model", "passport_verifier")
                },
                "face_model": face_result.get("model", "FaceNet"),
                "tampering_inliers": tampering_result.get("copy_move", {}).get("verified_inliers", 0)
            },
            "decision_note": "Human officer review required"
        }

        # 9. Persist to Database (exclude non-serializable ndarrays)
        try:
            db = SessionLocal()
            ocr_data_clean = {k: v for k, v in ocr_result.items() if k != "canonical_image"}
            record = ScreeningRecord(
                document_id=doc_id,
                filename=document_filename,
                document_type=document_type,
                status="completed",
                ocr_data=ocr_data_clean,
                validation_data=validation_result,
                tampering_data=tampering_result,
                face_data=face_result,
                risk_data=risk_result,
                rag_data=rag_explanations,
                orchestration_logs=orchestration_logs,
                full_report=report,
                created_at=datetime.utcnow()
            )
            db.add(record)
            db.commit()
            db.close()
            logger.info("[%s] Successfully persisted screening to database.", doc_id)
        except Exception as e:
            logger.error("[%s] Failed to persist to database: %s", doc_id, str(e))

        # Memory cache
        self.screenings[doc_id] = report

        return {
            "document_id": doc_id,
            "status": "completed",
            "report": report
        }

    def get_screening(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a screening result by document_id from database or memory."""
        if document_id in self.screenings:
            return {"report": self.screenings[document_id]}

        # Check database
        try:
            db = SessionLocal()
            rec = db.query(ScreeningRecord).filter(ScreeningRecord.document_id == document_id).first()
            if rec:
                report = rec.full_report
                if rec.officer_decision:
                    report["officer_decision"] = rec.officer_decision
                db.close()
                self.screenings[document_id] = report
                return {"report": report}
            db.close()
        except Exception as e:
            logger.error("Error fetching record %s: %s", document_id, str(e))

        return None

    def record_decision(self, document_id: str, action: str, comment: str = "") -> bool:
        """Record manual decision by verification officer."""
        decision_data = {
            "action": action,
            "comment": comment,
            "recorded_at": datetime.utcnow().isoformat()
        }

        if document_id in self.screenings:
            self.screenings[document_id]["officer_decision"] = decision_data

        try:
            db = SessionLocal()
            rec = db.query(ScreeningRecord).filter(ScreeningRecord.document_id == document_id).first()
            if rec:
                rec.officer_decision = decision_data
                report = dict(rec.full_report)
                report["officer_decision"] = decision_data
                rec.full_report = report
                db.commit()
                db.close()
                return True
            db.close()
        except Exception as e:
            logger.error("Failed to record decision for %s: %s", document_id, str(e))

        return False


# Global pipeline instance
pipeline = ScreeningPipeline()
