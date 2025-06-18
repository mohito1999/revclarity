import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.db.base_class import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # --- MODIFIED ---
    # A document can belong to a claim OR a patient directly. So claim_id can be null.
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    
    # --- MODIFIED ---
    # Renamed document_type to be more specific, e.g., 'POLICY_DOC', 'CLAIM_FORM'
    document_purpose = Column(String(50))
    
    parsed_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="documents")
    # --- NEW ---
    # Complete the link back to the Patient model
    patient = relationship("Patient", back_populates="documents")