import uuid
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app import models, schemas

# --- GET Functions ---

def get_claim(db: Session, claim_id: uuid.UUID) -> Optional[models.Claim]:
    """
    Retrieves a single claim by its ID, eagerly loading related documents.
    """
    return db.query(models.Claim).options(joinedload(models.Claim.documents)).filter(models.Claim.id == claim_id).first()

def get_claims(db: Session, skip: int = 0, limit: int = 100) -> List[models.Claim]:
    """
    Retrieves a list of claims with pagination.
    """
    return db.query(models.Claim).order_by(models.Claim.created_at.desc()).offset(skip).limit(limit).all()

def get_document(db: Session, document_id: uuid.UUID) -> Optional[models.Document]:
    """
    Retrieves a single document by its ID.
    """
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def find_document_by_purpose(db: Session, patient_id: uuid.UUID, purpose: str) -> Optional[models.Document]:
    """
    Finds the first document for a given patient with a specific purpose.
    """
    return db.query(models.Document).filter(
        models.Document.patient_id == patient_id,
        models.Document.document_purpose == purpose
    ).first()

# --- CREATE Functions ---

def create_claim(db: Session, patient_id: uuid.UUID) -> models.Claim:
    """
    Creates a new placeholder claim with 'processing' status, linked to a patient.
    """
    new_claim = models.Claim(status=models.ClaimStatus.processing, patient_id=patient_id)
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    return new_claim

def create_document_for_claim(db: Session, doc_in: schemas.DocumentCreate) -> models.Document:
    """

    Creates a document record and associates it with a patient and optionally a claim.
    """
    new_document = models.Document(**doc_in.model_dump())
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document

# --- UPDATE Functions ---

def update_claim_status(db: Session, claim: models.Claim, status: models.ClaimStatus) -> models.Claim:
    """
    Updates the status of a given claim.
    """
    claim.status = status
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim

def update_claim_with_ai_results(
    db: Session,
    claim: models.Claim,
    update_data: schemas.ClaimUpdate,
    status: models.ClaimStatus,
    eligibility_status: str,
    patient_responsibility: float, # <-- New
    compliance_flags: List[dict]
) -> models.Claim:
    """
    A comprehensive function to update a claim with all AI processing results.
    """
    # Update standard fields
    claim_data = update_data.model_dump(exclude_unset=True)
    for field, value in claim_data.items():
        setattr(claim, field, value)
        
    # Update AI-specific and financial fields
    claim.status = status
    claim.eligibility_status = eligibility_status
    claim.patient_responsibility_amount = patient_responsibility # <-- New
    claim.compliance_flags = compliance_flags
    
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim

def create_service_lines_for_claim(db: Session, claim_id: uuid.UUID, validated_codes: dict, confidence_scores: dict, diagnosis_pointers: dict):
    """
    Creates service line records for a claim, including all codes, charges, and pointers.
    (FINAL, SIMPLIFIED VERSION)
    """
    db.query(models.ServiceLine).filter(models.ServiceLine.claim_id == claim_id).delete()

    service_lines_to_add = []
    
    # Get all the final ICD-10 codes ready. This is the full list of diagnoses for the claim.
    final_icd10_codes = [item['code'] for item in validated_codes.get('icd10_codes', [])]

    # For each CPT code, create a service line
    for cpt_item in validated_codes.get('cpt_codes', []):
        cpt_code = cpt_item['code']
        
        charge_amount = 0.0
        if cpt_code == '99214': charge_amount = 150.00
        elif cpt_code == '73610': charge_amount = 180.00

        sl = models.ServiceLine(
            claim_id=claim_id,
            cpt_code=cpt_code,
            # --- THE FIX: Associate ALL relevant ICD-10 codes with this service line ---
            icd10_codes=final_icd10_codes,
            charge=charge_amount,
            code_confidence_score=confidence_scores.get(cpt_code),
            # We still record the primary pointer, even if we show all codes.
            diagnosis_pointer=diagnosis_pointers.get(cpt_code, "A")
        )
        service_lines_to_add.append(sl)

    db.bulk_save_objects(service_lines_to_add)
    db.commit()