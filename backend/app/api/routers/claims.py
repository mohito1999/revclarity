import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List
from fastapi.responses import Response

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_claim, crud_patient
from app.tasks import process_claim_creation, process_adjudication
from app.models.claim import ClaimStatus
from app.utils.file_handling import save_upload_file
from app.services import pdf_service
import datetime
from datetime import datetime, timezone

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)

logger = logging.getLogger(__name__)

@router.post("/upload", response_model=schemas.Claim, status_code=201)
def create_claim_from_upload(
    patient_id: uuid.UUID = Form(...),
    files: List[UploadFile] = File(...), # <-- Now accepts multiple files
    db: Session = Depends(get_db)
):
    """
    The primary endpoint to initiate a new claim from multiple documents.
    Dispatches a single task to the Celery queue for full processing.
    """
    patient = crud_patient.get_patient(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient with id {patient_id} not found.")

    # Create a placeholder claim first
     # --- NEW LOGIC: We now create the claim in 'processing' status
    # and will update it to 'draft' only after the full pipeline succeeds.
    new_claim = crud_claim.create_claim(db, patient_id=patient_id)
    new_claim.status = models.claim.ClaimStatus.processing
    db.commit()

    # Save all uploaded files and associate them with the new claim
    for file in files:
        file_path = save_upload_file(file)
        
        # Infer purpose from filename for the demo
        purpose = "UNKNOWN"
        if "intake" in file.filename.lower(): purpose = "PATIENT_INTAKE"
        if "policy" in file.filename.lower(): purpose = "POLICY_DOC"
        if "encounter" in file.filename.lower(): purpose = "ENCOUNTER_NOTE"
        
        doc_data = schemas.DocumentCreate(
            file_name=file.filename, file_path=file_path,
            patient_id=patient_id, claim_id=new_claim.id,
            document_purpose=purpose
        )
        crud_claim.create_document_for_claim(db, doc_data)

    # Dispatch a SINGLE task with just the claim_id.
    # The task itself is now smart enough to find all its own documents.
    logger.info(f"Dispatching comprehensive claim creation task to Celery for claim_id: {new_claim.id}")
    process_claim_creation.delay(str(new_claim.id))
    
    return new_claim

@router.post("/{claim_id}/simulate-outcome", response_model=schemas.Claim)
def simulate_claim_outcome(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Submits the claim and simulates a payer outcome.
    This triggers the AI Adjudicator to make a decision.
    """
    claim = crud_claim.get_claim(db, claim_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # 1. Update the claim status to "submitted" to reflect the action
    claim.status = models.claim.ClaimStatus.submitted
    claim.submission_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(claim)
    
    # 2. Dispatch the adjudication task to the Celery queue
    logger.info(f"Dispatching adjudication task to Celery for claim_id: {claim.id}")
    process_adjudication.delay(str(claim.id))

    # Return the claim in its current "submitted" state.
    # The adjudication will happen in the background.
    return claim

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

@router.get("/{claim_id}/export/cms1500",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "A generated CMS-1500 PDF for the claim.",
        }
    },
)
def export_claim_as_cms1500(
    claim_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Generates and returns a CMS-1500 PDF for the specified claim.
    """
    # Eagerly load all relationships needed for the PDF
    db_claim = db.query(models.Claim).options(
        joinedload(models.Claim.patient),
        joinedload(models.Claim.service_lines)
    ).filter(models.Claim.id == claim_id).first()

    if db_claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")

    pdf_bytes = pdf_service.generate_claim_summary_pdf(db_claim)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=claim_{claim_id}_cms1500.pdf"}
    )

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