import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from app import schemas
from app.api.deps import get_db
from app.crud import crud_meriplex
from app.utils.file_handling import save_upload_file
from app.tasks import process_meriplex_document

router = APIRouter(
    prefix="/orthopilot",
    tags=["OrthoPilot (Meriplex POC)"],
)

logger = logging.getLogger(__name__)

@router.post("/documents/upload", response_model=List[schemas.MeriplexDocument], status_code=201)
def upload_meriplex_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts one or more PDF files, saves them, creates database records,
    and will eventually dispatch them to a Celery queue for processing.
    """
    created_docs = []
    for file in files:
        if not file.filename:
            continue
        
        try:
            file_path = save_upload_file(file)
            db_doc = crud_meriplex.create_meriplex_document(db, file_name=file.filename, file_path=file_path)
            
            # --- Placeholder for Celery Task ---
            process_meriplex_document.delay(str(db_doc.id))
            
            created_docs.append(db_doc)
        except Exception as e:
            logger.error(f"Failed to process upload for file {file.filename}: {e}", exc_info=True)
            # We continue to the next file if one fails
            continue
    
    if not created_docs:
        raise HTTPException(status_code=500, detail="Failed to process any of the uploaded files.")
        
    return created_docs

@router.get("/documents", response_model=List[schemas.MeriplexDocument])
def list_meriplex_documents(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Retrieve a list of all documents uploaded for the Meriplex POC.
    """
    documents = crud_meriplex.get_meriplex_documents(db, skip=skip, limit=limit)
    return documents