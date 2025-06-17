import uuid
from pydantic import BaseModel
from typing import Optional, List

class ServiceLineBase(BaseModel):
    cpt_code: Optional[str] = None
    charge: Optional[float] = None
    code_confidence_score: Optional[float] = None
    icd10_codes: Optional[List[str]] = []
    diagnosis_pointer: Optional[str] = None

class ServiceLine(ServiceLineBase):
    id: uuid.UUID
    
    class Config:
        from_attributes = True