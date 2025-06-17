import uuid
from sqlalchemy import Column, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.db.base_class import Base

class MedicalCode(Base):
    __tablename__ = "medical_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_value = Column(String(50), nullable=False, index=True)
    code_type = Column(String(20), nullable=False, index=True)  # "CPT" or "ICD-10"
    description = Column(Text, nullable=False)

    __table_args__ = (UniqueConstraint('code_value', 'code_type', name='_code_value_type_uc'),)