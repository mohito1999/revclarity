import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List
from fastapi.responses import Response

from app import models, schemas
from app.api.deps import get_db
from app.crud import crud_claim, crud_patient
from app.tasks import process_claim_documents
from app.models.claim import ClaimStatus
from app.utils.file_handling import save_upload_file
from app.services import pdf_service

router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)

logger = logging.getLogger(__name__)

@router.post("/upload", response_model=schemas.Claim, status_code=201)
def create_claim_from_upload(
    patient_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    The primary endpoint to initiate a new claim.
    Dispatches a task to the Celery queue for AI processing.
    """
    patient = crud_patient.get_patient(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient with id {patient_id} not found.")

    file_path = save_upload_file(file)
    
    new_claim = crud_claim.create_claim(db, patient_id=patient_id)
    
    doc_data = schemas.DocumentCreate(
        file_name=file.filename,
        file_path=file_path,
        patient_id=patient_id,
        claim_id=new_claim.id,
        document_purpose='CLAIM_FORM'
    )
    new_document = crud_claim.create_document_for_claim(db, doc_data)

    logger.info(f"Dispatching claim processing task to Celery for claim_id: {new_claim.id}")
    process_claim_documents.delay(str(new_claim.id), str(new_document.id))
    
    return new_claim

@router.post("/{claim_id}/simulate-denial", response_model=schemas.Claim)
async def simulate_denial( # <-- Can be async or sync, doesn't matter here
    claim_id: uuid.UUID,
    # background_tasks: BackgroundTasks, # <-- REMOVED UNUSED DEPENDENCY
    db: Session = Depends(get_db)
):
    """
    Simulates a payer denying a claim. This updates the claim status.
    """
    claim = crud_claim.get_claim(db, claim_id=claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
        
    crud_claim.update_claim_status(db, claim=claim, status=ClaimStatus.denied)
    logger.info(f"Claim {claim_id} status updated to DENIED.")
    
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

    pdf_bytes = pdf_service.generate_cms1500_pdf(db_claim)
    
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