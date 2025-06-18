// This file will hold all the TypeScript types for our API responses.

export interface ServiceLine {
    id: string;
    cpt_code: string | null;
    charge: number | null;
    icd10_codes: string[];
    diagnosis_pointer: string | null;
    code_confidence_score: number | null;
  }
  
  export interface ComplianceFlag {
    level: 'error' | 'warning' | 'info';
    message: string;
  }
  
  export interface Claim {
    id: string;
    patient_id: string;
    status: "draft" | "processing" | "submitted" | "approved" | "denied" | "paid";
    
    // Comprehensive fields from the backend model
    insurance_type: string | null;
    insured_id_number: string | null;
    insured_name: string | null;
    insured_address: string | null;
    is_condition_related_to_employment: boolean | null;
    is_condition_related_to_auto_accident: boolean | null;
    is_condition_related_to_other_accident: boolean | null;
    insured_policy_group_or_feca_number: string | null;
    date_of_current_illness: string | null; // Comes as ISO string
    referring_provider_name: string | null;
    referring_provider_npi: string | null;
    prior_authorization_number: string | null;
    federal_tax_id_number: string | null;
    patient_account_no: string | null;
    accept_assignment: boolean | null;
    total_charge_amount: number | null;
    amount_paid_by_patient: number | null;
    service_facility_location_info: string | null;
    billing_provider_info: string | null;
    billing_provider_npi: string | null;
    
    // RevClarity specific fields
    payer_name: string | null;
    date_of_service: string | null; // Comes as ISO string
    submission_date: string | null; // Comes as ISO string
    adjudication_date: string | null; // Comes as ISO string
    patient_responsibility_amount: number | null;
    payer_paid_amount: number | null;
    edi_transaction_id: string | null;
    eligibility_status: string | null;
    compliance_flags: ComplianceFlag[] | null;
    
    // Denial fields
    denial_reason: string | null;
    denial_root_cause: string | null;
    denial_recommended_action: string | null;
  
    created_at: string; // Comes as ISO string
    updated_at: string; // Comes as ISO string
  
    // Relationships
    documents: any[]; // Use 'any' for now, can be refined if needed
    service_lines: ServiceLine[];
  }