import uuid
from sqlalchemy.orm import Session
from typing import List, Optional

from app import models, schemas

def get_patient(db: Session, patient_id: uuid.UUID) -> Optional[models.Patient]:
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()

def get_patients(db: Session, skip: int = 0, limit: int = 100) -> List[models.Patient]:
    return db.query(models.Patient).order_by(models.Patient.created_at.desc()).offset(skip).limit(limit).all()

def create_patient(db: Session, patient_in: schemas.PatientCreate) -> models.Patient:
    new_patient = models.Patient(**patient_in.model_dump())
    db.add(new_patient)
    db.commit()
    db.refresh(new_patient)
    return new_patient

def delete_patient(db: Session, patient_id: uuid.UUID) -> Optional[models.Patient]:
    """
    Deletes a patient and all their associated data (claims, documents).
    """
    db_patient = get_patient(db, patient_id)
    if db_patient:
        db.delete(db_patient)
        db.commit()
    return db_patient
