import streamlit as st
from services.supabase_client import get_supabase_client

TENANT_ID = "kb_signs"


def _get_migration_table():
    """
    Get or create the migration_status table for persistent tracking.
    Returns True if table exists and is accessible.
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.table("migration_status").select("id").limit(1).execute()
        return True
    except Exception:
        return False


def _check_column_exists(table_name: str, column_name: str = "is_active_v3") -> bool:
    """Check if the is_active_v3 column exists in the specified table."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.table(table_name).select(column_name).eq("tenant_id", TENANT_ID).limit(1).execute()
        return True
    except Exception:
        return False


def _get_promoted_ids_from_tracker() -> set:
    """Get all promoted IDs from the migration_status table."""
    client = get_supabase_client()
    if not client:
        return st.session_state.get("promoted_project_ids", set())
    
    if _get_migration_table():
        try:
            response = client.table("migration_status").select("entity_id").eq("is_promoted", True).execute()
            if response.data:
                return {row["entity_id"] for row in response.data}
        except Exception:
            pass
    
    return st.session_state.get("promoted_project_ids", set())


def _set_promoted_in_tracker(entity_id, entity_type: str = "project", is_promoted: bool = True) -> bool:
    """Set promotion status in the migration_status table."""
    client = get_supabase_client()
    if not client:
        if "promoted_project_ids" not in st.session_state:
            st.session_state.promoted_project_ids = set()
        if is_promoted:
            st.session_state.promoted_project_ids.add(entity_id)
        else:
            st.session_state.promoted_project_ids.discard(entity_id)
        return True
    
    if _get_migration_table():
        try:
            existing = client.table("migration_status").select("id").eq("entity_id", entity_id).execute()
            
            if existing.data:
                client.table("migration_status").update({
                    "is_promoted": is_promoted
                }).eq("entity_id", entity_id).execute()
            else:
                client.table("migration_status").insert({
                    "entity_id": str(entity_id),
                    "entity_type": entity_type,
                    "is_promoted": is_promoted
                }).execute()
            return True
        except Exception as e:
            st.error(f"Error updating migration status: {e}")
            return False
    
    if "promoted_project_ids" not in st.session_state:
        st.session_state.promoted_project_ids = set()
    if is_promoted:
        st.session_state.promoted_project_ids.add(entity_id)
    else:
        st.session_state.promoted_project_ids.discard(entity_id)
    return True


def _try_fetch_table(table_name: str, tenant_filter: bool = True):
    """Try to fetch from a table with optional tenant filter. Returns (data, error)."""
    client = get_supabase_client()
    if not client:
        return None, "No database connection"
    
    try:
        query = client.table(table_name).select("*")
        if tenant_filter:
            query = query.eq("tenant_id", TENANT_ID)
        response = query.execute()
        return response.data, None
    except Exception as e:
        return None, str(e)


def audit_data_connection():
    """
    Audit the data connection and find KB Signs data.
    Returns a dict with status information.
    """
    client = get_supabase_client()
    if not client:
        return {"success": False, "message": "No database connection"}
    
    results = {
        "success": False,
        "leads_table": None,
        "projects_table": None,
        "leads_count": 0,
        "projects_count": 0,
        "message": ""
    }
    
    for table_name in ["leads", "Leads"]:
        data, error = _try_fetch_table(table_name)
        if data is not None:
            results["leads_table"] = table_name
            results["leads_count"] = len(data)
            break
    
    for table_name in ["projects", "Projects"]:
        data, error = _try_fetch_table(table_name)
        if data is not None:
            results["projects_table"] = table_name
            results["projects_count"] = len(data)
            break
    
    if results["leads_count"] > 0 or results["projects_count"] > 0:
        results["success"] = True
        results["message"] = f"KB Signs Data Found! Leads: {results['leads_count']}, Projects: {results['projects_count']}"
    else:
        results["message"] = "No KB Signs data found in leads or projects tables."
    
    return results


def get_all_projects():
    """
    Fetch ALL projects for KB Signs tenant.
    Tries 'projects' first, then 'Projects'.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    for table_name in ["projects", "Projects"]:
        try:
            response = client.table(table_name).select("*").eq("tenant_id", TENANT_ID).execute()
            if response.data:
                return response.data
        except Exception:
            continue
    
    return []


def get_all_leads():
    """
    Fetch ALL leads for KB Signs tenant.
    Tries 'leads' first, then 'Leads'.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    for table_name in ["leads", "Leads"]:
        try:
            response = client.table(table_name).select("*").eq("tenant_id", TENANT_ID).execute()
            if response.data:
                return response.data
        except Exception:
            continue
    
    return []


