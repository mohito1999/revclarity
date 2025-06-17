import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_patient, crud_claim # <-- crud_claim imported
from app.utils.file_handling import save_upload_file # Assuming you have this helper
from app.background_tasks.processing import process_policy_document # <-- Background task imported

# It's good practice to have a logger in API files
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
    background_tasks: BackgroundTasks, # <-- Dependency added
    document_purpose: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a general document and associate it with a patient.
    If the purpose is 'POLICY_DOC', it will trigger the AI benefits analysis pipeline.
    """
    # Check if patient exists first
    if not crud_patient.get_patient(db, patient_id=patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # In a real app, this would save the file to a secure location (e.g., S3)
    # and return the path or URL.
    file_path = save_upload_file(file)
    
    # Create the document record in the database
    doc_data = schemas.DocumentCreate(
        file_name=file.filename,
        file_path=file_path,
        patient_id=patient_id,
        document_purpose=document_purpose
    )
    # The user's snippet uses a function from crud_claim, we follow that pattern.
    new_document = crud_claim.create_document_for_claim(db, doc_data)

    # --- NEW: Trigger the policy processing task ---
    if document_purpose == 'POLICY_DOC':
        logger.info(f"Adding policy document processing task to queue for patient {patient_id}")
        background_tasks.add_task(process_policy_document, str(patient_id), str(new_document.id))

    return new_document