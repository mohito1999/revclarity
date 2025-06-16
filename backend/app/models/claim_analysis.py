import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base

class ClaimAnalysis(Base):
    __tablename__ = "claim_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    analysis_type = Column(String(50))
    carc_codes = Column(ARRAY(String))
    rarc_codes = Column(ARRAY(String))
    summary_text = Column(Text, nullable=False)
    recommended_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("Claim", back_populates="analyses")