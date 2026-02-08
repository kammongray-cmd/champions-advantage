import streamlit as st
from datetime import datetime, date, timedelta
from services.database_manager import get_promoted_projects, get_status_badge, get_new_leads, create_lead, get_action_items, get_urgent_items, clear_action_status, add_project_history, get_system_alerts, snooze_project_alert, get_victory_lap_items, update_lead_status, delete_project, get_archived_projects, restore_project, get_won_projects, get_lost_projects
from services.gemini_service import extract_lead_info
from components.project_tiles import render_project_tile
from components.icons import get_icon, icon_button_html
from services.timezone_utils import today_mountain, now_mountain

# KB Signs Brand Colors
KB_GREEN = "#39FF14"
KB_DARK = "#0a0a0a"
KB_CARD_BG = "#111111"
KB_BORDER = "#222222"
KB_TEXT = "#E5E5E5"
KB_MUTED = "#888888"


@st.dialog("Smart Intake")
def render_smart_intake_dialog():
    """Smart Intake popup dialog for manual lead entry with Gemini extraction."""
    brain_icon = get_icon("brain", KB_GREEN, 18)
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border-radius: 12px;
            padding: 16px;
            margin: 0 0 12px 0;
            border: 1px solid {KB_GREEN};
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                {brain_icon}
                <span style="color: {KB_GREEN}; font-size: 15px; font-weight: 600;">AI-Powered Extraction</span>
            </div>
            <p style="color: {KB_MUTED}; margin: 0; font-size: 13px;">Paste text from emails, voicemails, or notes</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    intake_key = "dialog_intake_text"
    extracted_key = "dialog_extracted_lead"
    
    raw_text = st.text_area(
        "Paste lead info here",
        height=100,
        key=intake_key,
        placeholder="Example: Got a call from John Smith at 801-555-1234. He needs a new sign for his restaurant."
    )
    
    if st.button("Extract with AI", type="primary", use_container_width=True, disabled=not raw_text):
        if raw_text:
            with st.spinner("Extracting..."):
                extracted = extract_lead_info(raw_text)
                st.session_state[extracted_key] = extracted
                if extracted.get("error"):
                    st.warning(f"Note: {extracted['error']}")
    
    if extracted_key in st.session_state and st.session_state[extracted_key]:
        extracted = st.session_state[extracted_key]
        
        st.markdown(
            f'<p style="color: {KB_TEXT}; font-size: 14px; margin: 12px 0 8px 0; font-weight: 600;">Review & Edit:</p>',
            unsafe_allow_html=True
        )
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            lead_name = st.text_input("Name", value=extracted.get("name", ""), key="intake_name")
            lead_phone = st.text_input("Phone", value=extracted.get("phone", ""), key="intake_phone")
            lead_site_address = st.text_input("Site Address", value=extracted.get("site_address", ""), key="intake_site_address")
        
        with col_b:
            lead_email = st.text_input("Email", value=extracted.get("email", ""), key="intake_email")
            lead_notes = st.text_area("Notes", value=extracted.get("notes", ""), height=100, key="intake_notes")
        
        col_save, col_clear = st.columns(2)
        
        with col_save:
            if st.button("Save Lead", type="primary", use_container_width=True):
                if lead_name or lead_phone or lead_email:
                    success = create_lead(lead_name, lead_phone, lead_email, lead_notes, source="smart_intake", site_address=lead_site_address)
                    if success:
                        st.toast(f"Lead saved: {lead_name or lead_email or lead_phone}", icon="✅")
                        st.session_state[extracted_key] = None
                        st.rerun()
                    else:
                        st.error("Failed to save lead")
                else:
                    st.warning("Please provide at least a name, phone, or email")
        
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state[extracted_key] = None
                st.rerun()


