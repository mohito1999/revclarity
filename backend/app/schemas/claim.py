import uuid
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import List, Optional, Any, Dict

from app.models.claim import ClaimStatus
from .document import Document
from .service_line import ServiceLine

# This will be the main schema for data coming from our new AI Extractor
class ClaimData(BaseModel):
    # Box 1-11
    insurance_type: Optional[str] = None
    insured_id_number: Optional[str] = None
    patient_name: Optional[str] = None # Will be split into first/last later
    patient_dob: Optional[date] = None
    patient_sex: Optional[str] = None
    insured_name: Optional[str] = None
    patient_address: Optional[str] = None
    patient_city: Optional[str] = None
    patient_state: Optional[str] = None
    patient_zip: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_relationship_to_insured: Optional[str] = None
    insured_address: Optional[str] = None
    is_condition_related_to_employment: Optional[bool] = False
    is_condition_related_to_auto_accident: Optional[bool] = False
    is_condition_related_to_other_accident: Optional[bool] = False
    insured_policy_group_or_feca_number: Optional[str] = None
    
    # Box 14-23
    date_of_current_illness: Optional[date] = None
    referring_provider_name: Optional[str] = None
    referring_provider_npi: Optional[str] = None
    prior_authorization_number: Optional[str] = None
    
    # Box 24 (Service Lines - will be handled separately by the AI)
    # The AI will extract CPT codes and descriptions from the notes.
    
    # Box 25-33
    federal_tax_id_number: Optional[str] = None
    patient_account_no: Optional[str] = None
    accept_assignment: Optional[bool] = True
    total_charge_amount: Optional[float] = None
    amount_paid_by_patient: Optional[float] = 0.0
    service_facility_location_info: Optional[str] = None
    billing_provider_info: Optional[str] = None
    billing_provider_npi: Optional[str] = None

    # Top-level info for our system
    payer_name: Optional[str] = None
    date_of_service: Optional[date] = None
    
class ClaimUpdate(ClaimData):
    # This schema allows updating any of the fields from ClaimData
    eligibility_status: Optional[str] = None
    patient_responsibility_amount: Optional[float] = None
    compliance_flags: Optional[Any] = None
    pass

# This is the full Claim object returned by our API
class Claim(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    status: ClaimStatus
    
    # All the fields from our comprehensive database model
    insurance_type: Optional[str] = None
    insured_id_number: Optional[str] = None
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