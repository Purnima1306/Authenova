"""
Secure File Storage Service
Handles storage of uploaded document images and verification selfies.
Validates file types, prevents path traversal, and manages local uploads directory.
"""
import os
import uuid
from typing import Tuple

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit


class FileStorageService:
    """Manages secure file uploads and persistence."""

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.upload_dir = os.path.join(base_dir, "uploads")
        os.makedirs(self.upload_dir, exist_ok=True)

    def validate_file(self, filename: str, content: bytes) -> None:
        """Validate extension and file size."""
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size ({len(content)} bytes) exceeds the 15MB limit.")

        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

        # Magic number header check
        is_jpeg = content.startswith(b"\xff\xd8\xff")
        is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
        is_webp = content[:4] == b"RIFF" and content[8:12] == b"WEBP"

        if not (is_jpeg or is_png or is_webp):
            raise ValueError("Uploaded file content does not match a valid image format (PNG, JPG, WEBP).")

    def save_upload(
        self,
        document_content: bytes,
        document_filename: str,
        selfie_content: bytes | None = None,
        selfie_filename: str | None = None
    ) -> Tuple[str, str, str | None]:
        """
        Save document and optional selfie to storage.
        Returns: (document_id, document_path, selfie_path)
        """
        self.validate_file(document_filename, document_content)

        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        doc_ext = os.path.splitext(document_filename)[1].lower() or ".jpg"
        doc_path = os.path.join(self.upload_dir, f"{doc_id}_doc{doc_ext}")

        with open(doc_path, "wb") as f:
            f.write(document_content)

        selfie_path = None
        if selfie_content and selfie_filename:
            self.validate_file(selfie_filename, selfie_content)
            selfie_ext = os.path.splitext(selfie_filename)[1].lower() or ".jpg"
            selfie_path = os.path.join(self.upload_dir, f"{doc_id}_face{selfie_ext}")
            with open(selfie_path, "wb") as f:
                f.write(selfie_content)

        return doc_id, doc_path, selfie_path


# Singleton instance
file_storage = FileStorageService()
