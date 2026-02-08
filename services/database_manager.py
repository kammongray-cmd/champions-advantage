import os
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from services.timezone_utils import today_mountain, now_mountain, get_timestamp_mountain

_engine = None
_connection_error: str | None = None

TENANT_ID = "357145e4-b5a1-43e3-a9ba-f8e834b38034"


def get_engine():
    """
    Get or create SQLAlchemy engine with connection pooling.
    Returns None if DATABASE_URL is missing or connection fails.
    """
    global _engine, _connection_error
    
    if _engine is not None:
        return _engine
    
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        _connection_error = "DATABASE_URL not found in environment"
        return None
    
    try:
        _engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=300
        )
        _connection_error = None
        return _engine
    except Exception as e:
        _connection_error = f"Database connection error: {str(e)}"
        return None


def verify_connection() -> bool:
    """Verify that the database connection is working."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        global _connection_error
        _connection_error = f"Connection test failed: {str(e)}"
        return False


def get_connection_error() -> str | None:
    """Get the last connection error message."""
    return _connection_error


def execute_query(query: str, params: dict = None):
    """Execute a query and return results as list of dicts."""
    engine = get_engine()
    if engine is None:
        return []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    except SQLAlchemyError as e:
        st.error(f"Query error: {str(e)}")
        return []


def execute_update(query: str, params: dict = None) -> bool:
    """Execute an update/insert query. Returns True on success."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text(query), params or {})
            conn.commit()
        return True
    except SQLAlchemyError as e:
        st.error(f"Update error: {str(e)}")
        return False


def get_all_projects():
    """Fetch all projects for the KB Signs tenant."""
    query = """
        SELECT id, client_name, status, notes, estimated_value, is_active_v3, 
               source, last_touched, is_parked, parking_type, value_source
        FROM projects
        WHERE tenant_id = :tenant_id
        ORDER BY last_touched DESC NULLS LAST, created_at DESC NULLS LAST
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_promoted_projects(sort_by: str = "name_asc", include_archived: bool = False):
    """
    Fetch only projects promoted to V3 with sorting options.
    sort_by: 'name_asc', 'newest', 'last_updated'
    include_archived: If False (default), exclude 'Archived', 'Closed - Won', 'Closed - Lost' status projects
    """
    order_clause = {
        "name_asc": "client_name ASC NULLS LAST",
        "newest": "created_at DESC NULLS LAST",
        "last_updated": "last_touched DESC NULLS LAST, created_at DESC NULLS LAST"
    }.get(sort_by, "client_name ASC NULLS LAST")
    
    archived_filter = "" if include_archived else "AND LOWER(status) NOT IN ('archived', 'closed - won', 'closed - lost')"
    
    query = f"""
        SELECT id, client_name, status, notes, estimated_value, 
               source, last_touched, is_parked, created_at, value_source
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE {archived_filter}
        ORDER BY {order_clause}
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_archived_projects():
    """Fetch all archived (Cold Storage) projects."""
    query = """
        SELECT id, client_name, status, notes, estimated_value, 
               source, last_touched, is_parked, created_at, value_source
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE AND LOWER(status) = 'archived'
        ORDER BY last_touched DESC NULLS LAST
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def archive_project(project_id: str) -> bool:
    """Move a project to Cold Storage (Archived status)."""
    from services.timezone_utils import now_mountain
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE projects 
                    SET status = 'Archived', last_touched = :now
                    WHERE id = :id AND tenant_id = :tenant_id
                """),
                {"id": str(project_id), "tenant_id": TENANT_ID, "now": now_mountain()}
            )
            conn.commit()
        add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Project moved to Cold Storage")
        return True
    except SQLAlchemyError as e:
        st.error(f"Error archiving project: {str(e)}")
        return False


def restore_project(project_id: str) -> bool:
    """Restore a project from Cold Storage to Block A."""
    from services.timezone_utils import now_mountain
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE projects 
                    SET status = 'Block A', last_touched = :now
                    WHERE id = :id AND tenant_id = :tenant_id
                """),
                {"id": str(project_id), "tenant_id": TENANT_ID, "now": now_mountain()}
            )
            conn.commit()
        add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Project restored from Cold Storage to Block A")
        return True
    except SQLAlchemyError as e:
        st.error(f"Error restoring project: {str(e)}")
        return False


def get_won_projects():
    """Fetch all projects marked as Closed - Won (Victory Vault)."""
    query = """
        SELECT id, client_name, status, notes, estimated_value, 
               source, last_touched, is_parked, created_at, value_source
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE AND LOWER(status) = 'closed - won'
        ORDER BY last_touched DESC NULLS LAST
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_lost_projects():
    """Fetch all projects marked as Closed - Lost (Lost Deals)."""
    query = """
        SELECT id, client_name, status, notes, estimated_value, 
               source, last_touched, is_parked, created_at, value_source
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE AND LOWER(status) = 'closed - lost'
        ORDER BY last_touched DESC NULLS LAST
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def mark_project_won(project_id: str) -> bool:
    """Mark a project as Closed - Won (Victory Vault)."""
    from services.timezone_utils import now_mountain
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE projects 
                    SET status = 'Closed - Won', last_touched = :now
                    WHERE id = :id AND tenant_id = :tenant_id
                """),
                {"id": str(project_id), "tenant_id": TENANT_ID, "now": now_mountain()}
            )
            conn.commit()
        add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Project marked as WON - moved to Victory Vault")
        return True
    except SQLAlchemyError as e:
        st.error(f"Error marking project as won: {str(e)}")
        return False


