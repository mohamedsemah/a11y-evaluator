"""
Input validation models using Pydantic
"""
from pydantic import BaseModel, Field, validator, UUID4
from typing import List, Optional
import re
import uuid


# Allowed LLM models
ALLOWED_MODELS = ["gpt-4o", "claude-opus-4", "deepseek-v3", "llama-maverick"]


class AnalysisRequest(BaseModel):
    """Validated analysis request"""
    session_id: str = Field(..., description="Session ID (UUID format)")
    models: List[str] = Field(..., min_items=1, max_items=10, description="List of LLM models to use")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        """Validate session ID is a valid UUID"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")
    
    @validator("models", each_item=True)
    def validate_model_name(cls, v):
        """Validate model name is in allowed list"""
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Model '{v}' is not allowed. Allowed models: {', '.join(ALLOWED_MODELS)}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "models": ["gpt-4o", "claude-opus-4"]
            }
        }


class RemediationRequest(BaseModel):
    """Validated remediation request"""
    session_id: str = Field(..., description="Session ID")
    issue_id: str = Field(..., min_length=1, max_length=100, description="Issue ID")
    model: str = Field(..., description="LLM model to use")
    file_path: str = Field(..., min_length=1, max_length=500, description="File path")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")
    
    @validator("model")
    def validate_model(cls, v):
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Model '{v}' is not allowed")
        return v
    
    @validator("issue_id")
    def validate_issue_id(cls, v):
        """Validate issue ID format"""
        if not re.match(r'^[A-Z0-9_\-]+$', v):
            raise ValueError("issue_id contains invalid characters")
        return v


class PreviewRemediationRequest(BaseModel):
    """Validated preview remediation request"""
    session_id: str = Field(..., description="Session ID")
    issue_id: str = Field(..., min_length=1, max_length=100, description="Issue ID")
    model: str = Field(..., description="LLM model to use")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")
    
    @validator("model")
    def validate_model(cls, v):
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Model '{v}' is not allowed")
        return v
    
    @validator("issue_id")
    def validate_issue_id(cls, v):
        if not re.match(r'^[A-Z0-9_\-]+$', v):
            raise ValueError("issue_id contains invalid characters")
        return v


class ApplyRemediationRequest(BaseModel):
    """Validated apply remediation request"""
    session_id: str = Field(..., description="Session ID")
    issue_id: str = Field(..., min_length=1, max_length=100, description="Issue ID")
    model: str = Field(..., description="LLM model to use")
    force_apply: bool = Field(default=False, description="Force apply even if quality score is low")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")
    
    @validator("model")
    def validate_model(cls, v):
        if v not in ALLOWED_MODELS:
            raise ValueError(f"Model '{v}' is not allowed")
        return v
    
    @validator("issue_id")
    def validate_issue_id(cls, v):
        if not re.match(r'^[A-Z0-9_\-]+$', v):
            raise ValueError("issue_id contains invalid characters")
        return v


class RollbackRequest(BaseModel):
    """Validated rollback request"""
    session_id: str = Field(..., description="Session ID")
    issue_id: str = Field(..., min_length=1, max_length=100, description="Issue ID")
    
    @validator("session_id")
    def validate_session_id(cls, v):
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError("session_id must be a valid UUID")
    
    @validator("issue_id")
    def validate_issue_id(cls, v):
        if not re.match(r'^[A-Z0-9_\-]+$', v):
            raise ValueError("issue_id contains invalid characters")
        return v

