import uuid
import os
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_claim, crud_patient
from app.tasks import process_claim_documents, llm_service
from app.models.claim import ClaimStatus

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)

UPLOAD_DIRECTORY = "./uploads"
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

def save_upload_file(upload_file: UploadFile) -> str:
    # Sanitize filename to prevent directory traversal attacks
    filename = Path(upload_file.filename).name
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
    return file_path

@router.post("/upload", response_model=schemas.Claim, status_code=201)
async def create_claim_from_upload(
    background_tasks: BackgroundTasks,
    patient_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    The primary endpoint to initiate a new claim.
    This will create a placeholder claim for a given patient,
    save the associated document, and kick off the full AI pipeline.
    
    Note: For uploading other document types like 'POLICY_DOC', a separate
    endpoint on the /patients router should be used.
    """
    # 1. Verify patient exists
    patient = crud_patient.get_patient(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient with id {patient_id} not found.")

    # 2. Save the uploaded file
    file_path = save_upload_file(file)
    
    # 3. Create a new placeholder claim
    new_claim = crud_claim.create_claim(db, patient_id=patient_id)
    
    # 4. Create the document record linked to the claim and patient
    doc_data = schemas.DocumentCreate(
        file_name=file.filename,
        file_path=file_path,
        patient_id=patient_id,
        claim_id=new_claim.id,
        document_purpose='CLAIM_FORM'
    )
    new_document = crud_claim.create_document_for_claim(db, doc_data)

    # 5. Add the AI processing to the background queue
    background_tasks.add_task(process_claim_documents, new_claim.id, new_document.id)
    logger.info(f"AI processing task added for claim_id: {new_claim.id}, doc_id: {new_document.id}")
    
    return new_claim

# --- Payer Simulation Endpoints ---

@router.post("/{claim_id}/simulate-denial", response_model=schemas.Claim)
async def simulate_denial(
    claim_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Simulates a payer denying a claim. This updates the claim status
    and triggers a background task to perform AI denial analysis.
    """
    claim = crud_claim.get_claim(db, claim_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    # Update status immediately
    crud_claim.update_claim_status(db, claim=claim, status=ClaimStatus.denied)
    logger.info(f"Claim {claim_id} status updated to DENIED.")

    # In a real system, you'd pass denial codes. Here we'll generate them.
    # We'll create a simple background task for the analysis later if needed.
    # For now, let's do a simple update to show the flow.
    # background_tasks.add_task(llm_service.generate_denial_analysis, claim.id)
    
    return claim

@router.post("/{claim_id}/simulate-approval", response_model=schemas.Claim)
async def simulate_approval(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Simulates a payer approving a claim.
    """
    claim = crud_claim.get_claim(db, claim_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    updated_claim = crud_claim.update_claim_status(db, claim=claim, status=ClaimStatus.approved)
    logger.info(f"Claim {claim_id} status updated to APPROVED.")
    
    return updated_claim

# --- Read Endpoints ---

@router.get("/", response_model=List[schemas.Claim])
def list_claims(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve a list of claims.
    """
    claims = crud_claim.get_claims(db, skip=skip, limit=limit)
    return claims

@router.get("/{claim_id}", response_model=schemas.Claim)
def read_claim(
    claim_id: uuid.UUID, db: Session = Depends(get_db)
):
    """
    Retrieve the full details of a single claim by its ID, including all
    AI-generated data like codes, flags, and eligibility status.
    """
    db_claim = crud_claim.get_claim(db, claim_id=claim_id)
    if db_claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return db_claim