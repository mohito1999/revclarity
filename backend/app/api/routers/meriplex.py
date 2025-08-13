import uuid
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app import schemas
from app.api.deps import get_db
from app.crud import crud_meriplex
from app.utils.file_handling import save_upload_file
from app.tasks import process_meriplex_document
from app.models.meriplex_document import MeriplexDocumentClassification

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
    classification: Optional[MeriplexDocumentClassification] = None, # <-- Add this parameter
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    Retrieve a list of all documents uploaded for the Meriplex POC.
    Can be filtered by classification.
    """
    # This now passes the filter down to the CRUD function
    documents = crud_meriplex.get_meriplex_documents(db, classification=classification, skip=skip, limit=limit)
    return documents

@router.get("/documents/{doc_id}", response_model=schemas.MeriplexDocument)
def get_document_details(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Retrieve the full details of a single Meriplex document by its ID.
    """
    db_doc = crud_meriplex.get_meriplex_document(db, doc_id=doc_id)
    if db_doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_doc

@router.get("/documents/{doc_id}/download")
async def download_meriplex_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Serves a specific document for download by its ID.
    """
    db_doc = crud_meriplex.get_meriplex_document(db, doc_id=doc_id)
    if not db_doc or not db_doc.file_path:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    file_path = db_doc.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server.")

    return FileResponse(
        path=file_path,
        filename=db_doc.file_name,
        media_type='application/pdf'
    )