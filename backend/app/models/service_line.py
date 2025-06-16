import uuid
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class ServiceLine(Base):
    __tablename__ = "service_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim_id = Column(UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False)
    cpt_code = Column(String(10))
    icd10_codes = Column(ARRAY(String))
    modifiers = Column(ARRAY(String))
    units = Column(Integer)
    charge = Column(Numeric(10, 2))
    ai_suggestion_source = Column(Text)
    confidence_score = Column(Numeric(3, 2))

    claim = relationship("Claim", back_populates="service_lines")