def mark_project_lost(project_id: str, reason: str = "") -> bool:
    """Mark a project as Closed - Lost (Lost Deals) with optional reason."""
    from services.timezone_utils import now_mountain
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    UPDATE projects 
                    SET status = 'Closed - Lost', last_touched = :now
                    WHERE id = :id AND tenant_id = :tenant_id
                """),
                {"id": str(project_id), "tenant_id": TENANT_ID, "now": now_mountain()}
            )
            conn.commit()
        reason_text = f" Reason: {reason}" if reason else ""
        add_project_history(project_id, "STATUS_CHANGE", f"[SYSTEM] Project marked as LOST - moved to Lost Deals.{reason_text}")
        return True
    except SQLAlchemyError as e:
        st.error(f"Error marking project as lost: {str(e)}")
        return False


def promote_projects(project_ids: list) -> bool:
    """Set is_active_v3 to TRUE for given project IDs."""
    if not project_ids:
        return False
    
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            for pid in project_ids:
                conn.execute(
                    text("UPDATE projects SET is_active_v3 = TRUE WHERE id = :id AND tenant_id = :tenant_id"),
                    {"id": str(pid), "tenant_id": TENANT_ID}
                )
            conn.commit()
        return True
    except SQLAlchemyError as e:
        st.error(f"Error promoting projects: {str(e)}")
        return False




def demote_projects(project_ids: list) -> bool:
    """Set is_active_v3 to FALSE for given project IDs."""
    if not project_ids:
        return False
    
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            for pid in project_ids:
                conn.execute(
                    text("UPDATE projects SET is_active_v3 = FALSE WHERE id = :id AND tenant_id = :tenant_id"),
                    {"id": str(pid), "tenant_id": TENANT_ID}
                )
            conn.commit()
        return True
    except SQLAlchemyError as e:
        st.error(f"Error demoting projects: {str(e)}")
        return False


def get_all_promoted_ids() -> set:
    """Get all promoted project IDs."""
    query = """
        SELECT id FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE
    """
    results = execute_query(query, {"tenant_id": TENANT_ID})
    return {str(row["id"]) for row in results}


def audit_database():
    """Audit the database connection and table access."""
    results = {
        "success": False,
        "connected": False,
        "projects_count": 0,
        "message": ""
    }
    
    if not verify_connection():
        results["message"] = get_connection_error() or "Connection failed"
        return results
    
    results["connected"] = True
    
    projects = get_all_projects()
    
    results["projects_count"] = len(projects)
    
    if projects:
        results["success"] = True
        results["message"] = f"KB Signs Data Found! {len(projects)} projects loaded."
    else:
        results["message"] = "Connected but no KB Signs projects found."
    
    return results


def get_status_badge(status: str) -> str:
    """Return status badge based on project status - text labels, no emojis."""
    status_map = {
        "new_lead": "NEW",
        "New": "NEW",
        "info_gathering": "INFO",
        "Block A": "A",
        "design": "DES",
        "Block B": "B",
        "pricing": "PRC",
        "Block C": "C",
        "proposal_sent": "SENT",
        "Block D": "D",
        "in_production": "PROD",
        "ACTIVE PRODUCTION": "PROD",
        "completed": "DONE",
        "invoiced": "INV",
        "on_hold": "HOLD",
        "permit_pending": "PRMT",
        "Archived": "ARCH",
        "archived": "ARCH",
        "Closed - Won": "WON",
        "Closed - Lost": "LOST"
    }
    return status_map.get(status, status[:4].upper() if status else "---")


def get_project_by_id(project_id: str):
    """Fetch a single project by ID for the KB Signs tenant."""
    query = """
        SELECT id, client_name, status, notes, estimated_value, 
               source, last_touched, is_parked, google_drive_link,
               google_drive_folder_id, logo_url, created_at, updated_at,
               date_applied, permit_number, permit_office_phone, site_address,
               design_proof_drive_id, design_proof_name, proposal_drive_id, proposal_name,
               COALESCE(no_design_required, FALSE) as no_design_required,
               COALESCE(deposit_invoice_requested, FALSE) as deposit_invoice_requested,
               COALESCE(deposit_invoice_sent, FALSE) as deposit_invoice_sent,
               deposit_received_date, deposit_amount, value_source,
               COALESCE(pending_action, FALSE) as pending_action, action_note, action_due_date,
               primary_contact_name, primary_contact_phone, primary_contact_email,
               secondary_contact_name, secondary_contact_phone, secondary_contact_email,
               master_spec_file_id, master_spec_file_name, master_spec_locked_at,
               COALESCE(production_locked, FALSE) as production_locked,
               signed_spec_file_id, signed_spec_file_name
        FROM projects
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    results = execute_query(query, {"project_id": project_id, "tenant_id": TENANT_ID})
    return results[0] if results else None


def update_project_identity(project_id: str, client_name: str, site_address: str,
                           primary_contact_name: str, primary_contact_phone: str, primary_contact_email: str,
                           secondary_contact_name: str, secondary_contact_phone: str, secondary_contact_email: str) -> bool:
    """Update project identity fields (name, address, contacts)."""
    query = """
        UPDATE projects 
        SET client_name = :client_name,
            site_address = :site_address,
            primary_contact_name = :primary_contact_name,
            primary_contact_phone = :primary_contact_phone,
            primary_contact_email = :primary_contact_email,
            secondary_contact_name = :secondary_contact_name,
            secondary_contact_phone = :secondary_contact_phone,
            secondary_contact_email = :secondary_contact_email,
            updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "client_name": client_name,
        "site_address": site_address,
        "primary_contact_name": primary_contact_name or None,
        "primary_contact_phone": primary_contact_phone or None,
        "primary_contact_email": primary_contact_email or None,
        "secondary_contact_name": secondary_contact_name or None,
        "secondary_contact_phone": secondary_contact_phone or None,
        "secondary_contact_email": secondary_contact_email or None,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def update_design_proof(project_id: str, drive_id: str, filename: str) -> bool:
    """Update project with design proof Drive ID."""
    query = """
        UPDATE projects 
        SET design_proof_drive_id = :drive_id, design_proof_name = :filename, updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "drive_id": drive_id,
        "filename": filename,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def update_no_design_required(project_id: str, no_design_required: bool) -> bool:
    """Update the no_design_required flag for repair/service jobs."""
    query = """
        UPDATE projects 
        SET no_design_required = :no_design_required, updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "no_design_required": no_design_required,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def set_master_spec(project_id: str, file_id: str, file_name: str, client_name: str) -> bool:
    """Set the master spec file for a project (Golden Proof designation).
    
    Stores actual file name for UI display and logs MST timestamp.
    """
    from services.timezone_utils import now_mountain
    
    locked_at = now_mountain()
    
    query = """
        UPDATE projects 
        SET master_spec_file_id = :file_id,
            master_spec_file_name = :file_name,
            master_spec_locked_at = :locked_at,
            updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    success = execute_update(query, {
        "file_id": file_id,
        "file_name": file_name,
        "locked_at": locked_at,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })
    
    if success:
        add_project_history(project_id, f"🔒 MASTER SPEC LOCKED: {file_name} designated as production-ready design at {locked_at.strftime('%I:%M:%S %p MST on %B %d, %Y')}")
    
    return success


def lock_production(project_id: str) -> bool:
    """Lock production status for a project. Prevents design changes without change order."""
    from services.timezone_utils import now_mountain
    
    query = """
        UPDATE projects 
        SET production_locked = TRUE,
            status = 'ACTIVE PRODUCTION',
            status_updated_at = :now,
            updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    success = execute_update(query, {
        "now": now_mountain(),
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })
    
    if success:
        add_project_history(project_id, "🔒 PRODUCTION LOCKED: Project moved to Active Production status")
    
    return success


def set_signed_spec(project_id: str, file_id: str, file_name: str) -> bool:
    """Set the signed spec file for a project (required for production gatekeeper)."""
    query = """
        UPDATE projects 
        SET signed_spec_file_id = :file_id,
            signed_spec_file_name = :file_name,
            updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    success = execute_update(query, {
        "file_id": file_id,
        "file_name": file_name,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })
    
    if success:
        add_project_history(project_id, f"✍️ Signed spec uploaded: {file_name}")
    
    return success


