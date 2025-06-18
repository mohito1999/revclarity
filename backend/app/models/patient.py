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

    # --- THE FIX IS HERE ---
    # We are being more explicit with the cascade behavior.
    # "all, delete-orphan" tells SQLAlchemy: "When I delete a Patient,
    # also delete any Claim or Document that belongs to it."
    # `passive_deletes=True` is an optimization that tells it to let the
    # database's own ON DELETE CASCADE handle it, which is more efficient.
    claims = relationship("Claim", back_populates="patient", cascade="all, delete-orphan", passive_deletes=True)
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan", passive_deletes=True)
    policy_benefits = relationship("PolicyBenefit", back_populates="patient", cascade="all, delete-orphan", passive_deletes=True)
