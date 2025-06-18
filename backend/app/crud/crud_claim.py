import uuid
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app import models, schemas

# --- GET Functions ---

def get_claim(db: Session, claim_id: uuid.UUID) -> Optional[models.Claim]:
    """
    Retrieves a single claim by its ID, eagerly loading related documents and patient info.
    """
    return db.query(models.Claim).options(
        joinedload(models.Claim.documents),
        joinedload(models.Claim.patient).joinedload(models.Patient.documents)
    ).filter(models.Claim.id == claim_id).first()

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

def update_claim(db: Session, claim_id: uuid.UUID, claim_in: schemas.ClaimUpdate) -> Optional[models.Claim]:
    """
    Updates a claim with a comprehensive set of new data from a Pydantic schema.
    """
    db_claim = get_claim(db, claim_id)
    if not db_claim:
        return None
        
    update_data = claim_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_claim, field, value)
        
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

def create_service_lines_for_claim(db: Session, claim_id: uuid.UUID, validated_codes: dict, confidence_scores: dict, diagnosis_pointers: dict, extracted_claim_data: dict):
    """
    Creates service line records for a claim, including all codes, charges, and pointers.
    (FINAL, HYPER-REALISTIC VERSION)
    """
    # Clear any old service lines to ensure a clean slate
    db.query(models.ServiceLine).filter(models.ServiceLine.claim_id == claim_id).delete()

    # Get the full list of final, validated ICD-10 codes for the entire claim.
    final_icd10_codes = [item['code'] for item in validated_codes.get('icd10_codes', [])]
    
    # Create a lookup map for the dynamically extracted charges from the AI.
    # The AI returns a list like: [{'cpt_code': '99214', 'charge_amount': 150.0}, ...]
    charge_map = {line.get('cpt_code'): line.get('charge_amount') for line in extracted_claim_data.get('service_lines', [])}

    service_lines_to_add = []
    # Loop through each CPT code that was validated
    for cpt_item in validated_codes.get('cpt_codes', []):
        cpt_code = cpt_item['code']
        
        # Get the dynamic charge from our map, defaulting to 0.0 if not found.
        charge_amount = charge_map.get(cpt_code, 0.0)

        sl = models.ServiceLine(
            claim_id=claim_id,
            cpt_code=cpt_code,
            # Associate ALL relevant diagnoses with this service line.
            icd10_codes=final_icd10_codes,
            charge=charge_amount,
            # Get the confidence score for this specific CPT code.
            code_confidence_score=confidence_scores.get(cpt_code),
            # Get the primary diagnosis pointer for this CPT code.
            diagnosis_pointer=diagnosis_pointers.get(cpt_code, "A")
        )
        service_lines_to_add.append(sl)

    if service_lines_to_add:
        db.bulk_save_objects(service_lines_to_add)
        db.commit()