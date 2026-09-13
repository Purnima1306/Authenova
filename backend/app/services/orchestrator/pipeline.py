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

        # 3. Stage 2: Document Field Validation
        logger.info("[%s] Running document validation...", doc_id)
        validation_result = validation_service.validate(
            fields=ocr_result["fields"],
            document_type=document_type
        )

        # 4. Stage 3: Tampering Detection
        logger.info("[%s] Running tampering detection...", doc_id)
        tampering_result = tampering_service.analyze(doc_path)
        if tampering_result.get("adaptive_actions"):
            orchestration_logs.extend(tampering_result["adaptive_actions"])

        # 5. Stage 4: Face Verification
        logger.info("[%s] Running face verification...", doc_id)
        face_result = face_service.verify(
            document_image=doc_path,
            selfie_image=selfie_path if selfie_path else None
        )
        if face_result.get("adaptive_actions"):
            orchestration_logs.extend(face_result["adaptive_actions"])

        # 6. Stage 5: RAG Grounded Explanations
        logger.info("[%s] Retrieving grounded RAG explanations...", doc_id)
        flagged_issues = list(validation_result.get("failed_checks", []))
        if tampering_result.get("flagged"):
            flagged_issues.append("High tampering risk (probability of digital editing).")
        if face_result.get("status") == "completed" and face_result.get("match") is False:
            flagged_issues.append("Low face similarity score between document and selfie.")

        rag_explanations = rag_service.explain_all_flags(flagged_issues)

        # 7. Stage 6: Weighted Risk Scoring
        logger.info("[%s] Calculating composite risk...", doc_id)
        risk_result = risk_service.calculate(
            ocr_result=ocr_result,
            validation_result=validation_result,
            tampering_result=tampering_result,
            face_result=face_result
        )

        # 8. Compile Unified Frontend-Compatible Screening Report
        overall_conf_pct = int(ocr_result["ocr_confidence"] * 100)
        fields = ocr_result["fields"]

        # Format validation items for frontend checklist
        frontend_validation = []
        for chk in validation_result["checks"]:
            frontend_validation.append({
                "field": chk["label"],
                "status": chk["status"].lower(),
                "explanation": chk["message"]
            })

        # Format OCR fields with confidence bars
        frontend_ocr = {
            "name": {
                "value": fields.get("name") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("name", 0) * 100) if fields.get("name") else 0
            },
            "idNumber": {
                "value": fields.get("passport_number") or fields.get("document_number") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("passport_number", 0) * 100) if fields.get("passport_number") else 0
            },
            "dateOfBirth": {
                "value": fields.get("date_of_birth") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("date_of_birth", 0) * 100) if fields.get("date_of_birth") else 0
            },
            "nationality": {
                "value": fields.get("nationality") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("nationality", 0) * 100) if fields.get("nationality") else 0
            },
            "expiryDate": {
                "value": fields.get("expiry_date") or "Not Detected",
                "confidence": int(ocr_result["confidence"].get("expiry_date", 0) * 100) if fields.get("expiry_date") else 0
            }
        }

        # Face verification block
        face_match = face_result.get("match")
        sim_val = face_result.get("similarity")
        frontend_face = {
            "similarity": int(sim_val * 100) if sim_val is not None else 0,
            "threshold": int(face_result.get("threshold", 0.75) * 100),
            "match": face_match if face_match is not None else False,
            "status": face_result.get("status", "SKIPPED"),
            "verification_status": face_result.get("verification_status", "not_performed")
        }

        report = {
            "document_id": doc_id,
            "document_type": document_type,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "extracted_fields": fields,
            "ocr_confidence": ocr_result["ocr_confidence"],
            "ocr": frontend_ocr,
            "validation": frontend_validation,
            "tampering": {
                "level": tampering_result["level"],
                "score": int(tampering_result["tampering_score"] * 100),
                "tampering_score": tampering_result["tampering_score"],
                "explanation": tampering_result["explanation"],
                "flagged": tampering_result["flagged"],
                "flaggedRegion": tampering_result["flaggedRegion"],
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
            "decision_note": "Human officer review required"
        }

        # 9. Persist to Database
        try:
            db = SessionLocal()
            record = ScreeningRecord(
                document_id=doc_id,
                filename=document_filename,
                document_type=document_type,
                status="completed",
                ocr_data=ocr_result,
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
