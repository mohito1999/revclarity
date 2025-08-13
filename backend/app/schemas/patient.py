import uuid
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from .document import Document # Import for relationship

class PatientBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None

class PatientCreate(PatientBase):
    first_name: str
    last_name: str
    date_of_birth: date

class Patient(PatientBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    documents: List[Document] = []

    class Config:
        from_attributes = True

class PatientName(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    class Config:
        from_attributes = True