def update_proposal(project_id: str, drive_id: str, filename: str) -> bool:
    """Update project with proposal Drive ID."""
    query = """
        UPDATE projects 
        SET proposal_drive_id = :drive_id, proposal_name = :filename, updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "drive_id": drive_id,
        "filename": filename,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def update_project_status(project_id: str, new_status: str) -> bool:
    """Update a project's status and refresh status_updated_at timestamp."""
    query = """
        UPDATE projects 
        SET status = :status, updated_at = NOW(), status_updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "status": new_status,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def update_project_status_with_note(project_id: str, new_status: str, note_to_append: str) -> bool:
    """Update project status and append a timestamped note. Refreshes status_updated_at."""
    query = """
        UPDATE projects 
        SET status = :status, 
            notes = COALESCE(notes, '') || E'\n' || :note,
            updated_at = NOW(),
            status_updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "status": new_status,
        "note": note_to_append,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def delete_project(project_id: str) -> tuple:
    """
    Permanently delete a project and all associated records. Does NOT delete Google Drive files.
    Returns tuple: (success: bool, error_message: str or None)
    Uses transaction - rolls back on any failure.
    """
    try:
        engine = get_engine()
        if engine is None:
            return (False, "Database engine not available")
            
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                deleted_tables, child_errors = execute_delete_associated_records(conn, project_id)
                
                if child_errors:
                    trans.rollback()
                    return (False, f"Failed to clear child records: {'; '.join(child_errors)}")
                
                result = conn.execute(
                    text("""
                        DELETE FROM projects 
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {"project_id": project_id, "tenant_id": TENANT_ID}
                )
                
                if result.rowcount > 0:
                    trans.commit()
                    return (True, None)
                else:
                    trans.rollback()
                    return (False, "Project not found or already deleted")
            except Exception as e:
                trans.rollback()
                error_str = str(e)
                if "ForeignKeyViolation" in error_str or "foreign key" in error_str.lower():
                    return (False, f"Foreign key constraint blocking: {error_str}")
                return (False, f"Database error during delete: {error_str}")
    except Exception as e:
        return (False, f"Connection error: {str(e)}")


def execute_delete_associated_records(conn, project_id: str) -> tuple:
    """
    Nuclear delete: Delete from ALL child tables that reference projects.
    Based on actual FK constraints in schema.
    Returns tuple: (list of deleted tables, list of errors)
    """
    tables_with_project_fk = [
        "contacts",
        "estimates", 
        "locations",
        "processed_emails",
        "project_estimates",
        "project_files",
        "project_photos",
        "project_touches"
    ]
    
    deleted = []
    errors = []
    
    for table in tables_with_project_fk:
        try:
            result = conn.execute(
                text(f"DELETE FROM {table} WHERE project_id = :project_id"),
                {"project_id": project_id}
            )
            if result.rowcount > 0:
                deleted.append(f"{table}: {result.rowcount} rows")
        except Exception as e:
            error_str = str(e)
            if "does not exist" not in error_str.lower() and "doesn't exist" not in error_str.lower():
                errors.append(f"{table}: {error_str}")
    
    return (deleted, errors)


def update_permit_info(project_id: str, date_applied, permit_number: str, permit_phone: str, site_address: str) -> bool:
    """Update permit tracking information. Auto-sets status to 'permit_pending' if date_applied is set."""
    if date_applied:
        query = """
            UPDATE projects 
            SET date_applied = :date_applied, 
                permit_number = :permit_number, 
                permit_office_phone = :permit_phone,
                site_address = :site_address,
                status = 'permit_pending',
                updated_at = NOW()
            WHERE id = :project_id AND tenant_id = :tenant_id
        """
    else:
        query = """
            UPDATE projects 
            SET date_applied = :date_applied, 
                permit_number = :permit_number, 
                permit_office_phone = :permit_phone,
                site_address = :site_address,
                updated_at = NOW()
            WHERE id = :project_id AND tenant_id = :tenant_id
        """
    return execute_update(query, {
        "date_applied": date_applied,
        "permit_number": permit_number,
        "permit_phone": permit_phone,
        "site_address": site_address,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def ensure_leads_table():
    """Ensure leads table exists with required schema."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    tenant_id VARCHAR(255) NOT NULL DEFAULT '357145e4-b5a1-43e3-a9ba-f8e834b38034',
                    name VARCHAR(255),
                    phone VARCHAR(50),
                    email VARCHAR(255),
                    notes TEXT,
                    source VARCHAR(50) DEFAULT 'manual',
                    status VARCHAR(50) DEFAULT 'new',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    promoted_to_project_id VARCHAR(255)
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_leads_tenant_status ON leads(tenant_id, status)
            """))
            conn.commit()
        return True
    except Exception:
        return False


def get_new_leads():
    """Fetch all uncontacted projects (status='New') for the KB Signs tenant.
    
    UNIFIED WORKFLOW: This now queries the projects table for status='New'
    instead of a separate leads table. When contacted, these become 'Block A'.
    """
    query = """
        SELECT id, client_name as name, 
               COALESCE(
                   (SELECT content FROM project_history 
                    WHERE project_id = projects.id AND entry_type = 'phone' 
                    ORDER BY created_at DESC LIMIT 1), 
                   ''
               ) as phone,
               COALESCE(
                   (SELECT content FROM project_history 
                    WHERE project_id = projects.id AND entry_type = 'email' 
                    ORDER BY created_at DESC LIMIT 1), 
                   ''
               ) as email,
               notes, source, status, created_at
        FROM projects
        WHERE tenant_id = :tenant_id AND status = 'New' AND is_active_v3 = TRUE
        ORDER BY created_at DESC
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def create_lead(name: str, phone: str, email: str, notes: str, source: str = "manual", site_address: str = "") -> bool:
    """Create a new project with status='New' (unified workflow).
    
    UNIFIED WORKFLOW: Creates a project directly with status='New'.
    Auto-maps: name → client_name + primary_contact_name
               phone → primary_contact_phone
               email → primary_contact_email
               site_address → site_address
    When contacted, status flips to 'Block A'.
    """
    import uuid
    from services.timezone_utils import now_mountain
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        project_id = str(uuid.uuid4())
        current_time = now_mountain()
        
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO projects (id, tenant_id, client_name, status, notes, source, 
                                         primary_contact_name, primary_contact_phone, primary_contact_email,
                                         site_address, created_at, updated_at, is_active_v3)
                    VALUES (:id, :tenant_id, :name, 'New', :notes, :source, 
                            :primary_contact_name, :primary_contact_phone, :primary_contact_email,
                            :site_address, :created_at, :updated_at, TRUE)
                """),
                {
                    "id": project_id,
                    "tenant_id": TENANT_ID,
                    "name": name or "Unknown",
                    "notes": notes or "",
                    "source": source,
                    "primary_contact_name": name or None,
                    "primary_contact_phone": phone or None,
                    "primary_contact_email": email or None,
                    "site_address": site_address or None,
                    "created_at": current_time,
                    "updated_at": current_time
                }
            )
            
            # Store phone and email in project_history for retrieval (legacy support)
            if phone:
                conn.execute(
                    text("""
                        INSERT INTO project_history (project_id, entry_type, content)
                        VALUES (:project_id, 'phone', :phone)
                    """),
                    {"project_id": project_id, "phone": phone}
                )
            if email:
                conn.execute(
                    text("""
                        INSERT INTO project_history (project_id, entry_type, content)
                        VALUES (:project_id, 'email', :email)
                    """),
                    {"project_id": project_id, "email": email}
                )
            
            return True
    except Exception as e:
        print(f"Error creating project from intake: {e}")
        return False


def create_lead_from_zapier(data: dict) -> tuple[bool, str]:
    """Create a lead from Zapier webhook data. Returns (success, message)."""
    name = data.get("name", "") or data.get("client_name", "") or ""
    phone = data.get("phone", "") or data.get("phone_number", "") or ""
    email = data.get("email", "") or ""
    notes = data.get("notes", "") or data.get("message", "") or data.get("details", "") or ""
    
    if not name and not phone and not email:
        return False, "No lead data provided"
    
    success = create_lead(name, phone, email, notes, source="zapier")
    if success:
        return True, f"Lead created: {name or email or phone}"
    return False, "Failed to create lead"


def update_lead_status(project_id: str, new_status: str) -> bool:
    """Update the status of a project (unified workflow).
    
    UNIFIED WORKFLOW: Updates project status directly.
    When 'New' project is contacted, status should flip to 'Block A'.
    """
    query = """
        UPDATE projects
        SET status = :new_status, updated_at = NOW(), status_updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "project_id": project_id,
        "new_status": new_status,
        "tenant_id": TENANT_ID
    })


