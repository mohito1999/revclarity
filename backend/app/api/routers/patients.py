import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_patient

router = APIRouter(
    prefix="/patients",
    tags=["Patients"],
)

@router.post("/", response_model=schemas.Patient, status_code=201)
def create_patient(
    patient_in: schemas.PatientCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new patient in the system.
    """
    return crud_patient.create_patient(db=db, patient_in=patient_in)


@router.get("/", response_model=List[schemas.Patient])
def list_patients(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieve a list of all patients.
    """
    return crud_patient.get_patients(db, skip=skip, limit=limit)


@router.get("/{patient_id}", response_model=schemas.Patient)
def read_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get a single patient by their ID.
    """
    db_patient = crud_patient.get_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient