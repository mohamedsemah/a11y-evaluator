"""
Authentication and authorization module
Implements API key authentication (simple) and JWT infrastructure (for future use)
"""
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
from config import get_settings
from security import verify_token

logger = logging.getLogger(__name__)
settings = get_settings()

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# HTTP Bearer for JWT tokens
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_api_key(api_key: Optional[str] = Depends(api_key_header)) -> bool:
    """
    Verify API key from header
    Uses API key from settings
    """
    if not settings.AUTH_REQUIRED:
        return True  # Auth not required
    
    if not settings.API_KEY:
        logger.warning("AUTH_REQUIRED is True but no API_KEY configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication misconfigured",
        )
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
        )
    
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    return True


async def verify_jwt_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[dict]:
    """
    Verify JWT token from Authorization header
    Returns user payload if valid, None if not authenticated
    """
    if not settings.AUTH_REQUIRED:
        return None  # Auth not required
    
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


async def get_current_user(
    request: Request,
    api_key: Optional[str] = Depends(api_key_header),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> Optional[str]:
    """
    Get current user - supports both API key and JWT
    Returns user identifier or None if auth not required
    """
    if not settings.AUTH_REQUIRED:
        return None
    
    # Try API key first
    if api_key:
        try:
            await verify_api_key(api_key)
            return "api_key_user"
        except HTTPException:
            raise
    
    # Try JWT token
    if credentials:
        payload = await verify_jwt_token(credentials)
        if payload:
            return payload.get("sub", "jwt_user")
    
    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )

