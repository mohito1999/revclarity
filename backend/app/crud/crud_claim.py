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
    cpt_codes: List[str],
    icd10_codes: List[str],
    compliance_flags: List[dict]
) -> models.Claim:
    """
    A comprehensive function to update a claim with all AI processing results.
    """
    # Update standard fields
    claim_data = update_data.model_dump(exclude_unset=True)
    for field, value in claim_data.items():
        setattr(claim, field, value)
        
    # Update AI-specific fields
    claim.status = status
    claim.eligibility_status = eligibility_status
    claim.assigned_cpt_codes = cpt_codes
    claim.assigned_icd10_codes = icd10_codes
    claim.compliance_flags = compliance_flags
    
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim