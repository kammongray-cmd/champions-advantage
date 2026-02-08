import os
import streamlit as st
from supabase import create_client, Client

_supabase_client: Client | None = None
_connection_error: str | None = None


def _sanitize_url(url: str) -> str:
    """Sanitize URL by stripping whitespace, trailing slashes, and hidden characters."""
    if not url:
        return ""
    return url.strip().rstrip('/').replace('\n', '').replace('\r', '').replace('\t', '')


def _sanitize_key(key: str) -> str:
    """Sanitize API key by stripping whitespace and hidden characters."""
    if not key:
        return ""
    return key.strip().replace('\n', '').replace('\r', '').replace('\t', '')


def _mask_url(url: str) -> str:
    """Mask URL for safe display, showing only the domain structure."""
    if not url:
        return "[empty]"
    if "://" in url:
        parts = url.split("://", 1)
        protocol = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if "." in rest:
            domain_parts = rest.split(".")
            if len(domain_parts) >= 2:
                return f"{protocol}://{domain_parts[0][:4]}*****.{'.'.join(domain_parts[1:])}"
        return f"{protocol}://{rest[:8]}*****"
    return f"{url[:8]}*****"


def get_supabase_client() -> Client | None:
    """
    Singleton pattern for Supabase client initialization.
    Returns None if keys are missing or connection fails.
    """
    global _supabase_client, _connection_error
    
    if _supabase_client is not None:
        return _supabase_client
    
    raw_url = os.environ.get("SUPABASE_URL", "")
    raw_key = os.environ.get("SUPABASE_KEY", "")
    
    supabase_url = _sanitize_url(raw_url)
    supabase_key = _sanitize_key(raw_key)
    
    if not supabase_url or not supabase_key:
        _connection_error = "Missing SUPABASE_URL or SUPABASE_KEY in secrets"
        return None
    
    if not supabase_url.startswith("https://"):
        _connection_error = f"Invalid URL format. Expected https://... but got: {_mask_url(supabase_url)}"
        return None
    
    try:
        _supabase_client = create_client(supabase_url, supabase_key)
        _connection_error = None
        return _supabase_client
    except Exception as e:
        _connection_error = f"Connection failed to {_mask_url(supabase_url)}: {str(e)}"
        return None


def verify_connection() -> bool:
    """
    Verify that the Supabase connection is working.
    Returns True if connected, False otherwise.
    """
    client = get_supabase_client()
    return client is not None


def get_connection_error() -> str | None:
    """Get the last connection error message for display."""
    global _connection_error
    return _connection_error


def show_connection_debug():
    """Display connection debug info in the UI."""
    raw_url = os.environ.get("SUPABASE_URL", "")
    raw_key = os.environ.get("SUPABASE_KEY", "")
    
    st.markdown("### Connection Debug Info")
    
    if not raw_url:
        st.error("SUPABASE_URL secret is empty or not set")
    else:
        masked = _mask_url(_sanitize_url(raw_url))
        st.info(f"URL (masked): {masked}")
        st.caption(f"URL length: {len(raw_url)} chars, sanitized: {len(_sanitize_url(raw_url))} chars")
    
    if not raw_key:
        st.error("SUPABASE_KEY secret is empty or not set")
    else:
        st.info(f"Key: {raw_key[:8]}...{raw_key[-4:]} ({len(raw_key)} chars)")
    
    if _connection_error:
        st.error(f"Last error: {_connection_error}")
