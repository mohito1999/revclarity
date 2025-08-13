import uuid
import os
import logging
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
import pandas as pd
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

# --- CORRECTED IMPORTS ---
from app import schemas, models # <-- Added 'models' import
from app.api.deps import get_db
from app.crud import crud_meriplex
from app.utils.file_handling import save_upload_file
from app.tasks import process_meriplex_document
from app.models.meriplex_document import MeriplexDocumentClassification
from app.services import openai_service, embedding_service

router = APIRouter(
    prefix="/orthopilot",
    tags=["OrthoPilot (Meriplex POC)"],
)

logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    query: str

@router.post("/documents/upload", response_model=List[schemas.MeriplexDocument], status_code=201)
def upload_meriplex_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    created_docs = []
    for file in files:
        if not file.filename:
            continue
        try:
            file_path = save_upload_file(file)
            db_doc = crud_meriplex.create_meriplex_document(db, file_name=file.filename, file_path=file_path)
            process_meriplex_document.delay(str(db_doc.id))
            created_docs.append(db_doc)
        except Exception as e:
            logger.error(f"Failed to process upload for file {file.filename}: {e}", exc_info=True)
            continue
    if not created_docs:
        raise HTTPException(status_code=500, detail="Failed to process any of the uploaded files.")
    return created_docs

@router.get("/documents", response_model=List[schemas.MeriplexDocument])
def list_meriplex_documents(
    classification: Optional[MeriplexDocumentClassification] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    documents = crud_meriplex.get_meriplex_documents(db, classification=classification, skip=skip, limit=limit)
    return documents

@router.get("/documents/{doc_id}", response_model=schemas.MeriplexDocument)
def get_document_details(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    db_doc = crud_meriplex.get_meriplex_document(db, doc_id=doc_id)
    if db_doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return db_doc

@router.get("/documents/{doc_id}/download")
async def download_meriplex_document(
    doc_id: uuid.UUID,
    db: Session = Depends(get_db)
):
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

@router.get("/modmed_notes/export")
async def export_modmed_notes_to_excel(db: Session = Depends(get_db)):
    docs = crud_meriplex.get_meriplex_documents(db, classification=MeriplexDocumentClassification.MODMED_NOTE)
    if not docs:
        raise HTTPException(status_code=404, detail="No ModMed notes with extracted data found.")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        demographics_list, vitals_list, exam_list, plan_list = [], [], [], []
        for doc in docs:
            data = doc.extracted_data.get('extracted_modmed_note') if doc.extracted_data else None
            if not data: continue
            doc_id, patient_name = str(doc.id), data.get('patient_demographics', {}).get('name', 'N/A')
            if data.get('patient_demographics'): demographics_list.append({'Document ID': doc_id, 'Patient Name': patient_name, **data['patient_demographics']})
            if data.get('vitals'): vitals_list.append({'Document ID': doc_id, 'Patient Name': patient_name, **data['vitals']})
            if data.get('physical_exam', {}).get('extremity_strength_and_tone'):
                for item in data['physical_exam']['extremity_strength_and_tone']: exam_list.append({'Document ID': doc_id, 'Patient Name': patient_name, **item})
            if data.get('impression_and_plan'):
                for item in data['impression_and_plan']:
                    for plan_item in item.get('plan_items', []): plan_list.append({'Document ID': doc_id, 'Patient Name': patient_name, 'Diagnosis': item.get('diagnosis'), 'Plan Type': plan_item.get('type'), 'Plan Details': plan_item.get('details')})
        if demographics_list: pd.DataFrame(demographics_list).to_excel(writer, sheet_name='Patient Demographics', index=False)
        if vitals_list: pd.DataFrame(vitals_list).to_excel(writer, sheet_name='Vitals', index=False)
        if exam_list: pd.DataFrame(exam_list).to_excel(writer, sheet_name='Physical Exam', index=False)
        if plan_list: pd.DataFrame(plan_list).to_excel(writer, sheet_name='Treatment Plan', index=False)
    output.seek(0)
    headers = {'Content-Disposition': 'attachment; filename="modmed_notes_export.xlsx"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# --- THIS IS THE CORRECTED FUNCTION ---
@router.post("/chat")
async def chat_with_documents(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Answers questions about ModMed documents using RAG.
    """
    logger.info(f"RAG Chat Query Received: '{request.query}'")
    try:
        query_vector = embedding_service.get_embeddings([request.query])[0]
        if not query_vector:
            raise HTTPException(status_code=500, detail="Could not generate query embedding.")

        relevant_docs = db.query(models.MeriplexDocument).filter(
            models.MeriplexDocument.classification == MeriplexDocumentClassification.MODMED_NOTE
        ).order_by(
            models.MeriplexDocument.vector.l2_distance(query_vector)
        ).limit(3).all()

        if not relevant_docs:
            return {"answer": "I couldn't find any relevant information in the uploaded ModMed notes to answer that question."}

        context = "\n\n---\n\n".join([
            f"Content from document '{doc.file_name}':\n{doc.extracted_data.get('raw_text', '')}"
            for doc in relevant_docs if doc.extracted_data
        ])

        instructions = "You are a helpful clinical assistant. Answer the user's question based ONLY on the provided context from the visit notes. If the answer is not in the context, say so."
        user_input = f"Context:\n{context}\n\nQuestion: {request.query}"
        
        response_json = await openai_service.call_llm_with_reasoning(
            instructions,
            user_input,
            reasoning_effort="medium",
            is_json=False
        )
        return response_json

    except Exception as e:
        logger.error(f"Error in RAG chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while processing your chat request.")