def get_lead_by_id(project_id: str) -> dict:
    """Fetch a single project by ID for the unified workflow.
    
    UNIFIED WORKFLOW: Returns project data formatted like legacy lead data.
    """
    query = """
        SELECT id, client_name as name, notes, source, status, created_at, updated_at,
               COALESCE(
                   (SELECT content FROM project_history 
                    WHERE project_id = projects.id AND entry_type = 'phone' 
                    ORDER BY created_at DESC LIMIT 1), 
                   ''
               ) as phone,
               COALESCE(
                   (SELECT content FROM project_history 
                    WHERE project_id = projects.id AND entry_type = 'email' 
                    ORDER BY created_at DESC LIMIT 1), 
                   ''
               ) as email
        FROM projects
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    results = execute_query(query, {"project_id": project_id, "tenant_id": TENANT_ID})
    return results[0] if results else None


def add_lead_note(project_id: str, note_content: str) -> bool:
    """Add a note to a project and auto-update status to 'Block A' if currently 'New'.
    
    UNIFIED WORKFLOW: If a manual note is added to a 'New' project,
    automatically update its status to 'Block A' (The Shoebox).
    """
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.begin() as conn:
            # Add the note to project_history
            conn.execute(
                text("""
                    INSERT INTO project_history (project_id, entry_type, content)
                    VALUES (:project_id, 'note', :content)
                """),
                {"project_id": project_id, "content": note_content}
            )
            
            # Auto-update status from 'New' to 'Block A' (Note-Triggered Status)
            conn.execute(
                text("""
                    UPDATE projects 
                    SET status = 'Block A', updated_at = NOW(), status_updated_at = NOW()
                    WHERE id = :project_id AND status = 'New' AND tenant_id = :tenant_id
                """),
                {"project_id": project_id, "tenant_id": TENANT_ID}
            )
            
            return True
    except Exception as e:
        print(f"Error adding project note: {e}")
        return False


def get_all_projects_for_ledger():
    """Fetch all V3 projects with financial data for the ledger view."""
    query = """
        SELECT id, client_name, status, estimated_value, 
               COALESCE(commission_rate, 10.0) as commission_rate,
               COALESCE(paid_status, 'unpaid') as paid_status,
               created_at, updated_at
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE
        ORDER BY created_at DESC
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_paid_commissions_for_ledger():
    """Fetch only projects with recorded payments (deposit_received_date or final_payment_date not null).
    Joins projects with commissions table to get payment dates.
    Returns separate entries for deposit and final payment when both exist."""
    query = """
        WITH deposit_payments AS (
            SELECT 
                p.id,
                p.client_name,
                p.status,
                COALESCE(c.total_value, p.estimated_value, 0) as project_value,
                COALESCE(c.deposit_amount, 0) as payment_amount,
                COALESCE(p.commission_rate, 10.0) as commission_rate,
                c.deposit_received_date as payment_date,
                c.commission_notes,
                'deposit' as payment_type
            FROM projects p
            INNER JOIN commissions c ON p.id = c.project_id
            WHERE p.tenant_id = :tenant_id 
              AND p.is_active_v3 = TRUE
              AND c.deposit_received_date IS NOT NULL
        ),
        final_payments AS (
            SELECT 
                p.id,
                p.client_name,
                p.status,
                COALESCE(c.total_value, p.estimated_value, 0) as project_value,
                GREATEST(0, COALESCE(c.total_amount_received, 0) - COALESCE(c.deposit_amount, 0)) as payment_amount,
                COALESCE(p.commission_rate, 10.0) as commission_rate,
                c.final_payment_date as payment_date,
                c.commission_notes,
                'final' as payment_type
            FROM projects p
            INNER JOIN commissions c ON p.id = c.project_id
            WHERE p.tenant_id = :tenant_id 
              AND p.is_active_v3 = TRUE
              AND c.final_payment_date IS NOT NULL
              AND COALESCE(c.total_amount_received, 0) >= COALESCE(c.deposit_amount, 0)
              AND COALESCE(c.total_amount_received, 0) > 0
        )
        SELECT * FROM deposit_payments
        UNION ALL
        SELECT * FROM final_payments
        ORDER BY payment_date DESC
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_commissions_by_period(year: int, month: int, period: int):
    """Get commissions for a specific pay period.
    Period 1: 1st-15th (paid on 20th)
    Period 2: 16th-End of Month (paid on 5th of next month)
    """
    if period == 1:
        start_day = 1
        end_day = 15
    else:
        start_day = 16
        end_day = 31
    
    query = """
        SELECT 
            p.id,
            p.client_name,
            p.status,
            COALESCE(c.total_value, p.estimated_value, 0) as project_value,
            COALESCE(c.deposit_amount, 0) as deposit_amount,
            COALESCE(c.total_amount_received, 0) as total_received,
            COALESCE(p.commission_rate, 10.0) as commission_rate,
            c.deposit_received_date,
            c.final_payment_date,
            c.commission_notes,
            COALESCE(c.deposit_received_date, c.final_payment_date) as payment_date
        FROM projects p
        INNER JOIN commissions c ON p.id = c.project_id
        WHERE p.tenant_id = :tenant_id 
          AND p.is_active_v3 = TRUE
          AND (c.deposit_received_date IS NOT NULL OR c.final_payment_date IS NOT NULL)
          AND (
              (EXTRACT(YEAR FROM c.deposit_received_date) = :year 
               AND EXTRACT(MONTH FROM c.deposit_received_date) = :month
               AND EXTRACT(DAY FROM c.deposit_received_date) BETWEEN :start_day AND :end_day)
              OR
              (EXTRACT(YEAR FROM c.final_payment_date) = :year 
               AND EXTRACT(MONTH FROM c.final_payment_date) = :month
               AND EXTRACT(DAY FROM c.final_payment_date) BETWEEN :start_day AND :end_day)
          )
        ORDER BY COALESCE(c.deposit_received_date, c.final_payment_date) ASC
    """
    return execute_query(query, {
        "tenant_id": TENANT_ID,
        "year": year,
        "month": month,
        "start_day": start_day,
        "end_day": end_day
    })


def update_project_ledger(project_id: str, commission_rate: float, paid_status: str = None) -> bool:
    """Update project financial fields.
    If paid_status is None, only updates commission_rate (preserves existing paid_status)."""
    if paid_status is not None:
        query = """
            UPDATE projects 
            SET commission_rate = :commission_rate, 
                paid_status = :paid_status,
                updated_at = NOW()
            WHERE id = :project_id AND tenant_id = :tenant_id
        """
        return execute_update(query, {
            "commission_rate": commission_rate,
            "paid_status": paid_status,
            "project_id": project_id,
            "tenant_id": TENANT_ID
        })
    else:
        query = """
            UPDATE projects 
            SET commission_rate = :commission_rate, 
                updated_at = NOW()
            WHERE id = :project_id AND tenant_id = :tenant_id
        """
        return execute_update(query, {
            "commission_rate": commission_rate,
            "project_id": project_id,
            "tenant_id": TENANT_ID
        })


def save_project_photo(project_id: str, filename: str, file_data: bytes, photo_type: str = "markup") -> bool:
    """Save a photo to the project_photos table."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT id FROM project_photos WHERE project_id = :project_id AND filename = :filename"),
                {"project_id": project_id, "filename": filename}
            ).fetchone()
            
            if existing:
                conn.execute(
                    text("""
                        UPDATE project_photos 
                        SET file_data = :file_data, created_at = NOW()
                        WHERE project_id = :project_id AND filename = :filename
                    """),
                    {"project_id": project_id, "filename": filename, "file_data": file_data}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO project_photos (project_id, filename, file_data, photo_type)
                        VALUES (:project_id, :filename, :file_data, :photo_type)
                    """),
                    {"project_id": project_id, "filename": filename, "file_data": file_data, "photo_type": photo_type}
                )
            conn.commit()
        return True
    except SQLAlchemyError as e:
        st.error(f"Photo save error: {str(e)}")
        return False


def get_project_photos(project_id: str, photo_type: str = None) -> list:
    """Fetch photos for a project. Returns list of dicts with id, filename, file_data, photo_type."""
    engine = get_engine()
    if engine is None:
        return []
    
    try:
        with engine.connect() as conn:
            if photo_type:
                result = conn.execute(
                    text("""
                        SELECT id, filename, file_data, photo_type, created_at
                        FROM project_photos 
                        WHERE project_id = :project_id AND photo_type = :photo_type
                        ORDER BY created_at DESC
                    """),
                    {"project_id": project_id, "photo_type": photo_type}
                )
            else:
                result = conn.execute(
                    text("""
                        SELECT id, filename, file_data, photo_type, created_at
                        FROM project_photos 
                        WHERE project_id = :project_id
                        ORDER BY created_at DESC
                    """),
                    {"project_id": project_id}
                )
            rows = result.fetchall()
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    except SQLAlchemyError as e:
        st.error(f"Photo fetch error: {str(e)}")
        return []


def delete_project_photo(photo_id: str) -> bool:
    """Delete a photo by ID."""
    return execute_update("DELETE FROM project_photos WHERE id = :photo_id", {"photo_id": photo_id})


def get_next_photo_index(project_id: str, photo_type: str) -> int:
    """Get the next available index for a photo category (logo, reference).
    Checks existing files in database and returns the next sequential number."""
    engine = get_engine()
    if engine is None:
        return 1
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT COUNT(*) as count
                    FROM project_photos 
                    WHERE project_id = :project_id AND photo_type = :photo_type
                """),
                {"project_id": project_id, "photo_type": photo_type}
            )
            row = result.fetchone()
            return (row[0] if row else 0) + 1
    except SQLAlchemyError:
        return 1


