import uuid
from sqlalchemy import Column, String, Enum, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import enum

from app.db.base_class import Base

class ClaimStatus(enum.Enum):
    draft = "draft"
    processing = "processing"
    submitted = "submitted"
    approved = "approved"
    denied = "denied"
    paid = "paid"
    resubmitted = "resubmitted"

class Claim(Base):
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=True)
    payer_name = Column(String(255))
    total_amount = Column(Numeric(10, 2))
    date_of_service = Column(DateTime)
    status = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.draft)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="claims")
    documents = relationship("Document", back_populates="claim", cascade="all, delete-orphan")
    service_lines = relationship("ServiceLine", back_populates="claim", cascade="all, delete-orphan")
    analyses = relationship("ClaimAnalysis", back_populates="claim", cascade="all, delete-orphan")