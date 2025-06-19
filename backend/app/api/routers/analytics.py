import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models, schemas
from app.api.deps import get_db

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)
logger = logging.getLogger(__name__)

@router.get("/summary", response_model=schemas.analytics.AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Calculates and returns a summary of claim analytics.
    """
    total_claims = db.query(models.Claim).count()
    
    status_counts_query = db.query(models.Claim.status, func.count(models.Claim.id)).group_by(models.Claim.status).all()
    status_counts = {status.name: count for status, count in status_counts_query}

    # Calculate financial totals, handling NULL values by treating them as 0
    financials = db.query(
        func.sum(func.coalesce(models.Claim.total_charge_amount, 0)),
        func.sum(func.coalesce(models.Claim.payer_paid_amount, 0)),
        func.sum(func.coalesce(models.Claim.patient_responsibility_amount, 0))
    ).one()

    summary = schemas.analytics.AnalyticsSummary(
        total_claims=total_claims,
        status_counts=status_counts,
        total_charge_amount=float(financials[0] or 0),
        total_paid_amount=float(financials[1] or 0),
        total_patient_responsibility=float(financials[2] or 0)
    )
    return summary