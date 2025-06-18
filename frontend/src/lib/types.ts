// This file will hold all the TypeScript types for our API responses.

export interface ServiceLine {
    cpt_code: string | null;
    charge: number | null;
    icd10_codes: string[];
    diagnosis_pointer: string | null;
    id: string;
  }
  
  export interface Claim {
    id: string;
    patient_id: string;
    status: "draft" | "processing" | "submitted" | "approved" | "denied" | "paid";
    payer_name: string | null;
    total_charge_amount: number | null;
    date_of_service: string | null; // Comes as ISO string
    created_at: string;
    // Add other top-level fields from your API response as needed
  }