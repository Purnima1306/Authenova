"""
Screening API Routes
Endpoints for executing the complete identity and document screening pipeline,
retrieving screening records, and recording human officer decisions.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.orchestrator.pipeline import pipeline

router = APIRouter()


class ScreeningStatusResponse(BaseModel):
    success: bool
    document_id: str
    status: str
    message: str
    report: Optional[Dict[str, Any]] = None


class OfficerDecisionRequest(BaseModel):
    action: str  # "Approved" | "Flagged for Review" | "Rejected"
    comment: Optional[str] = ""


class OfficerDecisionResponse(BaseModel):
    success: bool
    message: str
    document_id: str
    decision: Dict[str, Any]


@router.post("/screen", response_model=ScreeningStatusResponse)
async def start_screening(
    file: UploadFile = File(...),
    document_type: str = Form("passport"),
    verification_image: Optional[UploadFile] = File(None)
):
    """
    Start a complete document screening process.
    Executes real OCR, validation, tampering analysis, face matching, RAG explanation,
    and weighted risk assessment.
    """
    try:
        file_content = await file.read()
        selfie_content = None
        selfie_filename = None

        if verification_image:
            selfie_content = await verification_image.read()
            selfie_filename = verification_image.filename

        result = await pipeline.run_screening(
            document_content=file_content,
            document_filename=file.filename,
            document_type=document_type,
            selfie_content=selfie_content,
            selfie_filename=selfie_filename
        )

        return ScreeningStatusResponse(
            success=True,
            document_id=result["document_id"],
            status="completed",
            message="Screening completed successfully",
            report=result["report"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening pipeline error: {str(e)}")


@router.get("/results/{document_id}")
async def get_screening_results(document_id: str):
    """
    Get the results of a completed screening.
    Returns the full screening report with all module results.
    """
    screening = pipeline.get_screening(document_id)

    if not screening:
        raise HTTPException(
            status_code=404,
            detail=f"Screening with document_id {document_id} not found"
        )

    return {
        "success": True,
        "data": screening["report"],
        "errors": []
    }


@router.post("/decision/{document_id}", response_model=OfficerDecisionResponse)
async def record_officer_decision(document_id: str, request: OfficerDecisionRequest):
    """
    Record an officer's final manual decision (Approve / Flag for Review / Reject).
    """
    screening = pipeline.get_screening(document_id)
    if not screening:
        raise HTTPException(status_code=404, detail=f"Screening with document_id {document_id} not found")

    success = pipeline.record_decision(document_id, request.action, request.comment)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to persist officer decision")

    return OfficerDecisionResponse(
        success=True,
        message=f"Decision '{request.action}' recorded successfully.",
        document_id=document_id,
        decision={
            "action": request.action,
            "comment": request.comment
        }
    )
