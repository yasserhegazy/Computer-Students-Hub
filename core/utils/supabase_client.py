import os
from supabase import create_client, Client
from django.conf import settings
from typing import Optional


_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance (singleton pattern).
    
    Usage:
        from core.utils.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        # Use for auth operations
        user = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    
    Returns:
        Configured Supabase client
    """
    global _supabase_client
    
    if _supabase_client is None:
        url = settings.SUPABASE_URL
        # Use ANON key (JWT format) - publishable keys might not be supported yet
        key = getattr(settings, 'SUPABASE_ANON_KEY', None) or settings.SUPABASE_KEY
        
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_KEY) must be set in environment variables"
            )
        
        _supabase_client = create_client(url, key)
    
    return _supabase_client


def reset_supabase_client():
    """Reset the client (useful for testing)"""
    global _supabase_client
    if _supabase_client:
        try:
            _supabase_client.auth.sign_out()
        except Exception:
            pass
        _supabase_client = None
