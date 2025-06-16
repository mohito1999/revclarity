import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
from pathlib import Path

from app import models, schemas
from app.db.session import SessionLocal

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

# --- API Endpoint (No Change, but path is now relative to the prefix) ---

@router.post("/upload", response_model=schemas.Claim, status_code=201)
async def create_claim_from_upload(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    This endpoint initiates a new claim by uploading one or more documents.
    ... (docstring is the same) ...
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    new_claim = models.Claim(status=models.ClaimStatus.processing)
    db.add(new_claim)
    db.commit()
    db.refresh(new_claim)

    for upload_file in files:
        file_path = save_upload_file(upload_file)
        doc_data = schemas.DocumentCreate(
            file_name=upload_file.filename,
            file_path=file_path,
            claim_id=new_claim.id
        )
        new_document = models.Document(**doc_data.model_dump())
        db.add(new_document)

    db.commit()
    db.refresh(new_claim)

    print(f"Background task triggered for claim_id: {new_claim.id}")
    
    return new_claim