"""Pydantic request/response schemas for the /api/v1/auth routes."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterRequest(BaseModel):
    """Payload for POST /api/v1/auth/register."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = Field(None, max_length=200)


class LoginRequest(BaseModel):
    """Payload for POST /api/v1/auth/login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Returned by /login and /refresh."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiry


class RefreshRequest(BaseModel):
    """Payload for POST /api/v1/auth/refresh — carries the current access token.

    In a full implementation this would carry a dedicated refresh token stored
    in an HttpOnly cookie.  For now we re-issue from a still-valid JWT so that
    the client can extend its session without re-entering credentials.
    """
    token: str


class LogoutRequest(BaseModel):
    """Payload for POST /api/v1/auth/logout.

    Since JWTs are stateless, logout is advisory: the client should discard the
    token.  A real implementation would add the token to a Redis deny-list here.
    """
    token: Optional[str] = None
