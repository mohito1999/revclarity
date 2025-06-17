import uuid
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple

from app import models

def create_benefits_for_patient(db: Session, patient_id: uuid.UUID, source_document_id: uuid.UUID, benefits_data: List[Dict[str, Any]]):
    """
    Creates multiple PolicyBenefit records for a patient from a list of data.
    """
    # First, clear any old benefits from the same source document to prevent duplicates on re-runs
    db.query(models.PolicyBenefit).filter(models.PolicyBenefit.source_document_id == source_document_id).delete()
    
    new_benefits = []
    for benefit_dict in benefits_data:
        benefit = models.PolicyBenefit(
            patient_id=patient_id,
            source_document_id=source_document_id,
            benefit_type=benefit_dict.get('benefit_type'),
            is_covered=benefit_dict.get('is_covered', False),
            co_pay_amount=benefit_dict.get('co_pay_amount'),
            coverage_percent=benefit_dict.get('coverage_percent')
        )
        new_benefits.append(benefit)
        
    db.bulk_save_objects(new_benefits)
    db.commit()
    return new_benefits


def check_claim_eligibility(db: Session, patient_id: uuid.UUID, service_codes: List[Dict[str,str]]) -> Tuple[str, float]:
    """
    Checks a list of service codes against a patient's stored policy benefits.
    Returns a status string and the calculated total patient responsibility.
    """
    benefits = db.query(models.PolicyBenefit).filter(models.PolicyBenefit.patient_id == patient_id).all()
    if not benefits:
        return "Inactive - No Policy on File", 0.0

    # In a real system, this logic would be very complex. We'll simplify for the demo.
    # We'll assume a general co-pay applies if any benefit is found.
    # A more advanced version would match CPT codes to specific benefit types.
    
    # Find a general "Office Visit" or similar benefit to get a co-pay
    patient_responsibility = 0.0
    found_benefit = next((b for b in benefits if "visit" in b.benefit_type.lower()), None)
    
    if found_benefit and found_benefit.co_pay_amount:
        patient_responsibility = float(found_benefit.co_pay_amount)

    return "Active", patient_responsibility