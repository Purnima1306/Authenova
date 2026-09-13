from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.validation.service import validation_service

router = APIRouter()


class ValidationRequest(BaseModel):
    document_id: str
    document_type: str = "passport"
    extracted_fields: Dict[str, Any]


@router.post("/validate-document")
async def validate_document(request: ValidationRequest):
    """
    Validate the extracted document fields for format correctness,
    logical consistency, and completeness using real rule engine.
    """
    result = validation_service.validate(request.extracted_fields, request.document_type)
    return {
        "success": True,
        "data": {
            "document_id": request.document_id,
            "is_valid_format": result["is_valid_format"],
            "validation_score": result["validation_score"],
            "checks": result["checks"],
            "validation_warnings": result["validation_warnings"],
            "failed_checks": result["failed_checks"]
        },
        "errors": []
    }