@st.dialog("New Lead Alert")
def render_hot_lead_popup(lead: dict):
    """Hot Lead popup triggered on login/refresh when new leads exist."""
    from services.email_service import send_email, is_test_mode
    
    lead_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "Unknown Lead"
    lead_email = lead.get("email", "") or ""
    lead_phone = lead.get("phone", "") or ""
    lead_notes = lead.get("notes", "") or ""
    
    flame_icon = get_icon("flame", "#e74c3c", 20)
    phone_icon = get_icon("phone", KB_MUTED, 14)
    mail_icon = get_icon("mail", KB_MUTED, 14)
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid #e74c3c;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            text-align: center;
        ">
            <div style="display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 6px;">
                {flame_icon}
                <span style="color: #e74c3c; font-size: 20px; font-weight: 600;">{lead_name}</span>
            </div>
            <p style="color: {KB_MUTED}; margin: 0; font-size: 14px;">is waiting for a response</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    st.markdown(
        f'''
        <div style="background: {KB_CARD_BG}; border: 1px solid {KB_BORDER}; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
            <p style="color: {KB_TEXT}; margin: 0 0 6px 0; font-size: 13px; font-weight: 600;">Lead Details:</p>
            <p style="color: {KB_MUTED}; margin: 3px 0; font-size: 13px;">Phone: {lead_phone or 'Not provided'}</p>
            <p style="color: {KB_MUTED}; margin: 3px 0; font-size: 13px;">Email: {lead_email or 'Not provided'}</p>
            <p style="color: #666; margin: 6px 0 0 0; font-size: 12px;">{lead_notes[:80] + '...' if len(lead_notes) > 80 else lead_notes or 'No notes'}</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    st.markdown(f'<p style="color: {KB_TEXT}; font-size: 13px; font-weight: 600; margin-bottom: 8px;">Quick Actions:</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Email", type="primary", use_container_width=True, key=f"popup_email_{lead_id}"):
            st.session_state[f"show_lead_email_dialog_{lead_id}"] = True
            st.session_state[f"lead_cache_{lead_id}"] = lead
            st.session_state["hot_lead_dismissed"] = True
            st.rerun()
    
    with col2:
        if st.button("Text", use_container_width=True, key=f"popup_text_{lead_id}"):
            st.session_state[f"show_lead_text_dialog_{lead_id}"] = True
            st.session_state[f"lead_cache_{lead_id}"] = lead
            st.session_state["hot_lead_dismissed"] = True
            st.rerun()
    
    with col3:
        if st.button("Call", use_container_width=True, key=f"popup_call_{lead_id}"):
            update_lead_status(lead_id, "Block A")
            add_project_history(lead_id, "LEAD_CALLED", f"Called {lead_name} at {lead_phone}")
            st.toast(f"{lead_name} moved to Block A", icon="✅")
            st.session_state["hot_lead_dismissed"] = True
            st.rerun()
    
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    
    if st.button("Not Now", use_container_width=True, key=f"popup_dismiss_{lead_id}"):
        st.session_state["hot_lead_dismissed"] = True
        st.rerun()


@st.dialog("Draft Email")
def render_lead_email_dialog(lead: dict):
    """Draft & Review email dialog for leads with voice dictation support."""
    from services.email_service import send_email, is_test_mode
    
    lead_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "there"
    lead_email = lead.get("email", "") or ""
    sender_name = "Kam"
    
    default_subject = f"Following up on your sign project inquiry - {lead_name}"
    default_body = f"""Hi {lead_name.split()[0] if lead_name and lead_name != 'there' else 'there'},

This is {sender_name} from KB Signs. I saw your request and wanted to reach out. Are you available for a quick call or text to discuss your project?

Looking forward to hearing from you!

{sender_name}
KB Signs"""
    
    mail_icon = get_icon("mail", KB_GREEN, 16)
    st.markdown(
        f'''
        <div style="background: {KB_CARD_BG}; border: 1px solid {KB_GREEN}; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                {mail_icon}
                <span style="color: {KB_GREEN}; font-size: 14px; font-weight: 600;">Draft & Review</span>
                <span style="color: {KB_MUTED}; font-size: 12px;">- Edit before sending</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    recipient = st.text_input("To:", value=lead_email, key=f"lead_email_to_{lead_id}")
    subject = st.text_input("Subject:", value=default_subject, key=f"lead_email_subject_{lead_id}")
    
    body_key = f"lead_email_body_{lead_id}"
    if body_key not in st.session_state:
        st.session_state[body_key] = default_body
    
    col_body, col_mic = st.columns([9, 1])
    with col_body:
        st.markdown('<p style="color: #E5E5E5; font-size: 12px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_voice_dictation_inline(lead_id, body_key, "lead_email")
    
    body = st.text_area("", height=180, key=body_key, label_visibility="collapsed")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Email", type="primary", use_container_width=True, key=f"lead_send_email_{lead_id}"):
            if not recipient:
                st.error("Please enter a recipient email")
            else:
                success, message = send_email(recipient, subject, body)
                if success:
                    update_lead_status(lead_id, "Block A")
                    add_project_history(lead_id, "EMAIL_SENT", f"Sent outreach email to {recipient}")
                    
                    if is_test_mode():
                        st.toast("Email sent (Test mode) - Moved to Block A", icon="✅")
                    else:
                        st.toast(f"Email sent to {recipient}", icon="✅")
                    
                    st.session_state[f"show_lead_email_dialog_{lead_id}"] = False
                    st.rerun()
                else:
                    st.error(f"Error: {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"lead_cancel_email_{lead_id}"):
            st.session_state[f"show_lead_email_dialog_{lead_id}"] = False
            st.rerun()


@st.dialog("Draft Text")
def render_lead_text_dialog(lead: dict):
    """Draft & Review text message dialog for leads with voice dictation support."""
    
    lead_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "there"
    lead_phone = lead.get("phone", "") or ""
    sender_name = "Kam"
    
    default_message = f"Hi {lead_name.split()[0] if lead_name and lead_name != 'there' else 'there'}, this is {sender_name} from KB Signs. I saw your request and wanted to reach out. Are you available for a quick call to discuss your project?"
    
    msg_icon = get_icon("message", KB_GREEN, 16)
    st.markdown(
        f'''
        <div style="background: {KB_CARD_BG}; border: 1px solid {KB_GREEN}; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                {msg_icon}
                <span style="color: {KB_GREEN}; font-size: 14px; font-weight: 600;">Draft Text Message</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    phone = st.text_input("To (Phone):", value=lead_phone, key=f"lead_text_phone_{lead_id}")
    
    body_key = f"lead_text_body_{lead_id}"
    if body_key not in st.session_state:
        st.session_state[body_key] = default_message
    
    col_body, col_mic = st.columns([9, 1])
    with col_body:
        st.markdown(f'<p style="color: {KB_TEXT}; font-size: 12px; margin-bottom: 4px;">Message:</p>', unsafe_allow_html=True)
    with col_mic:
        render_voice_dictation_inline(lead_id, body_key, "lead_text")
    
    message = st.text_area("", height=120, key=body_key, label_visibility="collapsed")
    
    st.markdown(
        f'''
        <div style="background: {KB_CARD_BG}; border: 1px solid {KB_BORDER}; border-radius: 8px; padding: 10px; margin: 10px 0;">
            <p style="color: {KB_MUTED}; margin: 0; font-size: 12px;">Copy text and send via your phone. Click "SMS Sent" when done.</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("SMS Sent", type="primary", use_container_width=True, key=f"lead_text_sent_{lead_id}"):
            update_lead_status(lead_id, "Block A")
            add_project_history(lead_id, "TEXT_SENT", f"Sent text message to {phone}")
            st.toast(f"{lead_name} moved to Block A", icon="✅")
            st.session_state[f"show_lead_text_dialog_{lead_id}"] = False
            st.rerun()
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"lead_cancel_text_{lead_id}"):
            st.session_state[f"show_lead_text_dialog_{lead_id}"] = False
            st.rerun()


def render_hot_leads_section():
    """Render the HOT LEADS section at the top of Marching Orders.
    
    UNIFIED WORKFLOW: Shows projects with status='New'. When contacted,
    they flip to 'Block A' and disappear from this section.
    """
    new_leads = get_new_leads()
    flame_icon = get_icon("flame", "#e74c3c", 18)
    
    if new_leads:
        st.markdown(
            f'''
            <div style="
                background: {KB_CARD_BG};
                border: 1px solid #e74c3c;
                border-radius: 12px;
                padding: 12px 16px;
                margin-bottom: 12px;
            ">
                <div style="display: flex; align-items: center; gap: 8px;">
                    {flame_icon}
                    <span style="color: #e74c3c; font-weight: 600; font-size: 14px;">HOT LEADS</span>
                    <span style="background: #e74c3c; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600;">{len(new_leads)}</span>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        for lead in new_leads:
            render_hot_lead_card(lead)
    else:
        st.markdown(
            f'''
            <div style="
                background: {KB_CARD_BG};
                border: 1px dashed {KB_BORDER};
                border-radius: 12px;
                padding: 14px;
                margin-bottom: 12px;
                text-align: center;
            ">
                <span style="color: {KB_MUTED}; font-size: 13px;">No hot leads waiting</span>
            </div>
            ''',
            unsafe_allow_html=True
        )


def render_hot_lead_card(lead: dict):
    """Render integrated hot lead card - click name to open, horizontal action row.
    
    UNIFIED WORKFLOW: Click lead name to navigate to project_detail.
    Contact actions flip status from 'New' to 'Block A'.
    """
    project_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "Unknown"
    phone = lead.get("phone", "")
    email = lead.get("email", "")
    
    contact_preview = phone or email or ""
    if len(contact_preview) > 20:
        contact_preview = contact_preview[:18] + ".."
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid {KB_BORDER};
            border-radius: 10px;
            padding: 8px 10px 4px 10px;
            margin-bottom: 4px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: {KB_MUTED}; font-size: 10px;">{contact_preview}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    cols = st.columns([3, 1, 1, 1, 1])
    
    with cols[0]:
        if st.button(lead_name, key=f"hl_nav_{project_id}", use_container_width=True):
            st.session_state.page = "project_detail"
            st.session_state.current_project_id = project_id
            st.session_state.scroll_to_top = True
            st.rerun()
    
    with cols[1]:
        if st.button("Call", key=f"hl_call_{project_id}", help="Mark as Called", use_container_width=True):
            update_lead_status(project_id, "Block A")
            add_project_history(project_id, "LEAD_CALLED", f"Called {lead_name}")
            st.toast(f"{lead_name} moved", icon="✅")
            st.rerun()
    
    with cols[2]:
        if st.button("Txt", key=f"hl_text_{project_id}", help="Draft Text", use_container_width=True):
            st.session_state[f"show_lead_text_dialog_{project_id}"] = True
            st.session_state[f"lead_cache_{project_id}"] = lead
            st.rerun()
    
    with cols[3]:
        if st.button("Mail", key=f"hl_email_{project_id}", help="Draft Email", use_container_width=True):
            st.session_state[f"show_lead_email_dialog_{project_id}"] = True
            st.session_state[f"lead_cache_{project_id}"] = lead
            st.rerun()
    
    with cols[4]:
        confirm_key = f"confirm_delete_lead_{project_id}"
        if st.session_state.get(confirm_key):
            if st.button("Yes", key=f"hl_confirm_del_{project_id}", type="primary", use_container_width=True):
                success, _ = delete_project(project_id)
                if success:
                    st.toast("Archived", icon="✅")
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            if st.button("Del", key=f"hl_delete_{project_id}", help="Archive", use_container_width=True):
                st.session_state[confirm_key] = True
                st.rerun()


def render_hot_lead_row(lead: dict):
    """Legacy hot lead row - redirects to new card style."""
    render_hot_lead_card(lead)


def render_action_hub():
    """Render Today's Marching Orders - the Action Hub with 48-hour focus and 3-tier categorization."""
    urgent_items = get_urgent_items()
    action_items = get_action_items()
    system_alerts = get_system_alerts()
    victory_lap_items = get_victory_lap_items()
    
    today = today_mountain()
    tomorrow = today + timedelta(days=1)
    day_5 = today + timedelta(days=5)
    
    red_items = []
    yellow_items = []
    grey_items = []
    
    for item in action_items:
        due_date = item.get("action_due_date")
        action_note = item.get("action_note", "") or ""
        
        if due_date:
            if isinstance(due_date, date):
                due = due_date
            else:
                try:
                    due = datetime.fromisoformat(str(due_date).replace('Z', '+00:00')).date()
                except:
                    due = None
            
            if due:
                if due <= tomorrow:
                    red_items.append(item)
                elif due <= day_5:
                    yellow_items.append(item)
                else:
                    yellow_items.append(item)
        else:
            if action_note.strip():
                grey_items.append(item)
    
    for item in urgent_items:
        item_id = str(item.get("id", ""))
        if not any(str(r.get("id", "")) == item_id for r in red_items):
            red_items.append(item)
    
    check_icon = get_icon("check", KB_GREEN, 18)
    if not red_items and not yellow_items and not grey_items:
        st.markdown(
            f'''
            <div style="
                background: {KB_CARD_BG};
                border: 1px solid {KB_GREEN};
                border-radius: 12px;
                padding: 16px;
                margin: 12px 0;
                text-align: center;
            ">
                <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                    {check_icon}
                    <span style="color: {KB_GREEN}; font-size: 15px; font-weight: 500;">All clear! Pipeline moving smooth.</span>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        return
    
    rocket_icon = get_icon("rocket", KB_GREEN, 18)
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid {KB_GREEN};
            border-radius: 12px;
            padding: 10px 14px;
            margin: 8px 0;
        ">
            <span style="color: {KB_GREEN}; font-weight: 600; font-size: 15px;">Today's Marching Orders</span>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    # HOT LEADS section - NEW leads at very top of Marching Orders
    render_hot_leads_section()
    
    if system_alerts:
        with st.expander(f"ALERTS ({len(system_alerts)}) - Business Day Nudges", expanded=True):
            for alert in system_alerts:
                render_system_alert_row(alert)
    
    if victory_lap_items:
        with st.expander(f"VICTORY LAP ({len(victory_lap_items)}) - Installed Yesterday", expanded=True):
            for item in victory_lap_items:
                render_victory_lap_row(item)
    
    if red_items:
        with st.expander(f"URGENT ({len(red_items)}) - Today/Tomorrow/Overdue", expanded=True):
            for item in red_items:
                render_action_row(item, urgency_level="red")
    
    if yellow_items:
        with st.expander(f"UPCOMING ({len(yellow_items)}) - Next 3-5 days", expanded=False):
            for item in yellow_items:
                render_action_row(item, urgency_level="yellow")
    
    if grey_items:
        with st.expander(f"PENDING ({len(grey_items)}) - When I get to it", expanded=False):
            for item in grey_items:
                render_action_row(item, urgency_level="grey")


def render_action_row(item, urgency_level="yellow"):
    """Render a single action row with Done button and countdown display."""
    project_id = str(item.get("id", ""))
    client_name = item.get("client_name", "Unknown")
    action_note = item.get("action_note", "") or "No action note"
    action_due_date = item.get("action_due_date")
    
    today = today_mountain()
    countdown_text = ""
    countdown_color = KB_MUTED
    
    if action_due_date:
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
                countdown_text = f"{abs(days_until)}d LATE"
                countdown_color = "#e74c3c"
            elif days_until == 0:
                countdown_text = "TODAY"
                countdown_color = "#e74c3c"
            elif days_until == 1:
                countdown_text = "Tomorrow"
                countdown_color = "#f39c12"
            else:
                countdown_text = f"{days_until}d"
                countdown_color = KB_GREEN if days_until > 3 else "#f39c12"
    else:
        countdown_text = "No date"
        countdown_color = "#555"
    
    action_preview = action_note[:40] + "..." if len(action_note) > 40 else action_note
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid {KB_BORDER};
            border-radius: 10px;
            padding: 6px 10px;
            margin: 2px 0;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: {KB_MUTED}; font-size: 10px;">{action_preview}</span>
                <span style="color: {countdown_color}; font-size: 10px; font-weight: 600;">{countdown_text}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        if st.button(client_name, key=f"action_link_{project_id}", use_container_width=True):
            st.session_state.current_project_id = project_id
            st.session_state.page = "project_detail"
            st.rerun()
    
    with col2:
        if st.button("OK", key=f"done_{project_id}", help="Done"):
            if clear_action_status(project_id):
                add_project_history(project_id, "TASK_COMPLETED", f"Task completed: {action_note}")
                st.toast(f"Done!", icon="✅")
                st.rerun()


def render_system_alert_row(alert):
    """Render a system alert row with Snooze 24h button."""
    project_id = str(alert.get("id", ""))
    client_name = alert.get("client_name", "Unknown")
    message = alert.get("message", "")
    business_days = alert.get("business_days", 0)
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid #9b59b6;
            border-radius: 10px;
            padding: 6px 10px;
            margin: 2px 0;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #9b59b6; font-size: 10px;">{message}</span>
                <span style="color: #9b59b6; font-size: 10px; font-weight: 600;">{business_days}d</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        if st.button(client_name, key=f"alert_link_{project_id}", use_container_width=True):
            st.session_state.current_project_id = project_id
            st.session_state.page = "project_detail"
            st.rerun()
    
    with col2:
        if st.button("Snz", key=f"snooze_{project_id}", help="Snooze 24h"):
            if snooze_project_alert(project_id, 24):
                st.toast(f"Snoozed", icon="⏸️")
                st.rerun()


def render_victory_lap_row(item):
    """Render a Victory Lap row for projects installed yesterday."""
    project_id = str(item.get("id", ""))
    client_name = item.get("client_name", "Unknown")
    customer_email = item.get("customer_email", "")
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid #FFD700;
            border-radius: 10px;
            padding: 6px 10px;
            margin: 2px 0;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #FFD700; font-size: 10px;">Installed yesterday</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns([5, 2])
    
    with col1:
        if st.button(client_name, key=f"victory_link_{project_id}", use_container_width=True):
            st.session_state.current_project_id = project_id
            st.session_state.page = "project_detail"
            st.rerun()
    
    with col2:
        if st.button("Review", key=f"victory_draft_{project_id}", use_container_width=True, help="Send review request"):
            st.session_state[f"show_victory_dialog_{project_id}"] = True
            st.session_state[f"victory_client_name_{project_id}"] = client_name
            st.session_state[f"victory_email_{project_id}"] = customer_email
            st.rerun()
    
    # Show Victory Lap dialog if triggered
    if st.session_state.get(f"show_victory_dialog_{project_id}"):
        render_victory_lap_dialog(
            project_id=project_id,
            client_name=st.session_state.get(f"victory_client_name_{project_id}", client_name),
            customer_email=st.session_state.get(f"victory_email_{project_id}", customer_email)
        )


@st.dialog("Victory Lap - Thank You & Review Request")
def render_victory_lap_dialog(project_id: str, client_name: str, customer_email: str):
    """Victory Lap dialog with pre-filled thank you / review request template."""
    from services.email_service import send_email, is_test_mode
    from services.database_manager import add_project_touch, add_project_history, update_project_status
    
    review_link = "https://g.page/r/YOUR_GOOGLE_REVIEW_LINK"
    sender_name = "Kam"
    
    default_subject = f"Thank you for choosing KB Signs - {client_name}"
    default_body = f"""Hi {client_name.split()[0] if client_name else 'there'},

It was great working with you on the {client_name} install yesterday! We hope you love the new look.

If you have 30 seconds, would you mind leaving us a quick review here?
{review_link}

It helps us out a ton!

Thanks,
{sender_name}
KB Signs"""
    
    st.markdown(
        '''
        <div style="background: linear-gradient(145deg, #2d4a1a 0%, #1a3a0a 100%); border: 1px solid #28a745; border-radius: 12px; padding: 16px; margin-bottom: 16px;">
            <p style="color: #90EE90; margin: 0; font-size: 14px;"><strong>Victory Lap!</strong> Send a thank you and request a review from your happy customer.</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    # Editable recipient
    recipient = st.text_input("To:", value=customer_email, key=f"victory_to_{project_id}")
    
    # Editable subject with voice dictation
    st.markdown('<p style="color: #E5E5E5; font-size: 12px; margin-bottom: 4px;">Subject:</p>', unsafe_allow_html=True)
    subject = st.text_input("", value=default_subject, key=f"victory_subject_{project_id}", label_visibility="collapsed")
    
    # Initialize body in session state if not present
    body_key = f"victory_body_{project_id}"
    if body_key not in st.session_state:
        st.session_state[body_key] = default_body
    
    # Email body with voice dictation button
    col_body, col_mic = st.columns([9, 1])
    with col_body:
        st.markdown('<p style="color: #E5E5E5; font-size: 12px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_voice_dictation_inline(project_id, body_key, "victory")
    
    body = st.text_area(
        "",
        height=200,
        key=body_key,
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Email", type="primary", use_container_width=True, key=f"victory_send_{project_id}"):
            if not recipient:
                st.error("Please enter a recipient email")
            else:
                success, message = send_email(recipient, subject, body)
                
                if success:
                    add_project_touch(project_id, "email_sent", f"Victory Lap review request sent to {recipient}")
                    add_project_history(project_id, "EMAIL_SENT", f"[VICTORY LAP] Thank you / review request sent to {recipient}")
                    update_project_status(project_id, "Completed")
                    add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Project completed after Victory Lap email")
                    
                    if is_test_mode():
                        st.toast("Victory Lap sent (Test mode)", icon="✅")
                    else:
                        st.toast(f"Victory Lap sent to {recipient}", icon="✅")
                    
                    st.session_state[f"show_victory_dialog_{project_id}"] = False
                    st.rerun()
                else:
                    st.error(f"Error: {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"victory_cancel_{project_id}"):
            st.session_state[f"show_victory_dialog_{project_id}"] = False
            st.rerun()


def render_voice_dictation_inline(project_id: str, target_key: str, dialog_type: str):
    """Render inline voice dictation button with visual feedback and proper Streamlit integration.
    
    Uses streamlit_js_eval with async promise pattern for reliable speech recognition.
    - Visual feedback: Mic changes to REC with "Recording..." text
    - Appends text (doesn't overwrite)
    - Console logs for debugging
    """
    import streamlit.components.v1 as components
    from streamlit_js_eval import streamlit_js_eval
    
    voice_key = f"voice_{dialog_type}_{project_id}"
    recording_key = f"recording_{dialog_type}_{project_id}"
    result_key = f"voice_result_{dialog_type}_{project_id}"
    error_key = f"voice_error_{dialog_type}_{project_id}"
    
    # Process any pending voice result
    if result_key in st.session_state and st.session_state[result_key]:
        result = st.session_state[result_key]
        st.session_state[result_key] = None
        st.session_state[recording_key] = False
        
        # Append to target text (don't overwrite)
        current = st.session_state.get(target_key, "")
        if current:
            st.session_state[target_key] = current + " " + result
        else:
            st.session_state[target_key] = result
        
        st.toast(f"Added: {result}", icon="✅")
        st.rerun()
    
    # Process any pending error
    if error_key in st.session_state and st.session_state[error_key]:
        error = st.session_state[error_key]
        st.session_state[error_key] = None
        st.session_state[recording_key] = False
        st.error(f"🎤 Voice error: {error}")
    
    is_recording = st.session_state.get(recording_key, False)
    
    if is_recording:
        # Show recording indicator with red button and status
        col_btn, col_status = st.columns([1, 4])
        with col_btn:
            if st.button("REC", key=f"{voice_key}_stop", help="Click to cancel recording"):
                st.session_state[recording_key] = False
                st.rerun()
        with col_status:
            st.markdown(
                '<p style="color: #e74c3c; font-size: 13px; margin: 6px 0; font-weight: 600;">🎤 Recording... speak now</p>',
                unsafe_allow_html=True
            )
        
        # Inject visual indicator and start speech recognition via JS
        components.html(f"""
        <style>
            @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}
            .rec {{ color:#e74c3c; animation:pulse 1s infinite; padding:6px; background:#2a0a0a; border-radius:6px; border:1px solid #e74c3c; font-size:13px; }}
        </style>
        <div class="rec" style="color:#e74c3c;font-weight:600;">REC Listening...</div>
        <script>
        (function() {{
            console.log('[VoiceDictation] Starting for: {target_key}');
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{ console.error('[VoiceDictation] Not supported'); sessionStorage.setItem('vd_error_{voice_key}','not_supported'); return; }}
            const r = new SR();
            r.lang = 'en-US';
            r.interimResults = false;
            r.maxAlternatives = 1;
            r.onstart = () => console.log('[VoiceDictation] Started');
            r.onresult = (e) => {{
                const t = e.results[0][0].transcript;
                console.log('[VoiceDictation] Result:', t, 'Confidence:', e.results[0][0].confidence);
                sessionStorage.setItem('vd_result_{voice_key}', t);
            }};
            r.onerror = (e) => {{
                console.error('[VoiceDictation] Error:', e.error);
                sessionStorage.setItem('vd_error_{voice_key}', e.error);
            }};
            r.onend = () => {{
                console.log('[VoiceDictation] Ended');
                sessionStorage.setItem('vd_ended_{voice_key}', 'true');
            }};
            try {{ r.start(); }} catch(e) {{ console.error('[VoiceDictation] Start failed:', e); }}
        }})();
        </script>
        """, height=40)
        
        # Poll for result
        try:
            poll_result = streamlit_js_eval(
                js_expressions=f"""
                (function() {{
                    const r = sessionStorage.getItem('vd_result_{voice_key}');
                    const e = sessionStorage.getItem('vd_error_{voice_key}');
                    const ended = sessionStorage.getItem('vd_ended_{voice_key}');
                    if (r) {{ sessionStorage.removeItem('vd_result_{voice_key}'); sessionStorage.removeItem('vd_ended_{voice_key}'); return JSON.stringify({{type:'result',value:r}}); }}
                    if (e) {{ sessionStorage.removeItem('vd_error_{voice_key}'); sessionStorage.removeItem('vd_ended_{voice_key}'); return JSON.stringify({{type:'error',value:e}}); }}
                    if (ended === 'true') {{ sessionStorage.removeItem('vd_ended_{voice_key}'); return JSON.stringify({{type:'no_result'}}); }}
                    return null;
                }})()
                """,
                key=f"poll_{voice_key}_{datetime.now().timestamp()}"
            )
            
            if poll_result:
                import json
                data = json.loads(poll_result)
                if data.get('type') == 'result':
                    st.session_state[result_key] = data['value']
                    st.session_state[recording_key] = False
                    st.rerun()
                elif data.get('type') == 'error':
                    st.session_state[error_key] = data['value']
                    st.session_state[recording_key] = False
                    st.rerun()
                elif data.get('type') == 'no_result':
                    st.session_state[recording_key] = False
                    st.warning("No speech detected. Please try again.")
                    st.rerun()
        except Exception as e:
            print(f"[VoiceDictation] Poll error: {e}")
    else:
        if st.button("🎙️", key=f"{voice_key}_start", help="Voice dictation - click and speak"):
            st.session_state[recording_key] = True
            st.rerun()


def render_new_leads():
    """Render NEW leads section with Electric Blue badges and clickable tiles."""
    leads = get_new_leads()
    
    if not leads:
        return False
    
    st.markdown(
        f'''
        <div style="margin: 0 0 12px 0;">
            <h3 style="color: #E5E5E5; margin: 0; display: inline-block; font-size: 18px;">
                New Leads
            </h3>
            <span style="
                background: #00A8E8;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 13px;
                font-weight: 600;
                margin-left: 12px;
            ">{len(leads)} NEW</span>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    for lead in leads:
        lead_id = str(lead.get("id", ""))
        lead_name = lead.get("name") or "Unknown"
        zap_icon = get_icon("zap", "#FFB800", 12)
        brain_icon = get_icon("brain", "#00A8E8", 12)
        source_badge = f'{zap_icon} Zapier' if lead.get("source") == "zapier" else f'{brain_icon} Smart Intake'
        source_color = "#FFB800" if lead.get("source") == "zapier" else "#00A8E8"
        
        col1, col2 = st.columns([5, 1])
        
        with col1:
            if st.button(f"{lead_name}", key=f"nl_nav_{lead_id}", help="Open lead details"):
                st.session_state.page = "lead_detail"
                st.session_state.current_lead_id = lead_id
                st.rerun()
            
            st.markdown(
                f'''
                <div style="margin-top: -6px; margin-bottom: 8px;">
                    <span style="background: {source_color}20; color: {source_color}; padding: 2px 8px; border-radius: 8px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">{source_badge}</span>
                    <span style="color: {KB_MUTED}; font-size: 12px; margin-left: 10px;">
                        {lead.get("phone") or "No phone"} | {lead.get("email") or "No email"}
                    </span>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f'''<span style="background: {KB_GREEN}; color: {KB_DARK}; padding: 3px 8px; border-radius: 8px; font-size: 11px; font-weight: 600;">NEW</span>''',
                unsafe_allow_html=True
            )
    
    return True


def render_dashboard():
    """Render the main dashboard view."""
    
    # Interface Anchor - scroll preservation JavaScript
    scroll_preservation_js = """
    <script>
    (function() {
        const savedPos = sessionStorage.getItem('grayco_scroll_pos');
        if (savedPos && savedPos !== '0') {
            setTimeout(function() {
                window.scrollTo(0, parseInt(savedPos));
                sessionStorage.removeItem('grayco_scroll_pos');
            }, 100);
        }
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('button');
            if (btn) {
                sessionStorage.setItem('grayco_scroll_pos', window.scrollY.toString());
            }
        }, true);
    })();
    </script>
    """
    st.markdown(scroll_preservation_js, unsafe_allow_html=True)
    
    # Hot Lead popup trigger - check for new leads on login/refresh
    if not st.session_state.get("hot_lead_dismissed", False):
        new_leads = get_new_leads()
        if new_leads:
            first_lead = new_leads[0]
            st.session_state[f"lead_cache_{first_lead.get('id', '')}"] = first_lead
            render_hot_lead_popup(first_lead)
    
    # Check for any lead dialogs that need to be rendered from HOT LEADS section
    new_leads_for_dialogs = get_new_leads()
    for lead in new_leads_for_dialogs:
        lead_id = str(lead.get("id", ""))
        if st.session_state.get(f"show_lead_email_dialog_{lead_id}"):
            cached_lead = st.session_state.get(f"lead_cache_{lead_id}", lead)
            render_lead_email_dialog(cached_lead)
        if st.session_state.get(f"show_lead_text_dialog_{lead_id}"):
            cached_lead = st.session_state.get(f"lead_cache_{lead_id}", lead)
            render_lead_text_dialog(cached_lead)
    
    if st.session_state.get("deleted_project_name"):
        deleted_name = st.session_state.pop("deleted_project_name")
        st.toast(f"Project '{deleted_name}' deleted", icon="✅")
    
    inbox_icon = get_icon("inbox", KB_GREEN, 16)
    
    st.markdown(
        f'''
        <div style="
            text-align: center;
            padding: 8px 0 4px 0;
            margin-bottom: 4px;
        ">
            <div style="display: inline-flex; align-items: baseline; gap: 6px;">
                <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 22px; font-weight: 700; color: {KB_GREEN}; letter-spacing: -0.5px;">KB</span>
                <span style="font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 22px; font-weight: 300; color: {KB_TEXT}; letter-spacing: -0.5px;">Signs</span>
            </div>
            <div style="width: 80px; height: 1px; background: {KB_GREEN}; margin: 2px auto 0 auto;"></div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    hot_lead_showing = not st.session_state.get("hot_lead_dismissed", False) and bool(get_new_leads())
    
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button(f"Smart Intake", type="primary", use_container_width=True, disabled=hot_lead_showing, key="smart_intake_btn"):
            st.session_state["show_smart_intake"] = True
            st.session_state["hot_lead_dismissed"] = True
            st.rerun()
    
    if st.session_state.get("show_smart_intake", False):
        render_smart_intake_dialog()
        st.session_state["show_smart_intake"] = False
    
    render_action_hub()
    
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    
    # UNIFIED WORKFLOW: Removed separate New Leads section
    # New projects with status='New' now appear in Hot Leads only
    # When contacted, they become 'Block A' and appear in main project queues
    
    sort_options = {
        "Name A-Z": "name_asc",
        "Newest": "newest",
        "Updated": "last_updated"
    }
    
    if "dashboard_sort" not in st.session_state:
        st.session_state["dashboard_sort"] = "Name A-Z"
    
    sort_choice = st.radio(
        "Sort by:",
        options=list(sort_options.keys()),
        index=list(sort_options.keys()).index(st.session_state["dashboard_sort"]),
        horizontal=True,
        key="sort_radio"
    )
    st.session_state["dashboard_sort"] = sort_choice
    
    promoted_projects = get_promoted_projects(sort_by=sort_options[sort_choice])
    
    in_production = len([p for p in promoted_projects if p.get("status") in ["in_production", "design"]])
    completed = len([p for p in promoted_projects if p.get("status") in ["completed", "invoiced"]])
    total_revenue = sum(float(p.get("estimated_value") or 0) for p in promoted_projects)
    dollar_icon = get_icon("dollar", KB_GREEN, 14)
    
    st.markdown(
        f'''
        <div style="
            background: {KB_CARD_BG};
            border: 1px solid {KB_BORDER};
            border-radius: 12px;
            padding: 12px 16px;
            margin: 12px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        ">
            <div style="display: flex; align-items: center; gap: 16px;">
                <span style="color: {KB_TEXT}; font-size: 14px;"><strong>{len(promoted_projects)}</strong> Active</span>
                <span style="color: {KB_MUTED}; font-size: 13px;">{in_production} In Prod</span>
                <span style="color: {KB_MUTED}; font-size: 13px;">{completed} Done</span>
            </div>
            <div style="display: flex; align-items: center; gap: 4px;">
                {dollar_icon}
                <span style="color: {KB_GREEN}; font-weight: 600; font-size: 14px;">${total_revenue:,.0f}</span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    st.markdown(f'<p style="color: {KB_TEXT}; font-size: 14px; font-weight: 600; margin: 8px 0;">Active Projects</p>', unsafe_allow_html=True)
    
    if not promoted_projects:
        st.info("No active projects yet.")
    else:
        col_count = 2
        rows = [promoted_projects[i:i + col_count] for i in range(0, len(promoted_projects), col_count)]
        
        for row_idx, row in enumerate(rows):
            cols = st.columns(col_count)
            for col_idx, project in enumerate(row):
                with cols[col_idx]:
                    render_project_tile(project, key_prefix=f"dash_{row_idx}_{col_idx}")
    
    render_victory_vault_section()
    render_lost_deals_section()
    render_cold_storage_section()


def render_victory_vault_section():
    """Render the Victory Vault (won projects) section at the bottom of the dashboard."""
    won_projects = get_won_projects()
    
    if not won_projects:
        return
    
    with st.expander(f"🏆 Victory Vault ({len(won_projects)})", expanded=False):
        st.markdown(
            f'<p style="color: {KB_MUTED}; font-size: 11px; margin: 0 0 8px 0;">Successfully closed deals - click to view details</p>',
            unsafe_allow_html=True
        )
        
        for proj in won_projects:
            project_id = str(proj.get("id", ""))
            client_name = proj.get("client_name", "Unknown")
            estimated_value = proj.get("estimated_value", 0)
            value_str = f"${float(estimated_value or 0):,.0f}" if estimated_value else ""
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(
                    f'<p style="color: {KB_GREEN}; font-size: 13px; margin: 0;">🏆 {client_name}</p>',
                    unsafe_allow_html=True
                )
            
            with col2:
                if value_str:
                    st.markdown(
                        f'<p style="color: {KB_GREEN}; font-size: 12px; margin: 0;">{value_str}</p>',
                        unsafe_allow_html=True
                    )
            
            with col3:
                if st.button("View", key=f"view_won_{project_id}", use_container_width=True):
                    st.session_state.current_project_id = project_id
                    st.session_state.page = "project_detail"
                    st.rerun()


def render_lost_deals_section():
    """Render the Lost Deals (lost projects) section at the bottom of the dashboard."""
    lost_projects = get_lost_projects()
    
    if not lost_projects:
        return
    
    with st.expander(f"🪦 Lost Deals ({len(lost_projects)})", expanded=False):
        st.markdown(
            f'<p style="color: {KB_MUTED}; font-size: 11px; margin: 0 0 8px 0;">Lost opportunities - click to view or retry</p>',
            unsafe_allow_html=True
        )
        
        for proj in lost_projects:
            project_id = str(proj.get("id", ""))
            client_name = proj.get("client_name", "Unknown")
            estimated_value = proj.get("estimated_value", 0)
            value_str = f"${float(estimated_value or 0):,.0f}" if estimated_value else ""
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(
                    f'<p style="color: {KB_MUTED}; font-size: 13px; margin: 0;">🪦 {client_name}</p>',
                    unsafe_allow_html=True
                )
            
            with col2:
                if value_str:
                    st.markdown(
                        f'<p style="color: {KB_MUTED}; font-size: 12px; margin: 0;">{value_str}</p>',
                        unsafe_allow_html=True
                    )
            
            with col3:
                if st.button("View", key=f"view_lost_{project_id}", use_container_width=True):
                    st.session_state.current_project_id = project_id
                    st.session_state.page = "project_detail"
                    st.rerun()


def render_cold_storage_section():
    """Render the Cold Storage (archived projects) section at the bottom of the dashboard."""
    archived = get_archived_projects()
    
    if not archived:
        return
    
    archive_icon = get_icon("archive", KB_MUTED, 14)
    
    with st.expander(f"📁 Cold Storage ({len(archived)})", expanded=False):
        st.markdown(
            f'<p style="color: {KB_MUTED}; font-size: 11px; margin: 0 0 8px 0;">Archived projects - click to view or restore</p>',
            unsafe_allow_html=True
        )
        
        for proj in archived:
            project_id = str(proj.get("id", ""))
            client_name = proj.get("client_name", "Unknown")
            estimated_value = proj.get("estimated_value", 0)
            value_str = f"${float(estimated_value or 0):,.0f}" if estimated_value else ""
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(
                    f'<p style="color: {KB_TEXT}; font-size: 13px; margin: 0;">{client_name}</p>',
                    unsafe_allow_html=True
                )
            
            with col2:
                if value_str:
                    st.markdown(
                        f'<p style="color: {KB_MUTED}; font-size: 12px; margin: 0;">{value_str}</p>',
                        unsafe_allow_html=True
                    )
            
            with col3:
                if st.button("View", key=f"view_archived_{project_id}", use_container_width=True):
                    st.session_state.current_project_id = project_id
                    st.session_state.page = "project_detail"
                    st.rerun()
