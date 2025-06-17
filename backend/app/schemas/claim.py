import uuid
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional, Any

from app.models.claim import ClaimStatus
from .document import Document  # Import the Document schema
from .service_line import ServiceLine

# Shared properties
class ClaimBase(BaseModel):
    payer_name: Optional[str] = None
    total_amount: Optional[float] = None
    date_of_service: Optional[date] = None

# Properties to receive on claim creation or update
class ClaimCreate(ClaimBase):
    pass

class ClaimUpdate(ClaimBase):
    pass

# Properties to return to client
class ClaimInDB(ClaimBase):
    id: uuid.UUID
    patient_id: Optional[uuid.UUID] = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime
    
    # --- NEW ---
    # Add the new fields to the API response
    eligibility_status: Optional[str] = None
    compliance_flags: Optional[Any] = None

    class Config:
        # This allows Pydantic to read data from ORM models
        from_attributes = True

# A full claim model for the detail view
class Claim(ClaimInDB):
    documents: List[Document] = []
    service_lines: List[ServiceLine] = []