def get_photos_by_categories(project_id: str) -> dict:
    """Fetch all photos for a project organized by category.
    Returns dict with keys: site, logo, reference, markup"""
    engine = get_engine()
    if engine is None:
        return {"site": [], "logo": [], "reference": [], "markup": []}
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, filename, file_data, photo_type, created_at
                    FROM project_photos 
                    WHERE project_id = :project_id
                    ORDER BY created_at DESC
                """),
                {"project_id": project_id}
            )
            rows = result.fetchall()
            columns = result.keys()
            
            categories = {"site": [], "logo": [], "reference": [], "markup": []}
            for row in rows:
                photo = dict(zip(columns, row))
                photo_type = photo.get("photo_type", "site")
                if photo_type in categories:
                    categories[photo_type].append(photo)
                else:
                    categories["site"].append(photo)
            
            return categories
    except SQLAlchemyError as e:
        st.error(f"Photo categorization error: {str(e)}")
        return {"site": [], "logo": [], "reference": [], "markup": []}


def update_deposit_stage(project_id: str, stage: str, value: bool) -> bool:
    """Update deposit workflow stage flags."""
    column_map = {
        "invoice_requested": "deposit_invoice_requested",
        "invoice_sent": "deposit_invoice_sent"
    }
    
    column = column_map.get(stage)
    if not column:
        return False
    
    query = f"""
        UPDATE projects 
        SET {column} = :value, updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "value": value,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def mark_deposit_received(project_id: str, deposit_date, deposit_amount: float) -> bool:
    """Mark deposit as received, update status to ACTIVE PRODUCTION, and update commissions."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(
                    text("""
                        UPDATE projects 
                        SET deposit_received_date = :deposit_date,
                            deposit_amount = :deposit_amount,
                            status = 'ACTIVE PRODUCTION',
                            updated_at = NOW()
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {
                        "deposit_date": deposit_date,
                        "deposit_amount": deposit_amount,
                        "project_id": project_id,
                        "tenant_id": TENANT_ID
                    }
                )
                
                try:
                    conn.execute(
                        text("""
                            INSERT INTO commissions (project_id, deposit_received_date, deposit_amount, created_at)
                            VALUES (:project_id, :deposit_date, :deposit_amount, NOW())
                            ON CONFLICT (project_id) DO UPDATE
                            SET deposit_received_date = :deposit_date,
                                deposit_amount = :deposit_amount,
                                updated_at = NOW()
                        """),
                        {
                            "project_id": project_id,
                            "deposit_date": deposit_date,
                            "deposit_amount": deposit_amount
                        }
                    )
                except Exception:
                    pass
                
                trans.commit()
                return True
            except Exception as e:
                trans.rollback()
                print(f"Error marking deposit received: {e}")
                return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def add_project_note(project_id: str, note_text: str) -> bool:
    """Add a timestamped note to the project's notes field (Mountain Time)."""
    timestamp = get_timestamp_mountain()
    formatted_note = f"[{timestamp}] {note_text}"
    
    query = """
        UPDATE projects 
        SET notes = CASE 
            WHEN notes IS NULL OR notes = '' THEN :note
            ELSE notes || E'\\n' || :note
        END,
        updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "note": formatted_note,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def add_project_touch(project_id: str, touch_type: str, note: str) -> bool:
    """Add a touch record to project_touches history table."""
    query = """
        INSERT INTO project_touches (id, project_id, touch_type, note, touched_at, created_at)
        VALUES (gen_random_uuid(), :project_id, :touch_type, :note, NOW(), NOW())
    """
    return execute_update(query, {
        "project_id": project_id,
        "touch_type": touch_type,
        "note": note
    })


def get_project_touches(project_id: str, limit: int = 20) -> list:
    """Get touch history for a project, ordered by most recent."""
    query = """
        SELECT id, touch_type, note, touched_at
        FROM project_touches
        WHERE project_id = :project_id
        ORDER BY touched_at DESC
        LIMIT :limit
    """
    return execute_query(query, {"project_id": project_id, "limit": limit})


def get_primary_contact_email(project_id: str) -> str:
    """Get the primary contact email for a project from contacts table."""
    query = """
        SELECT email FROM contacts 
        WHERE project_id = :project_id AND is_primary = TRUE
        LIMIT 1
    """
    results = execute_query(query, {"project_id": project_id})
    if results and results[0].get("email"):
        return results[0]["email"]
    
    query_any = """
        SELECT email FROM contacts 
        WHERE project_id = :project_id AND email IS NOT NULL AND email != ''
        ORDER BY created_at ASC
        LIMIT 1
    """
    results = execute_query(query_any, {"project_id": project_id})
    if results and results[0].get("email"):
        return results[0]["email"]
    
    return ""


def update_project_estimated_value(project_id: str, estimated_value: float) -> bool:
    """Update project's estimated value."""
    query = """
        UPDATE projects 
        SET estimated_value = :estimated_value, updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "estimated_value": estimated_value,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def save_commission_amounts(project_id: str, total_value: float, deposit_amount: float, deposit_date=None, notes: str = None) -> bool:
    """Save confirmed amounts to commissions table - Source of Truth for pay.
    deposit_date is optional - only set when deposit is actually received."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                if deposit_date:
                    conn.execute(
                        text("""
                            INSERT INTO commissions (project_id, total_value, deposit_amount, deposit_received_date, commission_notes, created_at)
                            VALUES (:project_id, :total_value, :deposit_amount, :received_date, :notes, NOW())
                            ON CONFLICT (project_id) DO UPDATE
                            SET total_value = :total_value,
                                deposit_amount = :deposit_amount,
                                deposit_received_date = :received_date,
                                commission_notes = :notes,
                                updated_at = NOW()
                        """),
                        {
                            "project_id": project_id,
                            "total_value": total_value,
                            "deposit_amount": deposit_amount,
                            "received_date": deposit_date,
                            "notes": notes
                        }
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO commissions (project_id, total_value, deposit_amount, commission_notes, created_at)
                            VALUES (:project_id, :total_value, :deposit_amount, :notes, NOW())
                            ON CONFLICT (project_id) DO UPDATE
                            SET total_value = :total_value,
                                deposit_amount = :deposit_amount,
                                commission_notes = :notes,
                                updated_at = NOW()
                        """),
                        {
                            "project_id": project_id,
                            "total_value": total_value,
                            "deposit_amount": deposit_amount,
                            "notes": notes
                        }
                    )
                trans.commit()
                return True
            except Exception as e:
                trans.rollback()
                print(f"Error saving commission amounts: {e}")
                return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def get_commission_notes(project_id: str) -> str:
    """Get commission notes for a project."""
    query = "SELECT commission_notes FROM commissions WHERE project_id = :project_id"
    results = execute_query(query, {"project_id": project_id})
    if results and results[0].get("commission_notes"):
        return results[0]["commission_notes"]
    return ""


def get_production_logistics(project_id: str) -> dict:
    """Get production logistics data for a project."""
    query = """
        SELECT target_installation_date, production_status, 
               paint_samples_approved, site_measurements_verified
        FROM production_logistics
        WHERE project_id = :project_id
    """
    results = execute_query(query, {"project_id": project_id})
    if results:
        return results[0]
    return {
        "target_installation_date": None,
        "production_status": "waiting",
        "paint_samples_approved": False,
        "site_measurements_verified": False
    }


def save_production_logistics(project_id: str, target_date=None, status: str = None, 
                              paint_approved: bool = None, measurements_verified: bool = None) -> bool:
    """Save production logistics data."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                existing = execute_query(
                    "SELECT id FROM production_logistics WHERE project_id = :project_id",
                    {"project_id": project_id}
                )
                
                if existing:
                    updates = []
                    params = {"project_id": project_id}
                    
                    if target_date is not None:
                        updates.append("target_installation_date = :target_date")
                        params["target_date"] = target_date
                    if status is not None:
                        updates.append("production_status = :status")
                        params["status"] = status
                    if paint_approved is not None:
                        updates.append("paint_samples_approved = :paint")
                        params["paint"] = paint_approved
                    if measurements_verified is not None:
                        updates.append("site_measurements_verified = :measurements")
                        params["measurements"] = measurements_verified
                    
                    updates.append("updated_at = NOW()")
                    
                    conn.execute(
                        text(f"UPDATE production_logistics SET {', '.join(updates)} WHERE project_id = :project_id"),
                        params
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO production_logistics 
                            (project_id, target_installation_date, production_status, 
                             paint_samples_approved, site_measurements_verified, created_at)
                            VALUES (:project_id, :target_date, :status, :paint, :measurements, NOW())
                        """),
                        {
                            "project_id": project_id,
                            "target_date": target_date,
                            "status": status or "waiting",
                            "paint": paint_approved or False,
                            "measurements": measurements_verified or False
                        }
                    )
                
                trans.commit()
                return True
            except Exception as e:
                trans.rollback()
                print(f"Error saving production logistics: {e}")
                return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def get_deposit_received_date(project_id: str):
    """Get the deposit received date for pulse check calculations."""
    query = "SELECT deposit_received_date FROM commissions WHERE project_id = :project_id"
    results = execute_query(query, {"project_id": project_id})
    if results and results[0].get("deposit_received_date"):
        return results[0]["deposit_received_date"]
    return None


def get_commission_data(project_id: str) -> dict:
    """Get full commission data for a project."""
    query = """
        SELECT total_value, deposit_amount, deposit_received_date, 
               commission_notes, final_payment_date, total_amount_received
        FROM commissions
        WHERE project_id = :project_id
    """
    results = execute_query(query, {"project_id": project_id})
    if results:
        return results[0]
    return {
        "total_value": 0,
        "deposit_amount": 0,
        "deposit_received_date": None,
        "commission_notes": "",
        "final_payment_date": None,
        "total_amount_received": 0
    }


def close_project_with_final_payment(project_id: str, total_amount_received: float) -> bool:
    """Close project, update status to COMPLETED, and record final payment.
    Preserves existing commission data (total_value, deposit_amount, etc.).
    
    BENTLEY STARK FIX: If installation_date is in the future, keep status as 'Confirmed'
    instead of auto-completing - project stays active on Dashboard Radar."""
    from datetime import date
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                # Check if installation date is in the future (Bentley Stark Fix)
                logistics = conn.execute(
                    text("SELECT target_installation_date FROM production_logistics WHERE project_id = :project_id"),
                    {"project_id": project_id}
                ).fetchone()
                
                install_date = logistics[0] if logistics else None
                today = today_mountain()
                
                # If installation is in the future, don't mark as completed (uses Mountain Time)
                if install_date and install_date > today:
                    new_status = 'Confirmed'
                else:
                    new_status = 'completed'
                
                conn.execute(
                    text("""
                        UPDATE projects 
                        SET status = :new_status, updated_at = NOW(), status_updated_at = NOW()
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {"project_id": project_id, "tenant_id": TENANT_ID, "new_status": new_status}
                )
                
                existing = conn.execute(
                    text("SELECT id FROM commissions WHERE project_id = :project_id"),
                    {"project_id": project_id}
                ).fetchone()
                
                if existing:
                    conn.execute(
                        text("""
                            UPDATE commissions 
                            SET total_amount_received = :amount,
                                final_payment_date = :payment_date,
                                updated_at = NOW()
                            WHERE project_id = :project_id
                        """),
                        {
                            "project_id": project_id,
                            "amount": total_amount_received,
                            "payment_date": today_mountain()
                        }
                    )
                else:
                    conn.execute(
                        text("""
                            INSERT INTO commissions (project_id, total_value, total_amount_received, final_payment_date, created_at)
                            VALUES (:project_id, :total_value, :amount, :payment_date, NOW())
                        """),
                        {
                            "project_id": project_id,
                            "total_value": total_amount_received,
                            "amount": total_amount_received,
                            "payment_date": today_mountain()
                        }
                    )
                
                trans.commit()
                return True
            except Exception as e:
                trans.rollback()
                print(f"Error closing project: {e}")
                return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False


