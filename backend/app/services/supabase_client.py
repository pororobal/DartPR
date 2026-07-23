"""Supabase client singleton for DB, Auth, Realtime integration."""

from supabase import create_client, Client

from app.config import settings


_supabase: Client | None = None


def get_supabase() -> Client:
    """Return a singleton Supabase client using the service role key."""
    global _supabase
    if _supabase is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _supabase


def get_public_client() -> Client:
    """Return a Supabase client with the anon key (for public/RLS queries)."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
    )
