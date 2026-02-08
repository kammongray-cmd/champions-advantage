import streamlit as st
from services.database_manager import get_status_badge
from components.icons import get_icon

KB_GREEN = "#39FF14"
KB_DARK = "#0a0a0a"
KB_CARD_BG = "#111111"
KB_BORDER = "#222222"
KB_TEXT = "#E5E5E5"
KB_MUTED = "#888888"


def render_project_tile(project: dict, key_prefix: str = "tile"):
    """
    Render unified project tile as one-button wrapper with flush horizontal Done.
    Entire tile is clickable. Max height ~0.9 inches for extreme vertical efficiency.
    
    Args:
        project: Dictionary containing project data
        key_prefix: Prefix for unique widget keys
    """
    from services.database_manager import clear_action_status
    
    project_id = str(project.get("id", ""))
    client_name = project.get("client_name", "Unknown Client")
    if len(client_name) > 18:
        client_name = client_name[:16] + ".."
    status = project.get("status", "pending")
    estimated_value = project.get("estimated_value", 0)
    value_source = project.get("value_source", "estimated")
    action_note = project.get("action_note", "")
    action_due_date = project.get("action_due_date")
    pending_action = project.get("pending_action", False)
    
    status_badge = get_status_badge(status)
    
    if estimated_value:
        if value_source == "validated":
            value_str = f"${float(estimated_value):,.0f}"
            value_color = KB_GREEN
        else:
            value_str = f"~${float(estimated_value):,.0f}"
            value_color = KB_MUTED
    else:
        value_str = ""
        value_color = KB_MUTED
    
    due_display = ""
    due_color = KB_MUTED
    if action_due_date:
        from datetime import date, datetime
        from services.timezone_utils import today_mountain
        
        today = today_mountain()
        if isinstance(action_due_date, date):
            due = action_due_date
        else:
            try:
                due = datetime.fromisoformat(str(action_due_date).replace('Z', '+00:00')).date()
            except:
                due = None
        
        if due:
            days_until = (due - today).days
            if days_until < 0:
                due_display = f"{abs(days_until)}d late"
                due_color = "#e74c3c"
            elif days_until == 0:
                due_display = "TODAY"
                due_color = "#e74c3c"
            elif days_until == 1:
                due_display = "Tmrw"
                due_color = "#f39c12"
            else:
                due_display = f"{days_until}d"
                due_color = KB_GREEN if days_until > 3 else "#f39c12"
    
    action_preview = ""
    if action_note:
        action_preview = action_note[:24] + ".." if len(action_note) > 24 else action_note
    
    info_right = f"{status_badge}"
    if value_str:
        info_right += f" {value_str}"
    if due_display:
        info_right += f" <span style='color:{due_color};font-weight:600;'>{due_display}</span>"
    
    if pending_action:
        col_tile, col_done = st.columns([5, 1])
        
        with col_tile:
            if st.button(
                client_name,
                key=f"{key_prefix}_{project_id}",
                use_container_width=True,
                help=action_preview or status
            ):
                st.session_state.current_project_id = project_id
                st.session_state.page = "project_detail"
                st.session_state.scroll_to_top = True
                st.rerun()
        
        with col_done:
            if st.button("OK", key=f"{key_prefix}_done_{project_id}", use_container_width=True, help="Done"):
                clear_action_status(project_id)
                st.toast("Done", icon="✅")
                st.rerun()
        
        st.markdown(
            f'<div style="color:{KB_MUTED};font-size:10px;margin:-10px 0 2px 4px;">'
            f'{action_preview} | {info_right}</div>',
            unsafe_allow_html=True
        )
    else:
        if st.button(
            client_name,
            key=f"{key_prefix}_{project_id}",
            use_container_width=True,
            help=action_preview or status
        ):
            st.session_state.current_project_id = project_id
            st.session_state.page = "project_detail"
            st.session_state.scroll_to_top = True
            st.rerun()
        
        st.markdown(
            f'<div style="color:{KB_MUTED};font-size:10px;margin:-10px 0 2px 4px;">'
            f'{action_preview or status} | {info_right}</div>',
            unsafe_allow_html=True
        )


def render_project_tile_compact(project: dict, key_prefix: str = "compact"):
    """
    Render a minimal project tile for lists.
    
    Args:
        project: Dictionary containing project data
        key_prefix: Prefix for unique widget keys
    """
    project_id = str(project.get("id", ""))
    client_name = project.get("client_name", "Unknown Client")
    status = project.get("status", "pending")
    estimated_value = project.get("estimated_value", 0)
    value_source = project.get("value_source", "estimated")
    
    status_badge = get_status_badge(status)
    
    if estimated_value:
        if value_source == "validated":
            value_str = f"${float(estimated_value):,.0f}"
            value_color = KB_GREEN
        else:
            value_str = f"~${float(estimated_value):,.0f}"
            value_color = KB_MUTED
    else:
        value_str = ""
        value_color = KB_MUTED
    
    return f"""
    <div style="
        background: {KB_CARD_BG};
        border: 1px solid {KB_BORDER};
        border-radius: 10px;
        padding: 8px 12px;
        margin: 2px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    ">
        <div style="flex: 1;">
            <span style="font-weight: 600; color: {KB_TEXT}; font-size: 13px;">{client_name}</span>
        </div>
        <div style="display: flex; align-items: center; gap: 6px;">
            <span style="font-size: 13px;">{status_badge}</span>
            <span style="color: {value_color}; font-size: 11px; font-weight: 500;">{value_str}</span>
        </div>
    </div>
    """