def get_project_proposals(project_id: str) -> list:
    """Get all proposals for a project."""
    engine = get_engine()
    if engine is None:
        return []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT id, file_name, file_path, is_primary, 
                           scanned_total, scanned_deposit, scan_notes, uploaded_at
                    FROM project_proposals
                    WHERE project_id = :project_id
                    ORDER BY is_primary DESC, uploaded_at DESC
                """),
                {"project_id": project_id}
            )
            rows = result.fetchall()
            return [dict(zip(result.keys(), row)) for row in rows]
    except Exception as e:
        print(f"Error fetching proposals: {e}")
        return []


def save_project_proposal(project_id: str, file_name: str, file_path: str, 
                          scanned_total: float = None, scanned_deposit: float = None,
                          scan_notes: str = None, is_primary: bool = False) -> tuple:
    """Save a new proposal for a project. Returns (proposal_id, error)."""
    engine = get_engine()
    if engine is None:
        return None, "Database connection not available"
    
    try:
        with engine.begin() as conn:
            if is_primary:
                conn.execute(
                    text("UPDATE project_proposals SET is_primary = FALSE WHERE project_id = :project_id"),
                    {"project_id": project_id}
                )
            
            result = conn.execute(
                text("""
                    INSERT INTO project_proposals 
                    (project_id, file_name, file_path, is_primary, scanned_total, scanned_deposit, scan_notes)
                    VALUES (:project_id, :file_name, :file_path, :is_primary, :scanned_total, :scanned_deposit, :scan_notes)
                    RETURNING id
                """),
                {
                    "project_id": project_id,
                    "file_name": file_name,
                    "file_path": file_path,
                    "is_primary": is_primary,
                    "scanned_total": scanned_total,
                    "scanned_deposit": scanned_deposit,
                    "scan_notes": scan_notes
                }
            )
            proposal_id = result.fetchone()[0]
            
            if is_primary and (scanned_total or scanned_deposit):
                conn.execute(
                    text("""
                        UPDATE projects 
                        SET estimated_value = COALESCE(:total, estimated_value),
                            deposit_amount = COALESCE(:deposit, deposit_amount),
                            value_source = 'validated',
                            updated_at = NOW()
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {
                        "total": scanned_total,
                        "deposit": scanned_deposit,
                        "project_id": project_id,
                        "tenant_id": TENANT_ID
                    }
                )
            
            return str(proposal_id), None
    except Exception as e:
        print(f"Error saving proposal: {e}")
        return None, str(e)


