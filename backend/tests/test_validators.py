"""
Unit tests for request validators
"""
import pytest
from pydantic import ValidationError
from validators import AnalysisRequest, PreviewRemediationRequest, ApplyRemediationRequest, RollbackRequest
from uuid import uuid4


class TestAnalysisRequest:
    """Tests for AnalysisRequest validator"""
    
    def test_valid_request(self):
        """Test valid analysis request"""
        session_id = str(uuid4())
        request = AnalysisRequest(
            session_id=session_id,
            models=["gpt-4o", "claude-opus-4"]
        )
        assert request.session_id == session_id
        assert len(request.models) == 2
    
    def test_invalid_uuid(self):
        """Test invalid UUID is rejected"""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                session_id="not-a-uuid",
                models=["gpt-4o"]
            )
    
    def test_empty_models_list(self):
        """Test empty models list is rejected"""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                session_id=str(uuid4()),
                models=[]
            )
    
    def test_invalid_model_name(self):
        """Test invalid model name is rejected"""
        with pytest.raises(ValidationError):
            AnalysisRequest(
                session_id=str(uuid4()),
                models=["GPT-4O"]  # Uppercase not allowed
            )


class TestPreviewRemediationRequest:
    """Tests for PreviewRemediationRequest validator"""
    
    def test_valid_request(self):
        """Test valid preview request"""
        session_id = str(uuid4())
        request = PreviewRemediationRequest(
            session_id=session_id,
            issue_id="issue-123",
            model="gpt-4o"
        )
        assert request.session_id == session_id
        assert request.issue_id == "issue-123"
        assert request.model == "gpt-4o"
    
    def test_empty_issue_id(self):
        """Test empty issue ID is rejected"""
        with pytest.raises(ValidationError):
            PreviewRemediationRequest(
                session_id=str(uuid4()),
                issue_id="",
                model="gpt-4o"
            )


class TestApplyRemediationRequest:
    """Tests for ApplyRemediationRequest validator"""
    
    def test_valid_request(self):
        """Test valid apply request"""
        session_id = str(uuid4())
        request = ApplyRemediationRequest(
            session_id=session_id,
            issue_id="issue-123",
            model="gpt-4o",
            force_apply=False
        )
        assert request.force_apply is False
    
    def test_force_apply_true(self):
        """Test force_apply can be True"""
        session_id = str(uuid4())
        request = ApplyRemediationRequest(
            session_id=session_id,
            issue_id="issue-123",
            model="gpt-4o",
            force_apply=True
        )
        assert request.force_apply is True


class TestRollbackRequest:
    """Tests for RollbackRequest validator"""
    
    def test_valid_request(self):
        """Test valid rollback request"""
        session_id = str(uuid4())
        request = RollbackRequest(
            session_id=session_id,
            issue_id="issue-123"
        )
        assert request.session_id == session_id
        assert request.issue_id == "issue-123"

