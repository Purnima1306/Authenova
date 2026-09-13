from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.face.service import face_service

router = APIRouter()


class FaceVerificationRequest(BaseModel):
    document_id: str
    document_image_path: str
    verification_image_path: Optional[str] = None


@router.post("/verify-face")
async def verify_face(request: FaceVerificationRequest):
    """
    Compare the face photo in the document with a presented/live verification photo
    using real FaceNet / OpenCV feature matching and cosine similarity.
    """
    try:
        result = face_service.verify(
            document_image=request.document_image_path,
            selfie_image=request.verification_image_path
        )
        return {
            "success": True,
            "data": {
                "document_id": request.document_id,
                "status": result["status"],
                "face_detected_document": result["face_detected_document"],
                "face_detected_verification": result["face_detected_verification"],
                "similarity_score": result.get("similarity"),
                "similarity": result.get("similarity"),
                "similarity_percent": result.get("similarity_percent"),
                "threshold": result["threshold"],
                "match": result["match"],
                "verification_status": result["verification_status"]
            },
            "errors": []
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Face verification failed: {str(e)}")