def set_proposal_as_primary(proposal_id: str, project_id: str) -> tuple:
    """Set a proposal as primary and update project values. Returns (success, error)."""
    engine = get_engine()
    if engine is None:
        return False, "Database connection not available"
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE project_proposals SET is_primary = FALSE WHERE project_id = :project_id"),
                {"project_id": project_id}
            )
            
            conn.execute(
                text("UPDATE project_proposals SET is_primary = TRUE WHERE id = :proposal_id"),
                {"proposal_id": proposal_id}
            )
            
            result = conn.execute(
                text("SELECT scanned_total, scanned_deposit FROM project_proposals WHERE id = :proposal_id"),
                {"proposal_id": proposal_id}
            )
            row = result.fetchone()
            
            if row and (row[0] or row[1]):
                conn.execute(
                    text("""
                        UPDATE projects 
                        SET estimated_value = COALESCE(:total, estimated_value),
                            deposit_amount = COALESCE(:deposit, deposit_amount),
                            value_source = 'validated',
                            updated_at = NOW()
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {
                        "total": row[0],
                        "deposit": row[1],
                        "project_id": project_id,
                        "tenant_id": TENANT_ID
                    }
                )
            
            return True, None
    except Exception as e:
        print(f"Error setting primary proposal: {e}")
        return False, str(e)


def update_proposal_scan_results(proposal_id: str, scanned_total: float, 
                                  scanned_deposit: float, scan_notes: str = None) -> bool:
    """Update scan results for a proposal. If proposal is primary, also update the project."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE project_proposals 
                    SET scanned_total = :total, scanned_deposit = :deposit, scan_notes = :notes
                    WHERE id = :proposal_id
                """),
                {
                    "proposal_id": proposal_id,
                    "total": scanned_total,
                    "deposit": scanned_deposit,
                    "notes": scan_notes
                }
            )
            
            result = conn.execute(
                text("SELECT project_id, is_primary FROM project_proposals WHERE id = :proposal_id"),
                {"proposal_id": proposal_id}
            )
            row = result.fetchone()
            
            if row and row[1]:
                project_id = row[0]
                conn.execute(
                    text("""
                        UPDATE projects 
                        SET estimated_value = COALESCE(:total, estimated_value),
                            deposit_amount = COALESCE(:deposit, deposit_amount),
                            value_source = 'validated',
                            updated_at = NOW()
                        WHERE id = :project_id AND tenant_id = :tenant_id
                    """),
                    {
                        "total": scanned_total,
                        "deposit": scanned_deposit,
                        "project_id": str(project_id),
                        "tenant_id": TENANT_ID
                    }
                )
            
            return True
    except Exception as e:
        print(f"Error updating proposal scan: {e}")
        return False


def delete_proposal(proposal_id: str) -> bool:
    """Delete a proposal."""
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM project_proposals WHERE id = :proposal_id"),
                {"proposal_id": proposal_id}
            )
            return True
    except Exception as e:
        print(f"Error deleting proposal: {e}")
        return False


def update_action_status(project_id: str, pending_action: bool, action_note: str = None, action_due_date = None) -> bool:
    """Update action status, note, and due date for a project."""
    query = """
        UPDATE projects 
        SET pending_action = :pending_action, action_note = :action_note, 
            action_due_date = :action_due_date,
            last_touched = NOW(), updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "pending_action": pending_action,
        "action_note": action_note,
        "action_due_date": action_due_date,
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def add_project_history(project_id: str, entry_type: str, content: str) -> bool:
    """Add an entry to the project history table with Mountain Time timestamp."""
    from services.timezone_utils import now_mountain
    
    engine = get_engine()
    if engine is None:
        return False
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO project_history (project_id, entry_type, content, created_at)
                    VALUES (:project_id, :entry_type, :content, :created_at)
                """),
                {
                    "project_id": project_id,
                    "entry_type": entry_type,
                    "content": content,
                    "created_at": now_mountain()
                }
            )
            return True
    except Exception as e:
        print(f"Error adding history: {e}")
        return False


def get_project_history(project_id: str, limit: int = 50) -> list:
    """Get history entries for a project."""
    query = """
        SELECT id, entry_type, content, created_at
        FROM project_history
        WHERE project_id = :project_id
        ORDER BY created_at DESC
        LIMIT :limit
    """
    return execute_query(query, {"project_id": project_id, "limit": limit})


def clear_action_status(project_id: str) -> bool:
    """Clear the pending_action flag, action_note, and action_due_date (mark as done)."""
    query = """
        UPDATE projects 
        SET pending_action = FALSE, action_note = NULL, action_due_date = NULL, 
            last_touched = NOW(), updated_at = NOW()
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "project_id": project_id,
        "tenant_id": TENANT_ID
    })


