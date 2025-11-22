"""
Database models and session management
"""
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
import logging
from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AnalysisSession(Base):
    """Database model for analysis sessions"""
    __tablename__ = "analysis_sessions"
    
    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    files = Column(JSON, default=list)
    analysis_results = Column(JSON, default=dict)
    remediation_results = Column(JSON, default=dict)
    remediations = Column(JSON, default=dict)
    user_id = Column(String, nullable=True, index=True)  # For future user association
    total_size = Column(Integer, default=0)  # Total size in bytes
    file_count = Column(Integer, default=0)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_session(session_id: str, files: list, user_id: Optional[str] = None) -> AnalysisSession:
    """Create a new analysis session in database"""
    db = SessionLocal()
    try:
        expires_at = datetime.utcnow() + timedelta(hours=settings.SESSION_EXPIRY_HOURS)
        
        session = AnalysisSession(
            id=session_id,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            files=files,
            analysis_results={},
            remediation_results={},
            remediations={},
            user_id=user_id,
            total_size=sum(f.get("size", 0) for f in files),
            file_count=len(files)
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created session {session_id} in database")
        return session
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create session: {str(e)}")
        raise
    finally:
        db.close()


def get_session(session_id: str) -> Optional[AnalysisSession]:
    """Get session from database"""
    db = SessionLocal()
    try:
        session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        
        if session and session.expires_at < datetime.utcnow():
            logger.warning(f"Session {session_id} has expired")
            return None
        
        return session
    except Exception as e:
        logger.error(f"Failed to get session: {str(e)}")
        return None
    finally:
        db.close()


def update_session(session_id: str, updates: Dict[str, Any]) -> bool:
    """Update session data"""
    db = SessionLocal()
    try:
        session = db.query(AnalysisSession).filter(AnalysisSession.id == session_id).first()
        if not session:
            return False
        
        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        db.commit()
        logger.info(f"Updated session {session_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update session: {str(e)}")
        return False
    finally:
        db.close()


def delete_expired_sessions():
    """Delete expired sessions"""
    db = SessionLocal()
    try:
        expired = db.query(AnalysisSession).filter(
            AnalysisSession.expires_at < datetime.utcnow()
        ).all()
        
        count = len(expired)
        for session in expired:
            db.delete(session)
        
        db.commit()
        logger.info(f"Deleted {count} expired sessions")
        return count
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete expired sessions: {str(e)}")
        return 0
    finally:
        db.close()


def session_to_dict(session: AnalysisSession) -> Dict[str, Any]:
    """Convert database session to dictionary format"""
    return {
        "id": session.id,
        "created_at": session.created_at.isoformat(),
        "expires_at": session.expires_at.isoformat(),
        "files": session.files or [],
        "analysis_results": session.analysis_results or {},
        "remediation_results": session.remediation_results or {},
        "remediations": session.remediations or {},
        "user_id": session.user_id,
        "total_size": session.total_size,
        "file_count": session.file_count
    }

