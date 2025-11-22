"""
Security utilities and middleware for the application
"""
import os
from pathlib import Path
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Security configuration - will be loaded from settings
from config import get_settings

settings = get_settings()
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    Returns only the base filename without directory components
    """
    if not filename:
        raise ValueError("Filename cannot be empty")
    
    # Get only the base name (removes any directory components)
    safe_name = Path(filename).name
    
    # Remove any remaining dangerous characters
    # Allow alphanumeric, dots, hyphens, underscores, and spaces
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._- ")
    
    # Ensure it's not empty after sanitization
    if not safe_name or safe_name.strip() == "":
        raise ValueError("Filename is invalid after sanitization")
    
    # Limit length to prevent issues
    if len(safe_name) > 255:
        safe_name = safe_name[:255]
    
    return safe_name


def validate_zip_path(zip_path: str, extract_dir: Path) -> bool:
    """
    Validate that a path from a ZIP file is safe to extract
    Prevents ZipSlip attacks
    """
    try:
        # Resolve the full path
        full_path = (extract_dir / zip_path).resolve()
        extract_dir_resolved = extract_dir.resolve()
        
        # Check if the resolved path is within the extract directory
        return full_path.is_relative_to(extract_dir_resolved)
    except (ValueError, OSError):
        return False


async def get_current_user(request: Request) -> Optional[dict]:
    """
    Get current user from JWT token in request
    Returns None if no valid token, user dict if valid
    """
    credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
    
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        return None
    
    return payload


async def require_auth(request: Request) -> dict:
    """
    Require authentication - raises HTTPException if not authenticated
    """
    credentials: Optional[HTTPAuthorizationCredentials] = await security(request)
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

