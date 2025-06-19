from pydantic import BaseModel
from typing import Dict

class AnalyticsSummary(BaseModel):
    total_claims: int
    status_counts: Dict[str, int]
    total_charge_amount: float
    total_paid_amount: float
    total_patient_responsibility: float