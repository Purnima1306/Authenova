"""
Screening Database Models
Stores completed screening reports, OCR extractions, tampering signals,
face match results, risk calculations, and officer manual decisions.
"""
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from app.database.session import Base


class ScreeningRecord(Base):
    """Persistent storage for document screening lifecycle records."""
    __tablename__ = "screenings"

    document_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=True)
    document_type = Column(String, default="passport")
    status = Column(String, default="pending")  # pending, completed, failed

    # Module results
    ocr_data = Column(JSON, nullable=True)
    validation_data = Column(JSON, nullable=True)
    tampering_data = Column(JSON, nullable=True)
    face_data = Column(JSON, nullable=True)
    risk_data = Column(JSON, nullable=True)
    rag_data = Column(JSON, nullable=True)
    orchestration_logs = Column(JSON, nullable=True)

    # Full compiled report
    full_report = Column(JSON, nullable=True)

    # Human officer decision
    officer_decision = Column(JSON, nullable=True)  # {"action": "Approved", "comment": "...", "timestamp": "..."}

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
