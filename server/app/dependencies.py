"""
FastAPI dependencies for authentication and database access.

The main dependency chain for protected routes:

    get_current_user()  →  Validates token via Supabase API
            ↓
    get_db()            →  Returns a Supabase client scoped to that JWT
"""

from typing import Annotated

# pyrefly: ignore [missing-import]
from fastapi import Depends, HTTPException, Request, status

from app.database import get_user_client
from supabase import Client


# ── JWT extraction & validation ──────────────────────────────


def get_current_user(request: Request) -> dict:
    """Extract and validate the Supabase JWT from the Authorization header.

    Uses the Supabase Auth API (`get_user`) to reliably verify the token,
    handling any algorithm (HS256, ES256) and automatically checking for revocation.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    
    # Use the Supabase client to call the Auth server and verify the token.
    # This completely bypasses local cryptographic decoding issues.
    client = get_user_client(token)
    
    try:
        user_res = client.auth.get_user(jwt=token)
        if not user_res or not user_res.user:
            raise ValueError("Invalid user session")
            
        return {
            "sub": user_res.user.id,
            "email": user_res.user.email,
            "role": user_res.user.role or "authenticated",
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Database dependency (JWT-scoped) ─────────────────────────


def get_db(request: Request) -> Client:
    """Provide a Supabase client scoped to the caller's JWT.

    This dependency extracts the raw Bearer token and passes it to
    `get_user_client()`, ensuring RLS is enforced at the PostgreSQL layer.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header.split(" ", 1)[1]
    return get_user_client(token)


# Type aliases for cleaner route signatures
CurrentUser = Annotated[dict, Depends(get_current_user)]
UserDB = Annotated[Client, Depends(get_db)]
