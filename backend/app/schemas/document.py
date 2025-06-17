import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    file_name: str
    document_purpose: Optional[str] = None # Renamed from document_type

class DocumentCreate(DocumentBase):
    file_path: str
    patient_id: uuid.UUID # All documents must have a patient
    claim_id: Optional[uuid.UUID] = None
    
class Document(DocumentBase):
    id: uuid.UUID
    uploaded_at: datetime
    
    class Config:
        from_attributes = True