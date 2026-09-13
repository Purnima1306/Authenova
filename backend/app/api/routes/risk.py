from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.risk.service import risk_service

router = APIRouter()


class RiskRequest(BaseModel):
    document_id: str
    ocr_confidence: float = 1.0
    fields: Optional[Dict[str, Any]] = None
    validation_result: Dict[str, Any]
    tampering_result: Dict[str, Any]
    face_result: Optional[Dict[str, Any]] = None


@router.post("/calculate-risk")
async def calculate_risk(request: RiskRequest):
    """
    Calculate an explainable risk score by combining real signals from
    OCR, validation, tampering, and face verification modules.
    """
    ocr_dict = {
        "ocr_confidence": request.ocr_confidence,
        "fields": request.fields or {}
    }
    result = risk_service.calculate(
        ocr_result=ocr_dict,
        validation_result=request.validation_result,
        tampering_result=request.tampering_result,
        face_result=request.face_result
    )
    return {
        "success": True,
        "data": {
            "document_id": request.document_id,
            "risk_score": result["score"],
            "risk_level": result["level"],
            "status": result["status"],
            "reasons": result["reasons"],
            "factors": result["factors"]
        },
        "errors": []
    }
