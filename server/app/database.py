"""
Supabase client factories.

Two separate clients for two separate trust levels:

1. **User-scoped client** (`get_user_client`):
   Instantiated per-request with the caller's JWT. All queries are governed
   by PostgreSQL Row-Level Security — the backend never needs to manually
   filter by user_id.

2. **Service client** (`get_service_client`):
   Uses the service-role key which **bypasses RLS entirely**.
   Reserved exclusively for background workers (Phase 2+) where no
   user session exists. NEVER expose through user-facing routes.
"""

from supabase import create_client, Client
# pyrefly: ignore [missing-import]
from supabase.lib.client_options import ClientOptions

from app.config import settings


def get_user_client(jwt: str) -> Client:
    """Create a Supabase client scoped to the caller's JWT.

    PostgreSQL RLS policies enforce tenant isolation — every query
    is automatically filtered to data owned by the authenticated user.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_ANON_KEY,
        options=ClientOptions(
            headers={"Authorization": f"Bearer {jwt}"}
        ),
    )


def get_service_client() -> Client:
    """Create a Supabase client with service-role privileges.

    ⚠️  This client bypasses ALL Row-Level Security policies.
    Use ONLY inside background task workers — never in user-facing routes.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )
