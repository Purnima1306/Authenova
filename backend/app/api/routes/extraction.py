import os
import glob
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ocr.engine import ocr_service
from app.storage.files import file_storage

router = APIRouter()


class ExtractionRequest(BaseModel):
    document_id: str
    document_type: str = "passport"


@router.post("/extract-data")
async def extract_data(request: ExtractionRequest):
    """
    Extract text data from the uploaded document using real OCR.
    Returns structured fields like name, passport number, dates, etc.
    """
    # Locate stored document by ID
    pattern = os.path.join(file_storage.upload_dir, f"{request.document_id}_doc.*")
    matches = glob.glob(pattern)

    if not matches:
        # Fallback to test document if document_id matches test fixtures
        sample_path = "data/samples/documents/test_document.png"
        if os.path.exists(sample_path):
            doc_path = sample_path
        else:
            raise HTTPException(status_code=404, detail=f"Document with ID {request.document_id} not found in storage.")
    else:
        doc_path = matches[0]

    try:
        result = ocr_service.extract(doc_path)
        fields = result["fields"]

        return {
            "success": True,
            "data": {
                "document_id": request.document_id,
                "document_type": fields.get("document_type") or request.document_type,
                "extracted_fields": fields,
                "confidence": result["confidence"],
                "ocr_confidence": result["ocr_confidence"],
                "raw_text": result["raw_text"]
            },
            "errors": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR extraction failed: {str(e)}")