def get_action_items() -> list:
    """Get all projects with pending actions for the Action Hub, sorted by due date."""
    query = """
        SELECT id, client_name, status, action_note, last_touched, pending_action, action_due_date
        FROM projects
        WHERE tenant_id = :tenant_id AND is_active_v3 = TRUE AND pending_action = TRUE
          AND LOWER(status) NOT IN ('archived', 'closed - won', 'closed - lost')
        ORDER BY action_due_date ASC NULLS LAST, last_touched ASC NULLS FIRST
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def get_urgent_items() -> list:
    """Get confirmed projects not yet submitted for pay period (URGENT)."""
    query = """
        SELECT id, client_name, status, action_note, last_touched, deposit_received_date, action_due_date
        FROM projects
        WHERE tenant_id = :tenant_id 
          AND is_active_v3 = TRUE 
          AND status = 'CONFIRMED'
          AND deposit_received_date IS NOT NULL
          AND LOWER(status) NOT IN ('archived', 'closed - won', 'closed - lost')
        ORDER BY deposit_received_date ASC
    """
    return execute_query(query, {"tenant_id": TENANT_ID})


def calculate_business_days(from_date, to_date) -> int:
    """Calculate business days (Mon-Fri) between two dates. The Weekend Shield."""
    from datetime import timedelta
    if from_date is None or to_date is None:
        return 0
    
    if hasattr(from_date, 'date'):
        from_date = from_date.date()
    if hasattr(to_date, 'date'):
        to_date = to_date.date()
    
    business_days = 0
    current = from_date
    while current < to_date:
        if current.weekday() < 5:  # Mon=0, Fri=4
            business_days += 1
        current += timedelta(days=1)
    return business_days


def get_system_alerts() -> list:
    """Get automated nudge triggers based on business days elapsed since status change.
    
    Nudge Triggers (🔴 URGENT):
    - Matt: If status is 'Design' and > 3 business days have passed
    - Bruno: If status is 'Quoting' and > 1 business day has passed  
    - Customer: If status is 'Awaiting Deposit' and > 3 business days have passed
    
    Respects snooze_until - items snoozed until that timestamp are hidden."""
    from datetime import datetime
    
    query = """
        SELECT id, client_name, status, status_updated_at, snooze_until
        FROM projects
        WHERE tenant_id = :tenant_id 
          AND is_active_v3 = TRUE 
          AND status IN ('Design', 'Quoting', 'Awaiting Deposit')
          AND status_updated_at IS NOT NULL
          AND (snooze_until IS NULL OR snooze_until < NOW())
        ORDER BY status_updated_at ASC
    """
    projects = execute_query(query, {"tenant_id": TENANT_ID})
    
    alerts = []
    today = now_mountain()
    
    for project in projects:
        status = (project.get("status") or "").lower().replace(" ", "_")
        status_updated = project.get("status_updated_at")
        
        if not status_updated:
            continue
        
        business_days = calculate_business_days(status_updated, today)
        
        alert = None
        if status == "design" and business_days > 3:
            alert = {
                "id": project.get("id"),
                "client_name": project.get("client_name"),
                "status": project.get("status"),
                "alert_type": "matt_nudge",
                "message": f"Matt hasn't responded in {business_days} business days",
                "business_days": business_days,
                "icon": "🎨"
            }
        elif status == "quoting" and business_days > 1:
            alert = {
                "id": project.get("id"),
                "client_name": project.get("client_name"),
                "status": project.get("status"),
                "alert_type": "bruno_nudge",
                "message": f"Bruno hasn't responded in {business_days} business days",
                "business_days": business_days,
                "icon": "💰"
            }
        elif status == "awaiting_deposit" and business_days > 3:
            alert = {
                "id": project.get("id"),
                "client_name": project.get("client_name"),
                "status": project.get("status"),
                "alert_type": "customer_nudge",
                "message": f"Customer hasn't paid deposit in {business_days} business days",
                "business_days": business_days,
                "icon": "👤"
            }
        
        if alert:
            alerts.append(alert)
    
    return alerts


def snooze_project_alert(project_id: str, hours: int = 24) -> bool:
    """Snooze a project's system alert for the specified number of hours (Mountain Time)."""
    from datetime import timedelta
    
    snooze_until_time = now_mountain() + timedelta(hours=hours)
    
    query = """
        UPDATE projects 
        SET snooze_until = :snooze_until
        WHERE id = :project_id AND tenant_id = :tenant_id
    """
    return execute_update(query, {
        "project_id": project_id, 
        "tenant_id": TENANT_ID,
        "snooze_until": snooze_until_time
    })


def get_victory_lap_items() -> list:
    """Get projects that were installed yesterday for the Victory Lap - thank you/review request.
    
    Logic: If target_installation_date (from production_logistics) = yesterday AND status != 'Completed', 
    show in URGENT section.
    Label: '🏆 Victory Lap: [Project Name] was installed yesterday. Send thank you / Request review!'
    """
    query = """
        SELECT p.id, p.client_name, p.status, pl.target_installation_date,
               (SELECT email FROM contacts WHERE project_id = p.id AND is_primary = TRUE LIMIT 1) as customer_email
        FROM projects p
        LEFT JOIN production_logistics pl ON p.id = pl.project_id
        WHERE p.tenant_id = :tenant_id 
          AND p.is_active_v3 = TRUE 
          AND pl.target_installation_date = CURRENT_DATE - INTERVAL '1 day'
          AND LOWER(p.status) NOT IN ('completed', 'cancelled', 'lost', 'archived', 'closed - won', 'closed - lost')
        ORDER BY p.client_name ASC
    """
    return execute_query(query, {"tenant_id": TENANT_ID})
