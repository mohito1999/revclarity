import uuid
from sqlalchemy import Column, String, DateTime, Text, Date
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

from app.db.base_class import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(100))
    last_name = Column(String(100))
    date_of_birth = Column(Date)
    address = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    claims = relationship("Claim", back_populates="patient")
    # --- NEW ---
    # Add a relationship to documents, so we can easily find a patient's policy docs
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")