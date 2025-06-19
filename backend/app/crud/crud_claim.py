import uuid
import logging
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app import models, schemas

logger = logging.getLogger(__name__)

# --- GET Functions ---

def get_claim(db: Session, claim_id: uuid.UUID) -> Optional[models.Claim]:
    """
    Retrieves a single claim by its ID, eagerly loading related documents and patient info.
    """
    return db.query(models.Claim).options(
        joinedload(models.Claim.documents),
        joinedload(models.Claim.patient).joinedload(models.Patient.documents)
    ).filter(models.Claim.id == claim_id).first()

# --- NEW: A more comprehensive GET for adjudication ---
def get_claim_for_adjudication(db: Session, claim_id: uuid.UUID) -> Optional[models.Claim]:
    """
    Retrieves a single claim by its ID, eagerly loading all relationships
    needed for the adjudication process.
    """
    return db.query(models.Claim).options(
        joinedload(models.Claim.patient).joinedload(models.Patient.documents),
        joinedload(models.Claim.service_lines)
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

def get_all_documents_for_patient(db: Session, patient_id: uuid.UUID) -> List[models.Document]:
    """
    Retrieves all documents associated with a given patient_id.
    """
    return db.query(models.Document).filter(models.Document.patient_id == patient_id).all()


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

def update_claim_status(db: Session, claim: models.Claim, status: models.ClaimStatus, denial_reason: str = None) -> models.Claim:
    """
    Updates the status of a given claim.
    """
    claim.status = status
    if denial_reason: # If a reason is provided, save it.
        claim.denial_reason = denial_reason
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim

def update_claim(db: Session, claim_id: uuid.UUID, claim_in: schemas.ClaimUpdate) -> Optional[models.Claim]:
    """
    Updates a claim with a comprehensive set of new data from a Pydantic schema.
    This now includes logic to replace service lines.
    """
    db_claim = get_claim(db, claim_id)
    if not db_claim:
        return None
        
    update_data = claim_in.model_dump(exclude_unset=True)

    # --- NEW: Handle service lines separately ---
    if 'service_lines' in update_data:
        new_service_lines_data = update_data.pop('service_lines')
        
        # 1. Delete existing service lines for this claim
        db.query(models.ServiceLine).filter(models.ServiceLine.claim_id == claim_id).delete(synchronize_session=False)
        
        # 2. Create new service lines from the provided data
        for line_data in new_service_lines_data:
            new_line = models.ServiceLine(
                claim_id=claim_id,
                **line_data
            )
            db.add(new_line)

    # Update the other top-level fields on the claim
    for field, value in update_data.items():
        setattr(db_claim, field, value)
        
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

# --- NEW: A specific function to save adjudication results ---
def update_claim_adjudication(db: Session, claim_id: uuid.UUID, update_data: dict) -> models.Claim:
    """
    Updates a claim with the results of the adjudication process.
    """
    db_claim = get_claim(db, claim_id)
    if not db_claim:
        return None
        
    for field, value in update_data.items():
        setattr(db_claim, field, value)
        
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

def create_service_lines_for_claim(db: Session, claim_id: uuid.UUID, validated_codes: dict, confidence_scores: dict, diagnosis_pointers: dict, extracted_claim_data: dict):
    """
    Creates service line records for a claim, including all codes, dynamically extracted charges, and pointers.
    (THE ACTUAL FINAL VERSION)
    """
    db.query(models.ServiceLine).filter(models.ServiceLine.claim_id == claim_id).delete()

    service_lines_to_add = []
    final_icd10_codes = [item['code'] for item in validated_codes.get('icd10_codes', [])]
    
    # Create a lookup map for the dynamically extracted charges from the AI.
    charge_map = {line.get('cpt_code'): line.get('charge_amount', 0.0) for line in extracted_claim_data.get('service_lines', [])}
    logger.info(f"Dynamically extracted charges map: {charge_map}")

    # Loop through each CPT code that was validated
    for cpt_item in validated_codes.get('cpt_codes', []):
        cpt_code = cpt_item['code']
        
        # --- THE FIX: Use the charge_map to get the dynamic charge ---
        charge_amount = charge_map.get(cpt_code, 0.0)
        
        sl = models.ServiceLine(
            claim_id=claim_id,
            cpt_code=cpt_code,
            icd10_codes=final_icd10_codes,
            charge=charge_amount,
            code_confidence_score=confidence_scores.get(cpt_code),
            diagnosis_pointer=diagnosis_pointers.get(cpt_code, "A")
        )
        service_lines_to_add.append(sl)

    if service_lines_to_add:
        db.bulk_save_objects(service_lines_to_add)
        db.commit()

def delete_claim(db: Session, claim_id: uuid.UUID) -> Optional[models.Claim]:
    """
    Deletes a claim and its associated data.
    """
    db_claim = get_claim(db, claim_id)
    if db_claim:
        db.delete(db_claim)
        db.commit()
    return db_claim
