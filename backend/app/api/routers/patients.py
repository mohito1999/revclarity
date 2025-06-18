import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_patient, crud_claim
from app.tasks import process_policy_document
from app.utils.file_handling import save_upload_file

logger = logging.getLogger(__name__)

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


@router.post("/{patient_id}/documents", response_model=schemas.Document)
def upload_patient_document(
    patient_id: uuid.UUID,
    document_purpose: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a general document and associate it with a patient.
    If the purpose is 'POLICY_DOC', it dispatches a task to the Celery queue for processing.
    """
    # Check if patient exists first
    if not crud_patient.get_patient(db, patient_id=patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    
    file_path = save_upload_file(file)
    
    # Create the document record in the database
    doc_data = schemas.DocumentCreate(
        file_name=file.filename,
        file_path=file_path,
        patient_id=patient_id,
        claim_id=None,
        document_purpose=document_purpose
    )
    new_document = crud_claim.create_document_for_claim(db, doc_data)

    # Dispatch task to Celery
    if document_purpose and document_purpose.upper() == 'POLICY_DOC':
        logger.info(f"Dispatching policy processing task to Celery for patient {patient_id}")
        # Call .delay() to send the job to the message queue (e.g., Redis).
        # We must pass simple, serializable types like strings.
        process_policy_document.delay(str(patient_id), str(new_document.id))

    return new_document

@router.delete("/{patient_id}", status_code=204)
def delete_patient(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Delete a patient and all their associated claims and documents.
    """
    db_patient = crud_patient.delete_patient(db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return None # Return no content on successful deletion