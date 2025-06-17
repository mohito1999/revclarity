import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import os
from pathlib import Path
import logging

from app import models, schemas
from app.db.session import SessionLocal
from app.crud import crud_claim # Import the crud module
from app.tasks import process_claim_documents # Import our new task

# Define the router with its prefix and tags here
router = APIRouter(
    prefix="/claims",
    tags=["Claims"],
)

# --- Helper Functions (No Change) ---

UPLOAD_DIRECTORY = "./uploads"
Path(UPLOAD_DIRECTORY).mkdir(parents=True, exist_ok=True)

def save_upload_file(upload_file: UploadFile) -> str:
    file_path = os.path.join(UPLOAD_DIRECTORY, upload_file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())
    return file_path

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- NEW: Read Endpoints ---

@router.get("/", response_model=List[schemas.Claim])
def list_claims(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve a list of claims.
    Used for the main dashboard view.
    """
    claims = crud_claim.get_claims(db, skip=skip, limit=limit)
    return claims

@router.get("/{claim_id}", response_model=schemas.Claim)
def read_claim(
    claim_id: uuid.UUID, db: Session = Depends(get_db)
):
    """
    Retrieve the full details of a single claim by its ID.
    Used for the claim detail/workspace page.
    """
    db_claim = crud_claim.get_claim(db, claim_id=claim_id)
    if db_claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return db_claim


# --- API Endpoint (No Change, but path is now relative to the prefix) ---

@router.post("/upload", response_model=schemas.Claim, status_code=201)
async def create_claim_from_upload(
    background_tasks: BackgroundTasks, # Add the dependency
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    This endpoint initiates a new claim by uploading one or more documents.
    It creates a placeholder claim, saves the documents, and kicks off
    a background task to perform AI-based data extraction.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    # 1. Create a new Claim using our CRUD function
    new_claim = crud_claim.create_claim(db)

    # 2. Process each uploaded file
    for upload_file in files:
        file_path = save_upload_file(upload_file)
        doc_data = schemas.DocumentCreate(
            file_name=upload_file.filename,
            file_path=file_path,
            claim_id=new_claim.id
        )
        # Use our CRUD function to create the document
        crud_claim.create_document_for_claim(db, doc_data)

    # 3. Add the AI processing to the background queue
    background_tasks.add_task(process_claim_documents, new_claim.id)
    
    # Log that the task was added
    logger = logging.getLogger(__name__)
    logger.info(f"AI processing task added to the queue for claim_id: {new_claim.id}")
    
    # Eagerly load the documents for the response object
    db.refresh(new_claim, attribute_names=['documents'])
    
    return new_claim