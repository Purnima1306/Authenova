from fastapi import APIRouter, HTTPException
from app.services.orchestrator.pipeline import pipeline

router = APIRouter()


@router.get("/screening-report/{document_id}")
async def get_screening_report(document_id: str):
    """
    Get the complete screening report for a document.
    Aggregates real results from all verification modules into a single report.
    """
    screening = pipeline.get_screening(document_id)

    if not screening:
        raise HTTPException(
            status_code=404,
            detail=f"Screening report with document_id '{document_id}' not found."
        )

    return {
        "success": True,
        "data": screening["report"],
        "errors": []
    }
