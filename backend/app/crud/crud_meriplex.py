import uuid
import logging
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any

from app.models.meriplex_document import MeriplexDocument, MeriplexDocumentStatus, MeriplexDocumentClassification
from app.schemas.meriplex_document import MeriplexDocument as MeriplexDocumentSchema

logger = logging.getLogger(__name__)

def create_meriplex_document(db: Session, file_name: str, file_path: str) -> MeriplexDocument:
    """
    Creates a new document record in the database with PENDING status.
    """
    db_doc = MeriplexDocument(
        file_name=file_name,
        file_path=file_path,
        status=MeriplexDocumentStatus.PENDING,
        classification=MeriplexDocumentClassification.UNCLASSIFIED
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    logger.info(f"Created new Meriplex document record with ID: {db_doc.id}")
    return db_doc

def get_meriplex_document(db: Session, doc_id: uuid.UUID) -> Optional[MeriplexDocument]:
    """
    Retrieves a single document by its ID.
    """
    return db.query(MeriplexDocument).filter(MeriplexDocument.id == doc_id).first()

def get_meriplex_documents(db: Session, skip: int = 0, limit: int = 100) -> List[MeriplexDocument]:
    """
    Retrieves a list of all Meriplex documents, newest first.
    """
    return db.query(MeriplexDocument).order_by(MeriplexDocument.created_at.desc()).offset(skip).limit(limit).all()

def update_document_status_and_classification(
    db: Session, 
    doc_id: uuid.UUID, 
    status: MeriplexDocumentStatus, 
    classification: MeriplexDocumentClassification
) -> Optional[MeriplexDocument]:
    """
    Updates the status and classification of a document.
    """
    db_doc = get_meriplex_document(db, doc_id)
    if db_doc:
        db_doc.status = status
        db_doc.classification = classification
        db.commit()
        db.refresh(db_doc)
        logger.info(f"Updated document {doc_id} to status: {status.name}, classification: {classification.name}")
    return db_doc

def update_document_with_results(
    db: Session, 
    doc_id: uuid.UUID, 
    extracted_data: Dict[str, Any],
    status: MeriplexDocumentStatus = MeriplexDocumentStatus.COMPLETED,
    error_message: Optional[str] = None
) -> Optional[MeriplexDocument]:
    """
    Updates a document with the extracted data from the AI pipeline.
    """
    db_doc = get_meriplex_document(db, doc_id)
    if db_doc:
        db_doc.extracted_data = extracted_data
        db_doc.status = status
        db_doc.processing_error = error_message
        db.commit()
        db.refresh(db_doc)
        logger.info(f"Updated document {doc_id} with AI extraction results.")
    return db_doc