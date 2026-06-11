from __future__ import annotations

from supabase import Client, create_client
from supabase.client import ClientOptions

from src.config import get_config


def get_client() -> Client:
    """Create a fresh Supabase client for each Streamlit rerun.

    This avoids reusing stale HTTP connections on Windows and gives PostgREST/Storage
    a larger timeout than the HTTPX default.
    """
    cfg = get_config()
    return create_client(
        cfg.supabase_url,
        cfg.supabase_service_role_key,
        options=ClientOptions(
            postgrest_client_timeout=20,
            storage_client_timeout=30,
            schema="public",
        ),
    )
