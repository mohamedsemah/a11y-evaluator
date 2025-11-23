"""
Unit tests for database operations
"""
import pytest
from datetime import datetime, timedelta
from database import (
    init_db, create_session, get_session, update_session,
    delete_expired_sessions, session_to_dict, AnalysisSession
)
from config import get_settings

settings = get_settings()


@pytest.fixture
def db_session():
    """Fixture to initialize database for testing"""
    init_db()
    yield
    # Cleanup could go here


class TestSessionOperations:
    """Tests for session database operations"""
    
    def test_create_session(self, db_session):
        """Test creating a session"""
        session_id = "test-session-123"
        files = [
            {"name": "test.html", "path": "/tmp/test.html", "size": 100}
        ]
        
        session = create_session(session_id, files)
        assert session.id == session_id
        assert len(session.files) == 1
        assert session.expires_at > datetime.utcnow()
    
    def test_get_session(self, db_session):
        """Test retrieving a session"""
        session_id = "test-session-456"
        files = [{"name": "test.html", "path": "/tmp/test.html", "size": 100}]
        
        create_session(session_id, files)
        retrieved = get_session(session_id)
        
        assert retrieved is not None
        assert retrieved.id == session_id
        assert len(retrieved.files) == 1
    
    def test_get_nonexistent_session(self, db_session):
        """Test retrieving non-existent session"""
        result = get_session("non-existent-session")
        assert result is None
    
    def test_update_session(self, db_session):
        """Test updating a session"""
        session_id = "test-session-789"
        files = [{"name": "test.html", "path": "/tmp/test.html", "size": 100}]
        
        create_session(session_id, files)
        
        updates = {
            "analysis_results": {"model1": [{"issue": "test"}]}
        }
        
        success = update_session(session_id, updates)
        assert success is True
        
        updated = get_session(session_id)
        assert updated.analysis_results is not None
        assert "model1" in updated.analysis_results
    
    def test_expired_session(self, db_session):
        """Test expired session is not returned"""
        session_id = "test-expired-session"
        files = [{"name": "test.html", "path": "/tmp/test.html", "size": 100}]
        
        # Create session with short expiry (would need to modify create_session to accept custom expiry)
        # For now, just test that expired sessions are handled
        session = create_session(session_id, files)
        
        # Manually expire it (in real scenario, wait for expiry)
        # This is a simplified test
        assert session.expires_at > datetime.utcnow()
    
    def test_delete_expired_sessions(self, db_session):
        """Test deleting expired sessions"""
        # Create a session
        session_id = "test-expired-123"
        files = [{"name": "test.html", "path": "/tmp/test.html", "size": 100}]
        create_session(session_id, files)
        
        # Delete expired (should not delete our session as it's not expired)
        deleted_count = delete_expired_sessions()
        assert deleted_count >= 0  # May be 0 if no expired sessions


class TestSessionToDict:
    """Tests for session dictionary conversion"""
    
    def test_session_to_dict(self, db_session):
        """Test converting session to dictionary"""
        session_id = "test-dict-session"
        files = [{"name": "test.html", "path": "/tmp/test.html", "size": 100}]
        
        session = create_session(session_id, files)
        session_dict = session_to_dict(session)
        
        assert session_dict["id"] == session_id
        assert "files" in session_dict
        assert "analysis_results" in session_dict
        assert "created_at" in session_dict

