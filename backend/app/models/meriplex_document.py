import uuid
import enum
from sqlalchemy import Column, String, Enum as SQLAlchemyEnum, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime

from app.db.base_class import Base

class MeriplexDocumentStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class MeriplexDocumentClassification(enum.Enum):
    UNCLASSIFIED = "UNCLASSIFIED"
    REFERRAL_FAX = "REFERRAL_FAX"
    DICTATED_NOTE = "DICTATED_NOTE"
    MODMED_NOTE = "MODMED_NOTE"
    NON_REFERRAL = "NON_REFERRAL" # For the 2 faxes that are not referrals

class MeriplexDocument(Base):
    __tablename__ = "meriplex_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    
    status = Column(SQLAlchemyEnum(MeriplexDocumentStatus), nullable=False, default=MeriplexDocumentStatus.PENDING)
    classification = Column(SQLAlchemyEnum(MeriplexDocumentClassification), nullable=False, default=MeriplexDocumentClassification.UNCLASSIFIED)
    
    extracted_data = Column(JSONB, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)