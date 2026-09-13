from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.upload import UploadResponse, UploadData
from app.storage.files import file_storage

router = APIRouter()


@router.post("/upload-document", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document image for verification.
    Saves the file securely to storage and returns a unique document_id.
    """
    try:
        content = await file.read()
        doc_id, doc_path, _ = file_storage.save_upload(
            document_content=content,
            document_filename=file.filename
        )
        return UploadResponse(
            success=True,
            data=UploadData(
                document_id=doc_id,
                filename=file.filename,
                content_type=file.content_type or "image/jpeg"
            ),
            errors=[]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")
