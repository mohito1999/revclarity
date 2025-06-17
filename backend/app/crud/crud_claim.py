import uuid
from sqlalchemy.orm import Session, joinedload
from typing import Optional, List

from app import models, schemas

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

def create_claim(db: Session) -> models.Claim:
    """
    Creates a new placeholder claim with 'processing' status.
    """
    new_claim = models.Claim(status=models.ClaimStatus.processing)
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)
    return new_claim

def create_document_for_claim(db: Session, doc_in: schemas.DocumentCreate) -> models.Document:
    """
    Creates a document record and associates it with a claim.
    """
    new_document = models.Document(**doc_in.model_dump())
    db.add(new_document)
    db.commit()
    db.refresh(new_document)
    return new_document

def update_claim_status(db: Session, claim: models.Claim, status: models.ClaimStatus) -> models.Claim:
    """
    Updates the status of a given claim.
    """
    claim.status = status
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim