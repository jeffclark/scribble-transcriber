"""Security utilities for authentication and token management."""

import secrets
from typing import Optional
from fastapi import Header, HTTPException, status

# Global auth token (generated at startup)
_AUTH_TOKEN: Optional[str] = None


def generate_auth_token() -> str:
    """
    Generate a secure authentication token for localhost API access.

    This prevents malicious local processes from accessing the transcription service.
    Token is generated at startup and must be passed in X-Auth-Token header.

    Returns:
        str: A cryptographically secure random token (32 bytes URL-safe)
    """
    global _AUTH_TOKEN
    _AUTH_TOKEN = secrets.token_urlsafe(32)
    return _AUTH_TOKEN


def set_auth_token(token: str) -> None:
    """
    Set the authentication token (for sidecar mode).

    This is used when the token is provided by Tauri via AUTH_TOKEN environment variable.

    Args:
        token: The authentication token to set
    """
    global _AUTH_TOKEN
    _AUTH_TOKEN = token


def get_auth_token() -> str:
    """
    Get the current authentication token.

    Returns:
        str: The current auth token

    Raises:
        RuntimeError: If token hasn't been generated yet
    """
    if _AUTH_TOKEN is None:
        raise RuntimeError("Auth token not generated. Call generate_auth_token() at startup.")
    return _AUTH_TOKEN


def verify_token(x_auth_token: str = Header(..., description="Authentication token")) -> str:
    """
    FastAPI dependency to verify authentication token from request headers.

    Args:
        x_auth_token: Token from X-Auth-Token header

    Returns:
        str: The validated token

    Raises:
        HTTPException: 401 if token is invalid or missing
    """
    if _AUTH_TOKEN is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server authentication not initialized"
        )

    if x_auth_token != _AUTH_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    return x_auth_token


def verify_token_value(token: str) -> bool:
    """
    Verify token value directly (for query params).

    Args:
        token: Token to verify

    Returns:
        bool: True if token is valid, False otherwise
    """
    return _AUTH_TOKEN is not None and token == _AUTH_TOKEN
