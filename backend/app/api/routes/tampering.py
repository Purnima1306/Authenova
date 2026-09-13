from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from app.services.tampering.service import tampering_service

router = APIRouter()


class TamperingRequest(BaseModel):
    document_id: str
    image_path: str


@router.post("/detect-tampering")
async def detect_tampering(request: TamperingRequest):
    """
    Analyze the document image for signs of digital tampering or manipulation
    using real ELA, copy-move detection, and metadata analysis.
    """
    try:
        result = tampering_service.analyze(request.image_path)
        return {
            "success": True,
            "data": {
                "document_id": request.document_id,
                "tampering_score": result["tampering_score"],
                "level": result["level"],
                "indicators": result.get("indicators", []),
                "evidence": result["evidence"],
                "flagged": result["flagged"],
                "flaggedRegion": result["flaggedRegion"],
                "ela": result["ela"],
                "copy_move": result["copy_move"],
                "metadata": result["metadata"]
            },
            "errors": []
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tampering analysis failed: {str(e)}")
