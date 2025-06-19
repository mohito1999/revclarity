import uuid
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional, Any, Dict

from app.models.claim import ClaimStatus
from .document import Document
from .service_line import ServiceLine

# NEW: This is now the ONLY schema needed for updating a claim.
# It will be used by both the AI pipeline and the manual edit form.

class ServiceLineUpdate(BaseModel):
    cpt_code: Optional[str] = None
    icd10_codes: Optional[List[str]] = []
    charge: Optional[float] = None
    diagnosis_pointer: Optional[str] = None

class ClaimUpdate(BaseModel):
    # --- Fields from the AI Extractor (ClaimData) ---
    insurance_type: Optional[str] = None
    insured_id_number: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_address: Optional[str] = None
    patient_relationship_to_insured: Optional[str] = None
    insured_name: Optional[str] = None
    insured_address: Optional[str] = None
    is_condition_related_to_employment: Optional[bool] = None
    is_condition_related_to_auto_accident: Optional[bool] = None
    is_condition_related_to_other_accident: Optional[bool] = None
    insured_policy_group_or_feca_number: Optional[str] = None
    date_of_current_illness: Optional[date] = None
    referring_provider_name: Optional[str] = None
    referring_provider_npi: Optional[str] = None
    prior_authorization_number: Optional[str] = None
    federal_tax_id_number: Optional[str] = None
    patient_account_no: Optional[str] = None
    accept_assignment: Optional[bool] = None
    total_charge_amount: Optional[float] = None
    amount_paid_by_patient: Optional[float] = None
    service_facility_location_info: Optional[str] = None
    billing_provider_info: Optional[str] = None
    billing_provider_npi: Optional[str] = None
    payer_name: Optional[str] = None
    date_of_service: Optional[date] = None

    # --- Fields from the AI Analysis Pipeline ---
    eligibility_status: Optional[str] = None
    patient_responsibility_amount: Optional[float] = None
    compliance_flags: Optional[Any] = None
    
    # --- Fields from Manual Edits (including service lines) ---
    service_lines: Optional[List[ServiceLineUpdate]] = None
    
    # This class no longer needs to be separate.
    # We've merged ClaimData and the old ClaimUpdate into one.
    class Config:
        from_attributes = True

# We no longer need the separate ClaimData class.
# The other classes (ServiceLine, Claim) remain the same.

# This is the full Claim object returned by our API
class Claim(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    status: ClaimStatus
    
    # All the fields from our comprehensive database model
    insurance_type: Optional[str] = None
    insured_id_number: Optional[str] = None
    patient_sex: Optional[str] = None
    patient_address: Optional[str] = None
    patient_relationship_to_insured: Optional[str] = None
    insured_name: Optional[str] = None
    insured_address: Optional[str] = None
    is_condition_related_to_employment: Optional[bool] = None
    is_condition_related_to_auto_accident: Optional[bool] = None
    is_condition_related_to_other_accident: Optional[bool] = None
    insured_policy_group_or_feca_number: Optional[str] = None
    date_of_current_illness: Optional[datetime] = None
    referring_provider_name: Optional[str] = None
    referring_provider_npi: Optional[str] = None
    prior_authorization_number: Optional[str] = None
    federal_tax_id_number: Optional[str] = None
    patient_account_no: Optional[str] = None
    accept_assignment: Optional[bool] = None
    total_charge_amount: Optional[float] = None
    amount_paid_by_patient: Optional[float] = None
    service_facility_location_info: Optional[str] = None
    billing_provider_info: Optional[str] = None
    billing_provider_npi: Optional[str] = None
    
    # RevClarity fields
    payer_name: Optional[str] = None
    date_of_service: Optional[datetime] = None
    submission_date: Optional[datetime] = None
    adjudication_date: Optional[datetime] = None
    patient_responsibility_amount: Optional[float] = None
    payer_paid_amount: Optional[float] = None
    edi_transaction_id: Optional[str] = None
    eligibility_status: Optional[str] = None
    compliance_flags: Optional[Any] = None
    denial_reason: Optional[str] = None
    denial_root_cause: Optional[str] = None
    denial_recommended_action: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    documents: List[Document] = []
    service_lines: List[ServiceLine] = []

    class Config:
        from_attributes = True