import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    file_name: str
    document_type: Optional[str] = None

class DocumentCreate(DocumentBase):
    file_path: str
    claim_id: uuid.UUID
    
class Document(DocumentBase):
    id: uuid.UUID
    uploaded_at: datetime
    
    class Config:
        from_attributes = True