def get_promoted_projects():
    """
    Fetch only projects where is_active_v3 is TRUE for KB Signs tenant.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    for table_name in ["projects", "Projects"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        try:
            if has_column:
                response = client.table(table_name).select("*").eq("tenant_id", TENANT_ID).eq("is_active_v3", True).execute()
                if response.data:
                    return response.data
            else:
                all_projects = get_all_projects()
                promoted_ids = _get_promoted_ids_from_tracker()
                return [p for p in all_projects if str(p.get("id")) in promoted_ids or p.get("id") in promoted_ids]
        except Exception:
            continue
    
    return []


def get_promoted_leads():
    """
    Fetch only leads where is_active_v3 is TRUE for KB Signs tenant.
    """
    client = get_supabase_client()
    if not client:
        return []
    
    for table_name in ["leads", "Leads"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        try:
            if has_column:
                response = client.table(table_name).select("*").eq("tenant_id", TENANT_ID).eq("is_active_v3", True).execute()
                if response.data:
                    return response.data
            else:
                all_leads = get_all_leads()
                promoted_ids = _get_promoted_ids_from_tracker()
                return [l for l in all_leads if str(l.get("id")) in promoted_ids or l.get("id") in promoted_ids]
        except Exception:
            continue
    
    return []


def get_all_promoted_ids() -> set:
    """Get all promoted entity IDs in bulk for KB Signs."""
    client = get_supabase_client()
    if not client:
        return st.session_state.get("promoted_project_ids", set())
    
    for table_name in ["projects", "Projects"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        if has_column:
            try:
                response = client.table(table_name).select("id").eq("tenant_id", TENANT_ID).eq("is_active_v3", True).execute()
                if response.data:
                    return {row["id"] for row in response.data}
            except Exception:
                continue
    
    return _get_promoted_ids_from_tracker()


def promote_projects(project_ids: list, entity_type: str = "project"):
    """
    Set is_active_v3 to TRUE for the given project IDs.
    """
    if not project_ids:
        return False
    
    client = get_supabase_client()
    if not client:
        return False
    
    for table_name in ["projects", "Projects"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        try:
            if has_column:
                for pid in project_ids:
                    client.table(table_name).update({"is_active_v3": True}).eq("id", pid).eq("tenant_id", TENANT_ID).execute()
                return True
            else:
                for pid in project_ids:
                    _set_promoted_in_tracker(pid, entity_type, True)
                return True
        except Exception as e:
            st.error(f"Error promoting projects: {e}")
            continue
    
    return False


def promote_leads(lead_ids: list):
    """
    Set is_active_v3 to TRUE for the given lead IDs.
    """
    if not lead_ids:
        return False
    
    client = get_supabase_client()
    if not client:
        return False
    
    for table_name in ["leads", "Leads"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        try:
            if has_column:
                for lid in lead_ids:
                    client.table(table_name).update({"is_active_v3": True}).eq("id", lid).eq("tenant_id", TENANT_ID).execute()
                return True
            else:
                for lid in lead_ids:
                    _set_promoted_in_tracker(lid, "lead", True)
                return True
        except Exception as e:
            st.error(f"Error promoting leads: {e}")
            continue
    
    return False


def demote_projects(project_ids: list):
    """
    Set is_active_v3 to FALSE for the given project IDs.
    """
    if not project_ids:
        return False
    
    client = get_supabase_client()
    if not client:
        return False
    
    for table_name in ["projects", "Projects"]:
        has_column = _check_column_exists(table_name, "is_active_v3")
        
        try:
            if has_column:
                for pid in project_ids:
                    client.table(table_name).update({"is_active_v3": False}).eq("id", pid).eq("tenant_id", TENANT_ID).execute()
                return True
            else:
                for pid in project_ids:
                    _set_promoted_in_tracker(pid, "project", False)
                return True
        except Exception as e:
            st.error(f"Error demoting projects: {e}")
            continue
    
    return False


def is_project_promoted(project_id) -> bool:
    """Check if a specific project is promoted to V3."""
    promoted_ids = get_all_promoted_ids()
    return str(project_id) in promoted_ids or project_id in promoted_ids
