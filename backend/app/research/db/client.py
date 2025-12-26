"""Supabase client initialization and base operations."""

import hashlib
from functools import lru_cache
from typing import Optional

from supabase import create_client, Client

from app.config import get_settings


class BaseSupabaseDB:
    """Base class for Supabase database operations."""

    def __init__(self, client: Client, workspace_id: str = "default"):
        self.client = client
        self.workspace_id = workspace_id

    @staticmethod
    def hash_string(text: str, length: int = 32) -> str:
        """Create a hash of a string."""
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()[:length]


@lru_cache()
def get_supabase_client() -> Client:
    """Get cached Supabase client instance."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("Supabase URL and key must be configured")

    # supabase-py v2.x simplified API
    return create_client(settings.supabase_url, settings.supabase_key)


def get_workspace_client(workspace_id: str = "default") -> Client:
    """Get Supabase client for a specific workspace."""
    return get_supabase_client()
