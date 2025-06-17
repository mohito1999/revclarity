import uuid
from sqlalchemy import Column, String, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class PolicyBenefit(Base):
    __tablename__ = "policy_benefits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    
    benefit_type = Column(String(255), nullable=False) # e.g., "Office Visit", "Specialist Visit", "X-Ray"
    cpt_code_match = Column(String(50)) # Optional: can link directly to a CPT code
    is_covered = Column(Boolean, default=False)
    coverage_percent = Column(Numeric(5, 2)) # e.g., 80.00 for 80%
    co_pay_amount = Column(Numeric(10, 2))
    deductible = Column(Numeric(10, 2))
    
    source_document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    
    patient = relationship("Patient")