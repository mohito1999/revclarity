import uuid
from sqlalchemy import Column, String, Enum, DateTime, Numeric, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
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

    # --- Core Identifiers ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False, index=True)
    status = Column(Enum(ClaimStatus), nullable=False, default=ClaimStatus.draft, index=True)

    # --- Box 1-11: Patient & Insured Info ---
    insurance_type = Column(String(50)) # Box 1
    insured_id_number = Column(String(255)) # Box 1a
    insured_name = Column(String(255)) # Box 4
    insured_address = Column(Text) # Box 7
    is_condition_related_to_employment = Column(Boolean) # Box 10a
    is_condition_related_to_auto_accident = Column(Boolean) # Box 10b
    is_condition_related_to_other_accident = Column(Boolean) # Box 10c
    insured_policy_group_or_feca_number = Column(String(255)) # Box 11

    # --- Box 14-23: Health Information ---
    date_of_current_illness = Column(DateTime) # Box 14
    referring_provider_name = Column(String(255)) # Box 17
    referring_provider_npi = Column(String(20)) # Box 17b
    prior_authorization_number = Column(String(255)) # Box 23

    # --- Box 25-33: Provider & Billing Info ---
    federal_tax_id_number = Column(String(50)) # Box 25
    patient_account_no = Column(String(255)) # Box 26
    accept_assignment = Column(Boolean) # Box 27
    total_charge_amount = Column(Numeric(10, 2)) # Box 28
    amount_paid_by_patient = Column(Numeric(10, 2)) # Box 29
    service_facility_location_info = Column(Text) # Box 32
    billing_provider_info = Column(Text) # Box 33
    billing_provider_npi = Column(String(20)) # Box 33a

    # --- RevClarity AI & Processing Fields ---
    payer_name = Column(String(255)) # Still useful to have at the top level
    date_of_service = Column(DateTime)
    submission_date = Column(DateTime)
    adjudication_date = Column(DateTime)
    patient_responsibility_amount = Column(Numeric(10, 2))
    payer_paid_amount = Column(Numeric(10, 2))
    edi_transaction_id = Column(String(255))
    eligibility_status = Column(String(50), default='Unknown')
    compliance_flags = Column(JSONB)
    
    # --- Denial Management (Moved from ClaimAnalysis) ---
    denial_reason = Column(Text)
    denial_root_cause = Column(Text)
    denial_recommended_action = Column(Text)

    # --- Timestamps ---
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Relationships ---
    patient = relationship("Patient", back_populates="claims")
    documents = relationship("Document", back_populates="claim", cascade="all, delete-orphan")
    service_lines = relationship("ServiceLine", back_populates="claim", cascade="all, delete-orphan")