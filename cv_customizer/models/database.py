"""SQLAlchemy models for database persistence (optional)"""

from sqlalchemy import Column, String, Float, DateTime, JSON, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class CVRecord(Base):
    """Database model for storing Master CV records"""

    __tablename__ = "master_cvs"

    # Primary key
    cv_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), nullable=True, index=True)

    # Core data (stored as JSON)
    cv_data = Column(JSON, nullable=False)

    # Metadata
    source = Column(String(50), default="manual")  # pdf, portfolio, manual
    extraction_confidence = Column(Float, default=1.0)
    parser_version = Column(String(50), nullable=True)

    # ATS metrics
    last_ats_score = Column(Float, nullable=True)
    last_ats_check_date = Column(DateTime, nullable=True)
    target_ats_score = Column(Float, default=95.0)

    # Versioning
    version = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CVRecord {self.cv_id} - User {self.user_id}>"


class CVVersion(Base):
    """Store CV version history for rollback/comparison"""

    __tablename__ = "cv_versions"

    version_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cv_id = Column(String(36), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)

    cv_data = Column(JSON, nullable=False)
    changes_summary = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<CVVersion {self.cv_id} - v{self.version_number}>"
