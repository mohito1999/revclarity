import uuid
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any
from app.models.meriplex_document import MeriplexDocumentStatus, MeriplexDocumentClassification

class MeriplexDocumentBase(BaseModel):
    file_name: str
    status: MeriplexDocumentStatus
    classification: MeriplexDocumentClassification
    
class MeriplexDocument(MeriplexDocumentBase):
    id: uuid.UUID
    extracted_data: Optional[Any] = None
    processing_error: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True