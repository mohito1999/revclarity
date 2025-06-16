import uuid
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional

from app.models.claim import ClaimStatus

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

    class Config:
        # This allows Pydantic to read data from ORM models
        from_attributes = True

# A full claim model for the detail view
class Claim(ClaimInDB):
    # We will add relationships here later, like documents and service lines
    pass