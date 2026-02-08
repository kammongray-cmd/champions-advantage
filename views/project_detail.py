import streamlit as st
import os
from datetime import datetime, date
from PIL import Image, ImageDraw, ImageFont
import io
import base64
from streamlit_drawable_canvas import st_canvas
from services.database_manager import get_project_by_id, get_status_badge, update_project_status_with_note, delete_project, update_no_design_required, update_action_status, add_project_history, update_project_identity, mark_project_won, mark_project_lost
from services.email_service import send_email
from services.gemini_service import draft_design_email, draft_pricing_email, draft_proposal_email
from services.timezone_utils import today_mountain, now_mountain, get_timestamp_mountain, get_file_timestamp_mountain


def render_project_detail():
    """Render the Project Detail View - Matt & Bruno Loop."""
    # Inject scroll preservation JavaScript - saves position before rerun and restores after
    scroll_preservation_js = """
    <script>
    (function() {
        // Restore scroll position if saved
        const savedPos = sessionStorage.getItem('grayco_scroll_pos');
        if (savedPos && savedPos !== '0') {
            setTimeout(function() {
                window.scrollTo(0, parseInt(savedPos));
                sessionStorage.removeItem('grayco_scroll_pos');
            }, 100);
        }
        
        // Save scroll position before any button click that causes rerun
        document.addEventListener('click', function(e) {
            const btn = e.target.closest('button');
            if (btn && !btn.textContent.includes('Back to Dashboard') && !btn.textContent.includes('Delete')) {
                sessionStorage.setItem('grayco_scroll_pos', window.scrollY.toString());
            }
        }, true);
    })();
    </script>
    """
    st.markdown(scroll_preservation_js, unsafe_allow_html=True)
    
    # Handle explicit scroll to top (for navigation)
    try:
        from streamlit_js_eval import streamlit_js_eval
        if st.session_state.get("scroll_to_top"):
            streamlit_js_eval(js_expressions="sessionStorage.removeItem('grayco_scroll_pos'); window.scrollTo(0, 0);", key="scroll_top")
            st.session_state.scroll_to_top = False
    except:
        pass
    
    # Render the main content
    render_project_detail_content()


def render_project_detail_content():
    """Render the main content of the Project Detail View."""
    project_id = st.session_state.get("current_project_id")
    
    if not project_id:
        st.warning("No project selected.")
        if st.button("← Back to Dashboard", type="primary"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return
    
    project = get_project_by_id(project_id)
    
    if not project:
        st.error(f"Project not found: {project_id}")
        if st.button("← Back to Dashboard", type="primary"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return
    
    client_name = project.get("client_name", "Unknown Client")
    status = project.get("status", "pending")
    notes = project.get("notes", "") or ""
    estimated_value = project.get("estimated_value", 0)
    google_drive_link = project.get("google_drive_link", "")
    google_drive_folder_id = project.get("google_drive_folder_id", "") or ""
    date_applied = project.get("date_applied")
    permit_number = project.get("permit_number", "") or ""
    permit_phone = project.get("permit_office_phone", "") or ""
    site_address = project.get("site_address", "") or ""
    design_proof_drive_id = project.get("design_proof_drive_id", "") or ""
    design_proof_name = project.get("design_proof_name", "") or ""
    proposal_drive_id = project.get("proposal_drive_id", "") or ""
    proposal_name = project.get("proposal_name", "") or ""
    no_design_required = project.get("no_design_required", False) or False
    
    master_spec_file_id = project.get("master_spec_file_id", "") or ""
    master_spec_file_name = project.get("master_spec_file_name", "") or ""
    master_spec_locked_at = project.get("master_spec_locked_at")
    production_locked = project.get("production_locked", False) or False
    signed_spec_file_id = project.get("signed_spec_file_id", "") or ""
    signed_spec_file_name = project.get("signed_spec_file_name", "") or ""
    
    render_sticky_header(client_name, status, google_drive_link)
    
    is_in_production = production_locked or status == "ACTIVE PRODUCTION"
    if is_in_production:
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #ff4444 0%, #cc0000 100%);
                border-radius: 8px;
                padding: 12px 20px;
                margin: 0 0 16px 0;
                text-align: center;
            ">
                <p style="color: white; margin: 0; font-size: 16px; font-weight: 700;">
                    🔒 PRODUCTION LOCKED: No design changes permitted without a Change Order.
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    st.divider()
    
    pending_action = project.get("pending_action", False) or False
    action_note = project.get("action_note", "") or ""
    action_due_date = project.get("action_due_date")
    render_action_capture_box(project_id, pending_action, action_note, action_due_date)
    
    primary_contact_name = project.get("primary_contact_name", "") or ""
    primary_contact_phone = project.get("primary_contact_phone", "") or ""
    primary_contact_email = project.get("primary_contact_email", "") or ""
    secondary_contact_name = project.get("secondary_contact_name", "") or ""
    secondary_contact_phone = project.get("secondary_contact_phone", "") or ""
    secondary_contact_email = project.get("secondary_contact_email", "") or ""
    
    render_project_identity_header(
        project_id, client_name, site_address,
        primary_contact_name, primary_contact_phone, primary_contact_email,
        secondary_contact_name, secondary_contact_phone, secondary_contact_email,
        status
    )
    
    st.markdown(
        '''<hr style="border: none; border-top: 2px solid #00A8E8; margin: 20px 0 24px 0;">''',
        unsafe_allow_html=True
    )
    
    status_lower = (status or "").lower().replace(" ", "_").replace("-", "_")
    
    # State-aware expansion: only the relevant block opens based on status
    expand_a = status_lower in ["migrated", "lead"]
    expand_b = status_lower == "design"
    expand_c = status_lower in ["quoting", "proposal", "pricing"]
    expand_d = status_lower in ["awaiting_deposit", "awaiting", "confirmed", "approved"]
    
    focus_mode_statuses = ["active_production", "production", "in_production", "installed", "completed", "invoiced", "permit_pending"]
    is_focus_mode = status_lower in focus_mode_statuses
    
    with st.expander("Block A: The Shoebox (Intake)", expanded=expand_a and not is_focus_mode):
        render_block_a_shoebox(project_id, client_name, google_drive_folder_id, 
                               master_spec_file_name, production_locked)
    
    with st.expander("Block B: Design Loop (Matt)", expanded=expand_b and not is_focus_mode):
        design_uploaded = render_block_b_design_loop(project_id, client_name, notes, google_drive_link, design_proof_drive_id, design_proof_name, no_design_required, status)
    
    if is_focus_mode:
        design_uploaded = True
    
    with st.expander("Block C: Pricing Loop (Bruno)", expanded=expand_c and not is_focus_mode):
        render_block_c_pricing_loop(project_id, client_name, design_uploaded, google_drive_link, proposal_drive_id, proposal_name)
    
    deposit_received_date = project.get("deposit_received_date")
    deposit_amount = project.get("deposit_amount", 0) or 0
    deposit_invoice_requested = project.get("deposit_invoice_requested", False)
    deposit_invoice_sent = project.get("deposit_invoice_sent", False)
    estimated_value = project.get("estimated_value", 0) or 0
    
    with st.expander("💵 Block D: Deposit & Handoff", expanded=expand_d and not is_focus_mode):
        render_block_d_deposit_handoff(
            project_id, client_name, status, 
            deposit_invoice_requested, deposit_invoice_sent, 
            deposit_received_date, deposit_amount,
            google_drive_link, estimated_value,
            master_spec_file_id, master_spec_file_name,
            signed_spec_file_id, signed_spec_file_name,
            production_locked
        )
        render_project_decision(project_id, client_name, status, deposit_received_date)
    
    render_block_e_production_logistics(
        project_id, client_name, status, deposit_received_date
    )
    
    render_block_f_installation_prep(
        project_id, client_name, status, google_drive_link
    )
    
    render_block_g_project_closeout(
        project_id, client_name, status
    )
    
    # Project History at the very bottom in collapsed expander
    with st.expander("📜 Project History", expanded=False):
        render_project_history(project_id)
    
    render_project_footer(project_id, client_name, status)


def render_project_footer(project_id: str, client_name: str, status: str):
    """Render the project footer with archive/restore and delete options."""
    from services.database_manager import archive_project, restore_project
    
    is_archived = status.lower() == "archived"
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        f'''
        <div style="
            border-top: 1px solid #333;
            padding-top: 24px;
            margin-top: 16px;
        ">
            <p style="color: #666; font-size: 11px; margin: 0 0 8px 0;">{"Cold Storage" if is_archived else "Project Management"}</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    if is_archived:
        col1, col2, col3 = st.columns([1.5, 1.5, 1])
        
        with col1:
            if st.button("♻️ Restore to Active", key=f"restore_btn_{project_id}", type="primary"):
                if restore_project(project_id):
                    st.toast("Restored to Block A", icon="✅")
                    st.rerun()
                else:
                    st.error("Failed to restore project")
        
        with col2:
            delete_key = f"confirm_delete_{project_id}"
            confirm_checked = st.checkbox(
                "Confirm permanent delete",
                key=delete_key,
                help="Check to enable delete"
            )
        
        with col3:
            if st.button(
                "🗑️ Delete",
                key=f"delete_btn_{project_id}",
                type="secondary",
                disabled=not confirm_checked
            ):
                success, error_msg = delete_project(project_id)
                if success:
                    st.session_state["deleted_project_name"] = client_name
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error(f"Failed to delete: {error_msg}")
        
        if confirm_checked:
            st.markdown(
                f'<p style="color: #dc3545; font-size: 12px; margin-top: 8px;">⚠️ This will permanently delete "{client_name}". Google Drive files will remain safe.</p>',
                unsafe_allow_html=True
            )
    else:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("📁 Move to Cold Storage", key=f"archive_btn_{project_id}"):
                if archive_project(project_id):
                    st.toast("Moved to Cold Storage", icon="✅")
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("Failed to archive project")
        
        st.markdown(
            '<p style="color: #666; font-size: 11px; margin-top: 8px;">Archive this project to remove it from your active dashboard. You can restore it anytime from Cold Storage.</p>',
            unsafe_allow_html=True
        )


def render_sticky_header(client_name: str, status: str, google_drive_link: str):
    """Render the sticky header with client name, back button, and Drive link."""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(
            f'''
            <div style="padding: 10px 0;">
                <h1 style="color: #E5E5E5; margin: 0; font-size: 28px;">{client_name}</h1>
                <p style="color: #00A8E8; margin: 4px 0 0 0; font-size: 14px;">
                    Status: {status} {get_status_badge(status)}
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    with col2:
        if google_drive_link:
            st.link_button(
                "📁 View Google Drive Folder",
                google_drive_link,
                use_container_width=True,
                type="primary"
            )
        else:
            st.markdown(
                '<p style="color: #888; font-size: 12px; text-align: center;">No Drive folder linked</p>',
                unsafe_allow_html=True
            )
    
    with col3:
        if st.button("← Back to Dashboard", key="back_btn", use_container_width=True):
            st.session_state.page = "Dashboard"
            st.rerun()


def render_action_capture_box(project_id: str, pending_action: bool, action_note: str, action_due_date=None):
    """Render compact Action Capture box with inline due date and standard mic icon."""
    from components.icons import get_icon
    
    KB_CARD_BG = "#111111"
    KB_BORDER = "#222222"
    KB_TEXT = "#E5E5E5"
    KB_GREEN = "#39FF14"
    
    with st.expander("Next Action", expanded=True):
        voice_key = f"voice_text_{project_id}"
        if voice_key not in st.session_state:
            st.session_state[voice_key] = ""
        
        combined_note = action_note
        if st.session_state[voice_key]:
            combined_note = (action_note + " " + st.session_state[voice_key]).strip()
        
        note_col, mic_col = st.columns([10, 1])
        
        with note_col:
            new_action_note = st.text_area(
                "Action",
                value=combined_note,
                height=60,
                key=f"action_note_{project_id}",
                placeholder="What's next for this project?",
                label_visibility="collapsed"
            )
        
        with mic_col:
            if st.button("Mic", key=f"mic_pulse_{project_id}", help="Voice dictation"):
                st.session_state[f"show_voice_modal_{project_id}"] = True
                st.rerun()
        
        if st.session_state.get(f"show_voice_modal_{project_id}", False):
            render_voice_dictation_modal(project_id, voice_key)
        
        current_due = None
        if action_due_date:
            if isinstance(action_due_date, date):
                current_due = action_due_date
            else:
                try:
                    current_due = datetime.fromisoformat(str(action_due_date).replace('Z', '+00:00')).date()
                except:
                    pass
        
        col_date, col_save = st.columns([1, 1])
        
        with col_date:
            new_due_date = st.date_input(
                "Due",
                value=current_due,
                key=f"action_due_date_{project_id}",
                label_visibility="collapsed"
            )
        
        with col_save:
            if st.button("Save", key=f"save_action_{project_id}", type="primary", use_container_width=True):
                due_date_to_save = new_due_date if new_due_date else None
                has_note = bool(new_action_note and new_action_note.strip())
                has_date = due_date_to_save is not None
                auto_pending_action = has_note or has_date
                
                if update_action_status(project_id, auto_pending_action, new_action_note, due_date_to_save):
                    if auto_pending_action and new_action_note:
                        add_project_history(project_id, "ACTION_LOG", f"[ACTION LOG] {new_action_note}")
                    st.toast("Saved", icon="✅")
                    st.rerun()
                else:
                    st.error("Failed to save action status")


def render_project_identity_header(project_id: str, client_name: str, site_address: str,
                                   primary_contact_name: str, primary_contact_phone: str, primary_contact_email: str,
                                   secondary_contact_name: str, secondary_contact_phone: str, secondary_contact_email: str,
                                   status: str = ""):
    """Render the editable Project Identity header with contacts, Google Maps link, and Global Escape Hatch."""
    
    status_lower = (status or "").lower().replace(" ", "_")
    show_lost_button = status_lower not in ['closed_-_won', 'closed_-_lost', 'completed', 'archived']
    
    with st.expander("📋 Project Identity", expanded=True):
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 16px;
                border: 1px solid #00A8E8;
            ">
                <p style="color: #00A8E8; font-size: 13px; margin: 0; font-weight: 600;">
                    🏢 Project Details & Contact Information
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_project_name = st.text_input(
                "Project Name",
                value=client_name,
                key=f"identity_name_{project_id}",
                placeholder="Enter project/client name"
            )
        
        with col2:
            new_site_address = st.text_input(
                "Site Address",
                value=site_address,
                key=f"identity_address_{project_id}",
                placeholder="Enter installation address"
            )
        
        if new_site_address:
            maps_url = f"https://www.google.com/maps/search/?api=1&query={new_site_address.replace(' ', '+')}"
            st.markdown(
                f'''
                <a href="{maps_url}" target="_blank" style="
                    display: inline-block;
                    background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                    color: #00A8E8;
                    padding: 8px 16px;
                    border-radius: 8px;
                    text-decoration: none;
                    font-size: 14px;
                    border: 1px solid #00A8E8;
                    margin: 8px 0;
                ">📍 Get Directions</a>
                ''',
                unsafe_allow_html=True
            )
        
        st.markdown(
            '<p style="color: #00A8E8; font-size: 14px; font-weight: 600; margin: 16px 0 8px 0;">👤 Primary Contact</p>',
            unsafe_allow_html=True
        )
        
        p_col1, p_col2, p_col3 = st.columns(3)
        
        with p_col1:
            new_primary_name = st.text_input(
                "Name",
                value=primary_contact_name,
                key=f"identity_primary_name_{project_id}",
                placeholder="Contact name"
            )
        
        with p_col2:
            new_primary_phone = st.text_input(
                "Phone",
                value=primary_contact_phone,
                key=f"identity_primary_phone_{project_id}",
                placeholder="(555) 123-4567"
            )
            if new_primary_phone:
                clean_phone = ''.join(filter(str.isdigit, new_primary_phone))
                st.markdown(
                    f'<a href="tel:{clean_phone}" style="color: #00A8E8; font-size: 12px;">📞 Call</a>',
                    unsafe_allow_html=True
                )
        
        with p_col3:
            new_primary_email = st.text_input(
                "Email",
                value=primary_contact_email,
                key=f"identity_primary_email_{project_id}",
                placeholder="email@example.com"
            )
            if new_primary_email:
                st.markdown(
                    f'<a href="mailto:{new_primary_email}" style="color: #00A8E8; font-size: 12px;">✉️ Email</a>',
                    unsafe_allow_html=True
                )
        
        st.markdown(
            '<p style="color: #888; font-size: 13px; font-weight: 600; margin: 16px 0 8px 0;">👥 Secondary Contact (Optional)</p>',
            unsafe_allow_html=True
        )
        
        s_col1, s_col2, s_col3 = st.columns(3)
        
        with s_col1:
            new_secondary_name = st.text_input(
                "Name ",
                value=secondary_contact_name,
                key=f"identity_secondary_name_{project_id}",
                placeholder="Contact name"
            )
        
        with s_col2:
            new_secondary_phone = st.text_input(
                "Phone ",
                value=secondary_contact_phone,
                key=f"identity_secondary_phone_{project_id}",
                placeholder="(555) 123-4567"
            )
            if new_secondary_phone:
                clean_phone = ''.join(filter(str.isdigit, new_secondary_phone))
                st.markdown(
                    f'<a href="tel:{clean_phone}" style="color: #888; font-size: 12px;">📞 Call</a>',
                    unsafe_allow_html=True
                )
        
        with s_col3:
            new_secondary_email = st.text_input(
                "Email ",
                value=secondary_contact_email,
                key=f"identity_secondary_email_{project_id}",
                placeholder="email@example.com"
            )
            if new_secondary_email:
                st.markdown(
                    f'<a href="mailto:{new_secondary_email}" style="color: #888; font-size: 12px;">✉️ Email</a>',
                    unsafe_allow_html=True
                )
        
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        
        if st.button("💾 SAVE PROJECT IDENTITY", key=f"save_identity_{project_id}", type="primary", use_container_width=True):
            if update_project_identity(
                project_id, new_project_name, new_site_address,
                new_primary_name, new_primary_phone, new_primary_email,
                new_secondary_name, new_secondary_phone, new_secondary_email
            ):
                st.success("Project identity saved!")
                st.rerun()
            else:
                st.error("Failed to save project identity")
        
        if show_lost_button:
            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
            st.markdown(
                '''
                <style>
                    div[data-testid="stButton"] button[kind="secondary"][data-testid*="escape_hatch"] {
                        border: 1px solid #ff4444 !important;
                        color: #ff6666 !important;
                        background: transparent !important;
                        font-size: 12px !important;
                        padding: 4px 12px !important;
                    }
                </style>
                ''',
                unsafe_allow_html=True
            )
            col_spacer, col_lost = st.columns([3, 1])
            with col_lost:
                if st.button("❌ Project Lost", key=f"escape_hatch_lost_{project_id}", use_container_width=True):
                    render_project_lost_dialog(project_id, client_name)


@st.dialog("Voice Dictation")
def render_voice_dictation_modal(project_id: str, voice_key: str):
    """Render voice dictation modal with visual feedback and proper Streamlit integration.
    
    Uses streamlit_js_eval with async promise pattern for reliable speech recognition.
    - Visual feedback: 🔴 pulsing indicator when recording
    - Appends text (doesn't overwrite)
    - Console logs for debugging
    """
    import streamlit.components.v1 as components
    from streamlit_js_eval import streamlit_js_eval
    import json
    
    modal_voice_key = f"modal_{project_id}"
    recording_key = f"modal_recording_{project_id}"
    result_key = f"modal_voice_result_{project_id}"
    error_key = f"modal_voice_error_{project_id}"
    
    # Process any pending voice result
    if result_key in st.session_state and st.session_state[result_key]:
        result = st.session_state[result_key]
        st.session_state[result_key] = None
        st.session_state[recording_key] = False
        
        # Append to existing text (don't overwrite)
        current = st.session_state.get(voice_key, "")
        if current:
            st.session_state[voice_key] = current + " " + result
        else:
            st.session_state[voice_key] = result
        
        st.toast(f"✅ Added: {result}", icon="🎤")
    
    # Process any pending error
    if error_key in st.session_state and st.session_state[error_key]:
        error = st.session_state[error_key]
        st.session_state[error_key] = None
        st.session_state[recording_key] = False
        st.error(f"🎤 Voice error: {error}")
    
    is_recording = st.session_state.get(recording_key, False)
    
    st.markdown(
        '''
        <div style="text-align: center; padding: 10px;">
            <p style="color: #E5E5E5; margin-bottom: 12px;">Click the button below to start voice recording.</p>
            <p style="color: #888; font-size: 12px;">Note: Works best in Chrome. Speak clearly after clicking.</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    if is_recording:
        # Show recording indicator with pulsing animation
        components.html(f"""
        <style>
            @keyframes pulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.7; transform:scale(1.05); }} }}
            .rec-box {{ color:#e74c3c; font-size:18px; animation:pulse 1s infinite; padding:20px; background:linear-gradient(145deg, #2a0a0a 0%, #1a0505 100%); border-radius:12px; border:2px solid #e74c3c; text-align:center; margin:10px 0; }}
        </style>
        <div class="rec-box">🔴 Listening... Speak now!</div>
        <script>
        (function() {{
            console.log('[VoiceDictation] Starting modal recognition for: {voice_key}');
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{ console.error('[VoiceDictation] Not supported'); sessionStorage.setItem('vd_error_{modal_voice_key}','not_supported'); return; }}
            const r = new SR();
            r.lang = 'en-US';
            r.interimResults = false;
            r.maxAlternatives = 1;
            r.onstart = () => console.log('[VoiceDictation] Modal started');
            r.onresult = (e) => {{
                const t = e.results[0][0].transcript;
                console.log('[VoiceDictation] Modal result:', t, 'Confidence:', e.results[0][0].confidence);
                sessionStorage.setItem('vd_result_{modal_voice_key}', t);
            }};
            r.onerror = (e) => {{
                console.error('[VoiceDictation] Modal error:', e.error);
                sessionStorage.setItem('vd_error_{modal_voice_key}', e.error);
            }};
            r.onend = () => {{
                console.log('[VoiceDictation] Modal ended');
                sessionStorage.setItem('vd_ended_{modal_voice_key}', 'true');
            }};
            try {{ r.start(); }} catch(e) {{ console.error('[VoiceDictation] Modal start failed:', e); }}
        }})();
        </script>
        """, height=80)
        
        # Poll for result
        try:
            poll_result = streamlit_js_eval(
                js_expressions=f"""
                (function() {{
                    const r = sessionStorage.getItem('vd_result_{modal_voice_key}');
                    const e = sessionStorage.getItem('vd_error_{modal_voice_key}');
                    const ended = sessionStorage.getItem('vd_ended_{modal_voice_key}');
                    if (r) {{ sessionStorage.removeItem('vd_result_{modal_voice_key}'); sessionStorage.removeItem('vd_ended_{modal_voice_key}'); return JSON.stringify({{type:'result',value:r}}); }}
                    if (e) {{ sessionStorage.removeItem('vd_error_{modal_voice_key}'); sessionStorage.removeItem('vd_ended_{modal_voice_key}'); return JSON.stringify({{type:'error',value:e}}); }}
                    if (ended === 'true') {{ sessionStorage.removeItem('vd_ended_{modal_voice_key}'); return JSON.stringify({{type:'no_result'}}); }}
                    return null;
                }})()
                """,
                key=f"poll_{modal_voice_key}_{datetime.now().timestamp()}"
            )
            
            if poll_result:
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
            print(f"[VoiceDictation] Modal poll error: {e}")
        
        if st.button("⏹️ Stop Recording", use_container_width=True, key=f"stop_modal_{project_id}"):
            st.session_state[recording_key] = False
            st.rerun()
    else:
        if st.button("🔴 Start Recording", type="primary", use_container_width=True, key=f"start_modal_{project_id}"):
            st.session_state[recording_key] = True
            st.rerun()
    
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Done", use_container_width=True, key=f"done_modal_{project_id}"):
            st.session_state[f"show_voice_modal_{project_id}"] = False
            st.session_state[recording_key] = False
            st.rerun()
    with col2:
        if st.button("🗑️ Clear", use_container_width=True, key=f"clear_modal_{project_id}"):
            st.session_state[voice_key] = ""
            st.session_state[f"show_voice_modal_{project_id}"] = False
            st.session_state[recording_key] = False
            st.rerun()


def get_browser_gps(project_id: str):
    """Get GPS coordinates from browser using streamlit-js-eval with async geolocation."""
    try:
        from streamlit_js_eval import streamlit_js_eval
        
        gps_js = """
        new Promise((resolve) => {
            const cached = sessionStorage.getItem('gps_coords');
            if (cached && cached !== '') {
                resolve(cached);
                return;
            }
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        const lat = position.coords.latitude.toFixed(6);
                        const lng = position.coords.longitude.toFixed(6);
                        const coords = lat + ', ' + lng;
                        sessionStorage.setItem('gps_coords', coords);
                        resolve(coords);
                    },
                    function(error) {
                        sessionStorage.setItem('gps_coords', '');
                        resolve('');
                    },
                    {enableHighAccuracy: true, timeout: 8000, maximumAge: 300000}
                );
            } else {
                resolve('');
            }
        })
        """
        
        result = streamlit_js_eval(js_expressions=gps_js, key=f"gps_capture_{project_id}")
        return result if result else ""
    except Exception:
        return ""


def render_gps_status(gps_coords: str):
    """Display GPS status indicator."""
    if gps_coords and gps_coords.strip():
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 8px;
                padding: 10px 14px;
                border: 1px solid #00A8E8;
                margin: 4px 0;
            ">
                <span style="font-size: 16px;">✅</span>
                <span style="color: #E5E5E5; font-size: 13px; margin-left: 6px;">GPS: {gps_coords}</span>
            </div>
            ''',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 8px;
                padding: 10px 14px;
                border: 1px solid #778da9;
                margin: 4px 0;
            ">
                <span style="font-size: 16px;">⚠️</span>
                <span style="color: #778da9; font-size: 13px; margin-left: 6px;">GPS unavailable - timestamp only</span>
            </div>
            ''',
            unsafe_allow_html=True
        )


def add_watermark_to_image(img_bytes: bytes, gps_coords: str = None) -> bytes:
    """Add high-contrast timestamp/GPS watermark to image (white text, black outline)."""
    import datetime
    
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    draw = ImageDraw.Draw(img)
    
    now = now_mountain()
    display_time = now.strftime("%b %d, %Y - %I:%M %p") + " MT"
    
    if gps_coords and gps_coords.strip():
        watermark_text = f"{display_time}\nGPS: {gps_coords}"
    else:
        watermark_text = display_time
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    lines = watermark_text.split('\n')
    max_width = 0
    total_height = 0
    for line in lines:
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            max_width = max(max_width, bbox[2] - bbox[0])
            total_height += bbox[3] - bbox[1] + 4
        except:
            max_width = max(max_width, len(line) * 9)
            total_height += 18
    
    padding = 8
    box_x = img.width - max_width - padding * 2 - 10
    box_y = img.height - total_height - padding * 2 - 10
    
    text_y = box_y + padding
    for line in lines:
        text_x = box_x + padding
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    draw.text((text_x + dx, text_y + dy), line, font=font, fill="#000000")
        draw.text((text_x, text_y), line, font=font, fill="#FFFFFF")
        text_y += 18
    
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=95)
    buf.seek(0)
    return buf.getvalue()


def render_folder_linker(project_id: str, client_name: str):
    """Render folder linker when no Drive folder is connected."""
    from views.migration_util import (
        get_drive_access_token, find_drive_folder_fuzzy, 
        update_project_drive_folder, extract_folder_id_from_url
    )
    
    st.markdown(
        '''
        <div style="
            background: linear-gradient(145deg, #1b263b 0%, #0d1b2a 100%);
            border-radius: 12px;
            padding: 16px;
            margin: 16px 0;
            border: 1px dashed #778da9;
        ">
            <p style="color: #778da9; font-size: 14px; margin: 0;">
                📂 No Google Drive folder linked to this project.
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    fuzzy_key = f"fuzzy_search_{project_id}"
    manual_key = f"manual_link_{project_id}"
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Auto-Find Folder", key=f"fuzzy_btn_{project_id}", use_container_width=True):
            st.session_state[fuzzy_key] = True
            st.rerun()
    
    with col2:
        if st.button("🔗 Manual Link", key=f"manual_btn_{project_id}", use_container_width=True):
            st.session_state[manual_key] = True
            st.rerun()
    
    if st.session_state.get(fuzzy_key, False):
        with st.spinner("Searching for matching folder..."):
            access_token, err = get_drive_access_token()
            if err:
                st.error(f"Drive not connected: {err}")
            else:
                folder, err = find_drive_folder_fuzzy(access_token, client_name)
                if folder:
                    folder_name = folder.get("name", "Unknown")
                    folder_id = folder.get("id")
                    folder_link = folder.get("webViewLink", "")
                    
                    st.success(f"Found matching folder: **{folder_name}**")
                    
                    if st.button("✅ Link This Folder", key=f"confirm_link_{project_id}", type="primary"):
                        success, err = update_project_drive_folder(project_id, folder_id, folder_link)
                        if success:
                            st.session_state[fuzzy_key] = False
                            st.rerun()
                        else:
                            st.error(f"Failed to link: {err}")
                    
                    if st.button("Cancel", key=f"cancel_fuzzy_{project_id}"):
                        st.session_state[fuzzy_key] = False
                        st.rerun()
                else:
                    st.warning("No matching folder found. Try manual linking instead.")
                    st.session_state[fuzzy_key] = False
    
    if st.session_state.get(manual_key, False):
        st.markdown('<p style="color: #FFFFFF; font-size: 13px;">Paste a Google Drive folder URL:</p>', unsafe_allow_html=True)
        
        drive_url = st.text_input(
            "Drive URL",
            key=f"drive_url_{project_id}",
            placeholder="https://drive.google.com/drive/folders/...",
            label_visibility="collapsed"
        )
        
        btn_col1, btn_col2 = st.columns(2)
        
        with btn_col1:
            if st.button("✅ Link Folder", key=f"link_manual_{project_id}", type="primary", use_container_width=True):
                if drive_url:
                    folder_id = extract_folder_id_from_url(drive_url)
                    if folder_id:
                        success, err = update_project_drive_folder(project_id, folder_id, drive_url)
                        if success:
                            st.session_state[manual_key] = False
                            st.rerun()
                        else:
                            st.error(f"Failed to link: {err}")
                    else:
                        st.error("Could not extract folder ID from URL")
                else:
                    st.warning("Please paste a Drive URL")
        
        with btn_col2:
            if st.button("Cancel", key=f"cancel_manual_{project_id}", use_container_width=True):
                st.session_state[manual_key] = False
                st.rerun()


def render_block_a_shoebox(project_id: str, client_name: str, drive_folder_id: str = None,
                           master_spec_file_name: str = None, production_locked: bool = False):
    """Block A: The Shoebox - Tri-Category Photo Intake with Zero-Input GPS and Master Spec pinning."""
    from services.database_manager import (
        get_photos_by_categories, save_project_photo, delete_project_photo, get_next_photo_index
    )
    import datetime
    
    if production_locked and master_spec_file_name:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px;
                margin: 0 0 20px 0;
                border: 2px solid #39FF14;
            ">
                <p style="color: #39FF14; font-size: 16px; font-weight: 700; margin: 0 0 8px 0;">
                    📌 MASTER SPEC (Pinned)
                </p>
                <p style="color: #E5E5E5; font-size: 14px; margin: 0 0 4px 0;">
                    <strong>{master_spec_file_name}</strong>
                </p>
                <span style="
                    background: #39FF14; 
                    color: #000; 
                    padding: 4px 10px; 
                    border-radius: 4px; 
                    font-size: 12px; 
                    font-weight: 600;
                ">✅ PRODUCTION READY</span>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        st.markdown(
            '''
            <details style="margin-bottom: 16px;">
                <summary style="
                    color: #888; 
                    cursor: pointer; 
                    padding: 10px; 
                    background: rgba(136, 136, 136, 0.1); 
                    border-radius: 8px;
                    font-size: 14px;
                ">📁 Archive Files (Other Uploads)</summary>
                <div style="opacity: 0.6; padding-top: 12px;">
            ''',
            unsafe_allow_html=True
        )
    
    gps_key = f"auto_gps_{project_id}"
    gps_attempted_key = f"gps_attempted_{project_id}"
    
    browser_gps = get_browser_gps(project_id)
    if browser_gps and browser_gps.strip():
        st.session_state[gps_key] = browser_gps
        st.session_state[gps_attempted_key] = True
    
    gps_coords = st.session_state.get(gps_key, "")
    
    gps_col1, gps_col2 = st.columns([3, 1])
    with gps_col1:
        render_gps_status(gps_coords)
    with gps_col2:
        if st.button("🔄 Refresh GPS", key=f"refresh_gps_{project_id}", use_container_width=True):
            st.session_state[gps_attempted_key] = True
            st.rerun()
    
    with st.expander("📍 Manual GPS Override", expanded=False):
        gps_value = st.text_input(
            "Enter GPS coordinates manually",
            value=gps_coords,
            key=f"gps_manual_{project_id}",
            placeholder="e.g., 32.7157, -117.1611",
            help="Override auto-detected GPS or enter manually"
        )
        if gps_value and gps_value != gps_coords:
            st.session_state[gps_key] = gps_value
            gps_coords = gps_value
    
    st.markdown(
        '''
        <div class="liquid-card" style="
            background: linear-gradient(145deg, #003049 0%, #001d2e 100%);
            border-radius: 20px;
            padding: 24px;
            margin: 16px 0;
            box-shadow: 0 4px 20px rgba(0, 168, 232, 0.25), 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1.5px solid #00A8E8;
        ">
            <h3 style="color: #00A8E8; margin: 0 0 8px 0; font-size: 18px;">Block A: The Shoebox (Intake)</h3>
            <p style="color: #FFFFFF; margin: 0; font-size: 14px;">Upload site photos, logos, and reference images - GPS auto-captured</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
    
    camera_key = f"camera_photo_{project_id}"
    markup_trigger_key = f"trigger_markup_{project_id}"
    
    st.markdown(
        '''
        <div style="
            background: linear-gradient(145deg, #1a3a1a 0%, #0d2a0d 100%);
            border-radius: 12px;
            padding: 16px;
            margin: 0 0 16px 0;
            border: 2px solid #39FF14;
            text-align: center;
        ">
            <p style="color: #39FF14; font-size: 14px; margin: 0 0 8px 0; font-weight: 600;">📸 Field Intelligence</p>
            <p style="color: #E5E5E5; font-size: 12px; margin: 0;">Snap a site photo and markup measurements instantly</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    camera_col1, camera_col2 = st.columns([1, 1])
    
    with camera_col1:
        camera_file = st.file_uploader(
            "📸 Site Photo (Camera)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=False,
            key=f"camera_capture_{project_id}",
            help="On mobile, this opens your camera. Take a photo and it will open the markup tool."
        )
        
        if camera_file:
            st.session_state[camera_key] = camera_file
            st.session_state[markup_trigger_key] = True
    
    with camera_col2:
        if st.session_state.get(camera_key):
            if st.button("📏 Open Markup Tool", key=f"open_camera_markup_{project_id}", type="primary", use_container_width=True):
                st.session_state[markup_trigger_key] = True
                st.rerun()
    
    if st.session_state.get(markup_trigger_key) and st.session_state.get(camera_key):
        render_camera_markup_tool(project_id, client_name, st.session_state[camera_key], gps_coords, safe_name)
    
    st.markdown("<hr style='border: none; border-top: 1px solid #333; margin: 16px 0;'>", unsafe_allow_html=True)
    
    upload_col1, upload_col2, upload_col3 = st.columns(3)
    
    with upload_col1:
        st.markdown('<p style="color: #00A8E8; font-size: 14px; font-weight: 600;">📷 Site Photo</p>', unsafe_allow_html=True)
        site_files = st.file_uploader(
            "Upload site photos",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"site_upload_{project_id}",
            label_visibility="collapsed"
        )
        if site_files:
            save_proceed_key = f"save_proceed_{project_id}"
            
            if not gps_coords and not st.session_state.get(save_proceed_key, False):
                st.warning("⚠️ GPS not captured yet. Click 'Refresh GPS' or proceed without GPS.")
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("🔄 Retry GPS", key=f"retry_gps_save_{project_id}", use_container_width=True):
                        st.rerun()
                with col_b:
                    if st.button("💾 Save without GPS", key=f"save_no_gps_{project_id}", use_container_width=True):
                        st.session_state[save_proceed_key] = True
                        st.rerun()
            else:
                if st.button("💾 Save Site Photos", key=f"save_site_{project_id}", use_container_width=True, type="primary"):
                    saved_count = 0
                    import time
                    for idx, file in enumerate(site_files):
                        timestamp = get_file_timestamp_mountain()
                        filename = f"{safe_name}_Site_{timestamp}.jpg"
                        img_bytes = file.read()
                        watermarked = add_watermark_to_image(img_bytes, gps_coords)
                        if save_project_photo(project_id, filename, watermarked, "site"):
                            saved_count += 1
                        time.sleep(1)
                    if saved_count > 0:
                        st.success(f"✅ Saved {saved_count} site photo(s)")
                        st.session_state[save_proceed_key] = False
                        st.rerun()
    
    with upload_col2:
        st.markdown('<p style="color: #00A8E8; font-size: 14px; font-weight: 600;">🎨 Client Logo</p>', unsafe_allow_html=True)
        logo_files = st.file_uploader(
            "Upload client logos",
            type=["jpg", "jpeg", "png", "svg", "pdf"],
            accept_multiple_files=True,
            key=f"logo_upload_{project_id}",
            label_visibility="collapsed"
        )
        if logo_files:
            if st.button("💾 Save Logos", key=f"save_logo_{project_id}", use_container_width=True, type="primary"):
                saved_count = 0
                for file in logo_files:
                    next_idx = get_next_photo_index(project_id, "logo") + saved_count
                    ext = file.name.split('.')[-1].lower() if '.' in file.name else 'jpg'
                    filename = f"{safe_name}_Logo_{next_idx}.{ext}"
                    img_bytes = file.read()
                    if save_project_photo(project_id, filename, img_bytes, "logo"):
                        saved_count += 1
                if saved_count > 0:
                    st.success(f"✅ Saved {saved_count} logo(s)")
                    st.rerun()
    
    with upload_col3:
        st.markdown('<p style="color: #00A8E8; font-size: 14px; font-weight: 600;">💡 Reference/Inspo</p>', unsafe_allow_html=True)
        ref_files = st.file_uploader(
            "Upload reference images",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"ref_upload_{project_id}",
            label_visibility="collapsed"
        )
        if ref_files:
            if st.button("💾 Save References", key=f"save_ref_{project_id}", use_container_width=True, type="primary"):
                saved_count = 0
                for file in ref_files:
                    next_idx = get_next_photo_index(project_id, "reference") + saved_count
                    filename = f"{safe_name}_Ref_{next_idx}.jpg"
                    img_bytes = file.read()
                    if save_project_photo(project_id, filename, img_bytes, "reference"):
                        saved_count += 1
                if saved_count > 0:
                    st.success(f"✅ Saved {saved_count} reference(s)")
                    st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    all_site_files = site_files if site_files else []
    if all_site_files:
        render_photo_markup_tool(project_id, client_name, all_site_files)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    photos_by_cat = get_photos_by_categories(project_id)
    
    site_photos = photos_by_cat.get("site", []) + photos_by_cat.get("markup", [])
    if site_photos:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 12px 16px;
                margin: 16px 0 8px 0;
                border: 1.5px solid #00A8E8;
            ">
                <p style="color: #00A8E8; font-size: 15px; margin: 0; font-weight: 600;">🏗️ Site Survey ({len(site_photos)})</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        render_photo_gallery(site_photos, "site", project_id, drive_folder_id)
    
    logo_photos = photos_by_cat.get("logo", [])
    if logo_photos:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 12px 16px;
                margin: 16px 0 8px 0;
                border: 1.5px solid #00A8E8;
            ">
                <p style="color: #00A8E8; font-size: 15px; margin: 0; font-weight: 600;">🎨 Brand Assets ({len(logo_photos)})</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        render_photo_gallery(logo_photos, "logo", project_id, drive_folder_id)
    
    ref_photos = photos_by_cat.get("reference", [])
    if ref_photos:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 12px 16px;
                margin: 16px 0 8px 0;
                border: 1.5px solid #00A8E8;
            ">
                <p style="color: #00A8E8; font-size: 15px; margin: 0; font-weight: 600;">💡 Inspiration ({len(ref_photos)})</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        render_photo_gallery(ref_photos, "reference", project_id, drive_folder_id)
    
    if not site_photos and not logo_photos and not ref_photos:
        st.markdown(
            '<p style="color: #778da9; font-size: 13px; font-style: italic; margin: 16px 0;">No photos saved yet. Upload files above to get started.</p>',
            unsafe_allow_html=True
        )
    
    if drive_folder_id:
        from views.migration_util import render_legacy_thumbnails, render_legacy_pdfs
        render_legacy_thumbnails(project_id, drive_folder_id)
        render_legacy_pdfs(project_id, drive_folder_id)
    else:
        render_folder_linker(project_id, client_name)


def render_photo_gallery(photos: list, category: str, project_id: str, drive_folder_id: str = None):
    """Render a photo gallery with download, archive, and delete buttons."""
    from services.database_manager import delete_project_photo
    
    cols = st.columns(3)
    for idx, photo in enumerate(photos):
        with cols[idx % 3]:
            photo_bytes = bytes(photo["file_data"]) if isinstance(photo["file_data"], memoryview) else photo["file_data"]
            
            created_at = photo.get("created_at")
            if created_at:
                caption = created_at.strftime("%b %d, %Y - %I:%M %p")
            else:
                caption = photo.get("filename", "Photo")
            
            st.image(io.BytesIO(photo_bytes), caption=caption, use_container_width=True)
            
            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                st.download_button(
                    label="📥",
                    data=photo_bytes,
                    file_name=photo["filename"],
                    mime="image/jpeg",
                    key=f"dl_{category}_{photo['id']}",
                    use_container_width=True
                )
            with btn_col2:
                if drive_folder_id:
                    if st.button("📦", key=f"arch_{category}_{photo['id']}", use_container_width=True, help="Archive to Drive"):
                        from views.migration_util import archive_drive_file
                        success, err = archive_drive_file(photo["id"], drive_folder_id)
                        if success:
                            if delete_project_photo(photo["id"]):
                                st.success("Archived")
                                st.rerun()
                        else:
                            st.error(f"Archive failed: {err}")
            with btn_col3:
                if st.button("🗑️", key=f"del_{category}_{photo['id']}", use_container_width=True):
                    if delete_project_photo(photo["id"]):
                        st.success("Deleted")
                        st.rerun()


def render_camera_markup_tool(project_id: str, client_name: str, camera_file, gps_coords: str, safe_name: str):
    """Render the camera markup tool that auto-opens and saves with MT timestamp."""
    from services.database_manager import save_project_photo
    
    st.markdown(
        '''
        <style>
        .stCanvasToolbar button {
            background-color: #1a2a3a !important;
            color: #E5E5E5 !important;
            border: 1px solid #39FF14 !important;
        }
        .stCanvasToolbar button:hover {
            background-color: #39FF14 !important;
            color: #000 !important;
        }
        </style>
        <div class="liquid-card" style="
            background: linear-gradient(145deg, #1a3a1a 0%, #0d2a0d 100%);
            border-radius: 16px;
            padding: 20px;
            margin: 16px 0;
            box-shadow: 0 4px 16px rgba(57, 255, 20, 0.2);
            border: 1.5px solid #39FF14;
        ">
            <h4 style="color: #39FF14; margin: 0 0 8px 0; font-size: 16px;">📸 Field Intelligence Markup</h4>
            <p style="color: #E5E5E5; margin: 0; font-size: 13px;">Draw lines and add measurements to your site photo</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    try:
        img = Image.open(camera_file)
    except Exception as e:
        st.error(f"Could not open image: {e}")
        return
    
    max_width = 700
    aspect_ratio = img.height / img.width
    canvas_width = min(img.width, max_width)
    canvas_height = int(canvas_width * aspect_ratio)
    
    img_resized = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
    
    st.markdown(
        '<p style="color: #FFFFFF; font-size: 14px; margin: 16px 0 8px 0;">🎨 Drawing Tools:</p>',
        unsafe_allow_html=True
    )
    
    active_lane_key = f"camera_active_lane_{project_id}"
    if active_lane_key not in st.session_state:
        st.session_state[active_lane_key] = "width"
    
    btn_col1, btn_col2, tool_col1, tool_col2 = st.columns([1.2, 1.2, 1, 1])
    
    with btn_col1:
        width_active = st.session_state[active_lane_key] == "width"
        if st.button("🟠 Draw Width", key=f"camera_width_btn_{project_id}", use_container_width=True, type="primary" if width_active else "secondary"):
            st.session_state[active_lane_key] = "width"
            st.rerun()
    
    with btn_col2:
        height_active = st.session_state[active_lane_key] == "height"
        if st.button("🟢 Draw Height", key=f"camera_height_btn_{project_id}", use_container_width=True, type="primary" if height_active else "secondary"):
            st.session_state[active_lane_key] = "height"
            st.rerun()
    
    if st.session_state[active_lane_key] == "width":
        stroke_color = "#FF8C00"
        active_label = "🟠 WIDTH MODE - Drawing Orange Lines"
    else:
        stroke_color = "#39FF14"
        active_label = "🟢 HEIGHT MODE - Drawing Green Lines"
    
    st.markdown(
        f'<p style="color: {stroke_color}; font-size: 12px; font-weight: bold; margin: 4px 0; text-align: center;">{active_label}</p>',
        unsafe_allow_html=True
    )
    
    with tool_col1:
        drawing_mode = st.selectbox(
            "Mode",
            ["line", "freedraw", "rect"],
            format_func=lambda x: {"freedraw": "✏️ Freehand", "line": "📏 Line", "rect": "⬜ Rectangle"}[x],
            key=f"camera_draw_mode_{project_id}"
        )
    
    with tool_col2:
        stroke_width = st.slider(
            "Width",
            min_value=1,
            max_value=10,
            value=3,
            key=f"camera_stroke_width_{project_id}"
        )
    
    st.markdown(
        '''
        <div style="
            background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
            border-radius: 12px;
            padding: 12px 16px;
            margin: 12px 0;
            border: 1.5px solid #39FF14;
        ">
            <p style="color: #E5E5E5; font-size: 13px; margin: 0;">📐 Enter measurements (optional):</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    meas_col1, meas_col2 = st.columns(2)
    
    with meas_col1:
        lane1_text = st.text_input(
            "🟠 Width Measurement",
            value="",
            placeholder="e.g., 24 ft",
            key=f"camera_lane1_text_{project_id}"
        )
    
    with meas_col2:
        lane2_text = st.text_input(
            "🟢 Height Measurement",
            value="",
            placeholder="e.g., 8 ft",
            key=f"camera_lane2_text_{project_id}"
        )
    
    st.markdown(
        '''
        <div style="
            background: #1a2a3a;
            border-radius: 12px;
            padding: 8px;
            margin: 8px 0;
            border: 1.5px solid #39FF14;
        ">
        ''',
        unsafe_allow_html=True
    )
    
    canvas_result = st_canvas(
        fill_color="rgba(57, 255, 20, 0.1)",
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_image=img_resized,
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        key=f"camera_canvas_{project_id}",
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    save_col, close_col = st.columns(2)
    
    with save_col:
        if st.button("💾 Save & Complete", key=f"save_camera_markup_{project_id}", type="primary", use_container_width=True):
            if canvas_result.image_data is not None:
                result_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                
                composite = Image.new('RGBA', img_resized.size, (255, 255, 255, 255))
                img_rgba = img_resized.convert('RGBA')
                composite = Image.alpha_composite(composite, img_rgba)
                composite = Image.alpha_composite(composite, result_image)
                
                final_image = composite.convert('RGB')
                draw = ImageDraw.Draw(final_image)
                
                if lane1_text.strip():
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                    except:
                        font = ImageFont.load_default()
                    
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                draw.text((20 + dx, canvas_height - 60 + dy), lane1_text, font=font, fill="#000000")
                    draw.text((20, canvas_height - 60), lane1_text, font=font, fill="#FF8C00")
                
                if lane2_text.strip():
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                    except:
                        font = ImageFont.load_default()
                    
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                draw.text((20 + dx, canvas_height - 30 + dy), lane2_text, font=font, fill="#000000")
                    draw.text((20, canvas_height - 30), lane2_text, font=font, fill="#39FF14")
                
                now = now_mountain()
                display_time = f"{now.strftime('%b %d, %Y - %I:%M %p')} MT"
                
                try:
                    wm_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                except:
                    wm_font = ImageFont.load_default()
                
                watermark_text = display_time
                if gps_coords:
                    watermark_text = f"{display_time}\nGPS: {gps_coords}"
                
                try:
                    lines = watermark_text.split('\n')
                    max_width_wm = 0
                    total_height = 0
                    for line in lines:
                        bbox = draw.textbbox((0, 0), line, font=wm_font)
                        max_width_wm = max(max_width_wm, bbox[2] - bbox[0])
                        total_height += bbox[3] - bbox[1] + 2
                except:
                    max_width_wm = len(display_time) * 7
                    total_height = 14
                
                padding = 6
                box_w = max_width_wm + padding * 2
                box_h = total_height + padding * 2
                box_x = canvas_width - box_w - 8
                box_y = 8
                
                overlay = Image.new('RGBA', final_image.size, (0, 0, 0, 0))
                overlay_draw = ImageDraw.Draw(overlay)
                overlay_draw.rectangle(
                    [(box_x, box_y), (box_x + box_w, box_y + box_h)],
                    fill=(0, 48, 73, 180)
                )
                
                img_rgba = final_image.convert('RGBA')
                img_with_box = Image.alpha_composite(img_rgba, overlay)
                
                final_draw = ImageDraw.Draw(img_with_box)
                text_y = box_y + padding
                for line in watermark_text.split('\n'):
                    final_draw.text((box_x + padding, text_y), line, font=wm_font, fill=(229, 229, 229, 255))
                    text_y += 14
                
                final_image = img_with_box.convert('RGB')
                
                timestamp = get_file_timestamp_mountain()
                filename = f"{safe_name}_FieldPhoto_{timestamp}.jpg"
                
                buf = io.BytesIO()
                final_image.save(buf, format='JPEG', quality=95)
                buf.seek(0)
                image_bytes = buf.getvalue()
                
                if save_project_photo(project_id, filename, image_bytes, "markup"):
                    st.success(f"✅ Saved: {filename}")
                    st.session_state[f"camera_photo_{project_id}"] = None
                    st.session_state[f"trigger_markup_{project_id}"] = False
                    st.rerun()
                else:
                    st.error("Failed to save photo to database")
            else:
                st.warning("Draw on the canvas first before saving.")
    
    with close_col:
        if st.button("Cancel", key=f"cancel_camera_markup_{project_id}", use_container_width=True):
            st.session_state[f"camera_photo_{project_id}"] = None
            st.session_state[f"trigger_markup_{project_id}"] = False
            st.rerun()


def render_photo_markup_tool(project_id: str, client_name: str, uploaded_files: list):
    """Render the photo markup tool for adding measurements to site photos."""
    
    markup_key = f"show_markup_{project_id}"
    selected_photo_key = f"markup_photo_{project_id}"
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if st.button("📏 Markup Photo", key=f"open_markup_{project_id}", type="primary", use_container_width=True):
            st.session_state[markup_key] = True
            st.rerun()
    
    if st.session_state.get(markup_key, False):
        st.markdown(
            '''
            <style>
            /* Make st_canvas action buttons visible on dark UI */
            .stCanvasToolbar button {
                background-color: #1a2a3a !important;
                color: #E5E5E5 !important;
                border: 1px solid #00A8E8 !important;
            }
            .stCanvasToolbar button:hover {
                background-color: #00A8E8 !important;
                color: #000 !important;
            }
            div[data-testid="stDrawableCanvas"] button {
                background-color: #1a2a3a !important;
                color: #E5E5E5 !important;
                border: 1px solid #00A8E8 !important;
            }
            /* Canvas control buttons - Undo, Redo, Clear */
            .canvas-toolbar button,
            [class*="CanvasToolbar"] button,
            div[class*="canvas"] button {
                background-color: #1a2a3a !important;
                color: #FFFFFF !important;
                border: 1px solid #00A8E8 !important;
                padding: 4px 8px !important;
            }
            </style>
            <div class="liquid-card" style="
                background: linear-gradient(145deg, #0d1b2a 0%, #1b263b 100%);
                border-radius: 16px;
                padding: 20px;
                margin: 16px 0;
                box-shadow: 0 4px 16px rgba(0, 168, 232, 0.2);
                border: 1.5px solid #00A8E8;
            ">
                <h4 style="color: #00A8E8; margin: 0 0 8px 0; font-size: 16px;">📏 Photo Markup Tool</h4>
                <p style="color: #E5E5E5; margin: 0; font-size: 13px;">Draw lines and add measurements to your site photos</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        photo_options = [f.name for f in uploaded_files]
        selected_idx = st.selectbox(
            "Select photo to markup",
            range(len(photo_options)),
            format_func=lambda x: photo_options[x],
            key=f"photo_select_{project_id}"
        )
        
        if selected_idx is not None:
            selected_file = uploaded_files[selected_idx]
            
            img = Image.open(selected_file)
            
            max_width = 700
            aspect_ratio = img.height / img.width
            canvas_width = min(img.width, max_width)
            canvas_height = int(canvas_width * aspect_ratio)
            
            img_resized = img.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
            st.markdown(
                '<p style="color: #FFFFFF; font-size: 14px; margin: 16px 0 8px 0;">🎨 Drawing Tools:</p>',
                unsafe_allow_html=True
            )
            
            active_lane_key = f"active_lane_{project_id}"
            if active_lane_key not in st.session_state:
                st.session_state[active_lane_key] = "width"
            
            btn_col1, btn_col2, tool_col1, tool_col2 = st.columns([1.2, 1.2, 1, 1])
            
            with btn_col1:
                width_active = st.session_state[active_lane_key] == "width"
                width_style = "background: #FF8C00; color: #000;" if width_active else "background: #1a2a3a; color: #FF8C00; border: 2px solid #FF8C00;"
                if st.button("🟠 Draw Width", key=f"width_btn_{project_id}", use_container_width=True, type="primary" if width_active else "secondary"):
                    st.session_state[active_lane_key] = "width"
                    st.rerun()
            
            with btn_col2:
                height_active = st.session_state[active_lane_key] == "height"
                height_style = "background: #39FF14; color: #000;" if height_active else "background: #1a2a3a; color: #39FF14; border: 2px solid #39FF14;"
                if st.button("🟢 Draw Height", key=f"height_btn_{project_id}", use_container_width=True, type="primary" if height_active else "secondary"):
                    st.session_state[active_lane_key] = "height"
                    st.rerun()
            
            if st.session_state[active_lane_key] == "width":
                stroke_color = "#FF8C00"
                active_label = "🟠 WIDTH MODE - Drawing Orange Lines"
            else:
                stroke_color = "#39FF14"
                active_label = "🟢 HEIGHT MODE - Drawing Green Lines"
            
            st.markdown(
                f'<p style="color: {stroke_color}; font-size: 12px; font-weight: bold; margin: 4px 0; text-align: center;">{active_label}</p>',
                unsafe_allow_html=True
            )
            
            with tool_col1:
                drawing_mode = st.selectbox(
                    "Mode",
                    ["line", "freedraw", "rect"],
                    format_func=lambda x: {"freedraw": "✏️ Freehand", "line": "📏 Line", "rect": "⬜ Rectangle"}[x],
                    key=f"draw_mode_{project_id}"
                )
            
            with tool_col2:
                stroke_width = st.slider(
                    "Width",
                    min_value=1,
                    max_value=10,
                    value=3,
                    key=f"stroke_width_{project_id}"
                )
            
            def hex_to_rgb(hex_color):
                """Convert hex color to RGB tuple."""
                hex_color = hex_color.lstrip('#')
                if len(hex_color) == 6:
                    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                return (0, 0, 0)
            
            def is_fuzzy_orange(hex_color):
                """Fuzzy detection: High Red, Medium Green, Low Blue = Orange."""
                r, g, b = hex_to_rgb(hex_color)
                return r >= 200 and 50 <= g <= 180 and b <= 100
            
            def is_fuzzy_green(hex_color):
                """Fuzzy detection: High Green, Low Red = Neon Green."""
                r, g, b = hex_to_rgb(hex_color)
                return g >= 200 and r <= 100
            
            def get_line_midpoint_by_color(json_data, target_color, img_width, img_height):
                """Extract line midpoint for a specific stroke color using fuzzy matching. Returns (x, y) or None."""
                if not json_data or "objects" not in json_data:
                    return None
                
                is_orange_target = target_color.upper() in ["#FF8C00", "#FFA500", "#FF7F00", "#FF6600"] or is_fuzzy_orange(target_color)
                is_green_target = target_color.upper() in ["#39FF14", "#00FF00", "#32CD32", "#7CFC00"] or is_fuzzy_green(target_color)
                
                for obj in json_data.get("objects", []):
                    obj_stroke = obj.get("stroke", "")
                    if not obj_stroke:
                        continue
                    
                    stroke_is_orange = is_fuzzy_orange(obj_stroke)
                    stroke_is_green = is_fuzzy_green(obj_stroke)
                    
                    color_match = False
                    if is_orange_target and stroke_is_orange:
                        color_match = True
                    elif is_green_target and stroke_is_green:
                        color_match = True
                    
                    if not color_match:
                        continue
                    
                    if obj.get("type") == "line":
                        x1 = obj.get("x1", 0) + obj.get("left", 0)
                        y1 = obj.get("y1", 0) + obj.get("top", 0)
                        x2 = obj.get("x2", 0) + obj.get("left", 0)
                        y2 = obj.get("y2", 0) + obj.get("top", 0)
                        return (int((x1 + x2) / 2), int((y1 + y2) / 2))
                    elif obj.get("type") == "path":
                        path = obj.get("path", [])
                        if len(path) >= 2:
                            start, end = path[0], path[-1]
                            if len(start) >= 3 and len(end) >= 3:
                                left, top = obj.get("left", 0), obj.get("top", 0)
                                x1, y1 = start[1] + left, start[2] + top
                                x2, y2 = end[1] + left, end[2] + top
                                return (int((x1 + x2) / 2), int((y1 + y2) / 2))
                
                return None
            
            def get_lane_placement(json_data, lane_color, img_width, img_height, font_size, lane_num, text_width=0):
                """Get text placement for a specific lane with offset positioning.
                Orange (Lane 1): Text centered horizontally, just BELOW the line midpoint.
                Green (Lane 2): Text centered vertically, just to the RIGHT of the line midpoint.
                """
                midpoint = get_line_midpoint_by_color(json_data, lane_color, img_width, img_height)
                
                if midpoint:
                    if lane_num == 1:
                        offset_x = midpoint[0]
                        offset_y = midpoint[1] + font_size + 5
                        return (offset_x, offset_y), "midpoint"
                    else:
                        offset_x = midpoint[0] + 10
                        offset_y = midpoint[1]
                        return (offset_x, offset_y), "midpoint"
                else:
                    margin = 20
                    base_y = img_height - font_size - margin
                    if lane_num == 2:
                        base_y = base_y - font_size - 15
                    return (margin, base_y), "bottom-left"
            
            st.markdown(
                '''
                <div style="
                    background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                    border-radius: 12px;
                    padding: 12px 16px;
                    margin: 12px 0;
                    border: 1.5px solid #00A8E8;
                ">
                    <p style="color: #E5E5E5; font-size: 13px; margin: 0;">📐 Enter measurements (leave blank to skip):</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            meas_col1, meas_col2, meas_col3, meas_col4 = st.columns([2, 1, 2, 1])
            
            with meas_col1:
                lane1_text = st.text_input(
                    "🟠 Width",
                    value="",
                    placeholder="e.g., 24 ft",
                    key=f"lane1_text_{project_id}"
                )
            with meas_col2:
                lane1_size = st.slider(
                    "Size",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key=f"lane1_size_{project_id}"
                )
            
            with meas_col3:
                lane2_text = st.text_input(
                    "🟢 Height",
                    value="",
                    placeholder="e.g., 8 ft",
                    key=f"lane2_text_{project_id}"
                )
            with meas_col4:
                lane2_size = st.slider(
                    "Size",
                    min_value=1,
                    max_value=20,
                    value=5,
                    key=f"lane2_size_{project_id}"
                )
            
            show_lane2 = bool(lane2_text.strip())
            
            preview_key = f"show_preview_{project_id}"
            if preview_key not in st.session_state:
                st.session_state[preview_key] = False
            
            st.markdown(
                '''
                <div style="
                    background: #1a2a3a;
                    border-radius: 12px;
                    padding: 8px;
                    margin: 8px 0;
                    border: 1.5px solid #00A8E8;
                ">
                ''',
                unsafe_allow_html=True
            )
            
            canvas_result = st_canvas(
                fill_color="rgba(0, 168, 232, 0.1)",
                stroke_width=stroke_width,
                stroke_color=stroke_color,
                background_image=img_resized,
                update_streamlit=True,
                height=canvas_height,
                width=canvas_width,
                drawing_mode=drawing_mode,
                key=f"canvas_{project_id}",
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            preview_col, spacer_col = st.columns([1, 2])
            with preview_col:
                show_preview_clicked = st.button("🔍 Show Preview", key=f"preview_btn_{project_id}", use_container_width=True)
                if show_preview_clicked:
                    st.session_state[preview_key] = True
            
            has_text = lane1_text.strip() or (show_lane2 and lane2_text.strip())
            should_show_preview = st.session_state.get(preview_key, False) and has_text
            
            if should_show_preview:
                st.markdown(
                    '''
                    <div style="
                        background: linear-gradient(145deg, #003049 0%, #001d2e 100%);
                        border-radius: 12px;
                        padding: 12px;
                        margin: 12px 0;
                        border: 1.5px solid #00A8E8;
                        box-shadow: 0 4px 16px rgba(0, 168, 232, 0.25);
                    ">
                        <p style="color: #00A8E8; font-size: 14px; margin: 0 0 8px 0; font-weight: 600;">👁️ Text Placement Preview</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                
                preview_img = img_resized.copy().convert('RGB')
                preview_draw = ImageDraw.Draw(preview_img)
                
                json_data = canvas_result.json_data if hasattr(canvas_result, 'json_data') else None
                
                orange_count = 0
                green_count = 0
                width_line_found = False
                height_line_found = False
                
                if json_data and "objects" in json_data:
                    for obj in json_data.get("objects", []):
                        obj_stroke = obj.get("stroke", "")
                        if obj_stroke and is_fuzzy_orange(obj_stroke):
                            orange_count += 1
                            width_line_found = True
                        elif obj_stroke and is_fuzzy_green(obj_stroke):
                            green_count += 1
                            height_line_found = True
                
                st.caption(f"📊 Fuzzy detection: 🟠 Orange strokes: {orange_count} | 🟢 Green strokes: {green_count}")
                
                placement_info = []
                
                if lane1_text.strip():
                    font_size_1 = int(canvas_height * (lane1_size / 100))
                    font_size_1 = max(12, font_size_1)
                    
                    try:
                        font_1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_1)
                    except:
                        font_1 = ImageFont.load_default()
                    
                    try:
                        bbox = preview_draw.textbbox((0, 0), lane1_text, font=font_1)
                        text_w1, text_h1 = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    except:
                        text_w1, text_h1 = int(len(lane1_text) * font_size_1 * 0.6), font_size_1
                    
                    pos1, ptype1 = get_lane_placement(json_data, "#FF8C00", canvas_width, canvas_height, font_size_1, 1, text_w1)
                    
                    if ptype1 == "midpoint":
                        tx1 = pos1[0] - text_w1 // 2
                        ty1 = pos1[1]
                    else:
                        tx1, ty1 = pos1[0], pos1[1]
                    
                    tx1 = max(5, min(tx1, canvas_width - text_w1 - 5))
                    ty1 = max(5, min(ty1, canvas_height - text_h1 - 5))
                    
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                preview_draw.text((tx1 + dx, ty1 + dy), lane1_text, font=font_1, fill="#000000")
                    preview_draw.text((tx1, ty1), lane1_text, font=font_1, fill="#FF8C00")
                    
                    placement_info.append(f"Width: {'Found' if width_line_found else 'Not Found'}")
                
                if show_lane2 and lane2_text.strip():
                    font_size_2 = int(canvas_height * (lane2_size / 100))
                    font_size_2 = max(12, font_size_2)
                    
                    try:
                        font_2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_2)
                    except:
                        font_2 = ImageFont.load_default()
                    
                    try:
                        bbox = preview_draw.textbbox((0, 0), lane2_text, font=font_2)
                        text_w2, text_h2 = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    except:
                        text_w2, text_h2 = int(len(lane2_text) * font_size_2 * 0.6), font_size_2
                    
                    pos2, ptype2 = get_lane_placement(json_data, "#39FF14", canvas_width, canvas_height, font_size_2, 2, text_w2)
                    
                    if ptype2 == "midpoint":
                        tx2 = pos2[0]
                        ty2 = pos2[1] - text_h2 // 2
                    else:
                        tx2, ty2 = pos2[0], pos2[1]
                    
                    tx2 = max(5, min(tx2, canvas_width - text_w2 - 5))
                    ty2 = max(5, min(ty2, canvas_height - text_h2 - 5))
                    
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                preview_draw.text((tx2 + dx, ty2 + dy), lane2_text, font=font_2, fill="#000000")
                    preview_draw.text((tx2, ty2), lane2_text, font=font_2, fill="#39FF14")
                    
                    placement_info.append(f"Height: {'Found' if height_line_found else 'Not Found'}")
                
                try:
                    debug_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
                except:
                    debug_font = ImageFont.load_default()
                
                width_status = "Found" if width_line_found else "Not Found"
                height_status = "Found" if height_line_found else "Not Found"
                debug_text = f"Width Line: {width_status} | Height Line: {height_status}"
                
                debug_y = canvas_height - 18
                preview_draw.rectangle([(0, debug_y - 2), (canvas_width, canvas_height)], fill="#001d2e")
                preview_draw.text((5, debug_y), debug_text, font=debug_font, fill="#00A8E8")
                
                preview_buf = io.BytesIO()
                preview_img.save(preview_buf, format='PNG')
                preview_buf.seek(0)
                
                st.image(preview_buf, caption="Preview with debug status bar", use_container_width=True)
            
            save_col1, save_col2, close_col = st.columns([1, 1, 1])
            
            with save_col1:
                if st.button("💾 Save Markup", key=f"save_markup_{project_id}", type="primary", use_container_width=True):
                    if canvas_result.image_data is not None:
                        result_image = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                        
                        composite = Image.new('RGBA', img_resized.size, (255, 255, 255, 255))
                        img_rgba = img_resized.convert('RGBA')
                        composite = Image.alpha_composite(composite, img_rgba)
                        composite = Image.alpha_composite(composite, result_image)
                        
                        final_image = composite.convert('RGB')
                        draw = ImageDraw.Draw(final_image)
                        
                        json_data = canvas_result.json_data if hasattr(canvas_result, 'json_data') else None
                        
                        lane1_text_val = st.session_state.get(f"lane1_text_{project_id}", "")
                        lane1_size_val = st.session_state.get(f"lane1_size_{project_id}", 5)
                        lane2_text_val = st.session_state.get(f"lane2_text_{project_id}", "")
                        lane2_size_val = st.session_state.get(f"lane2_size_{project_id}", 5)
                        
                        if lane1_text_val.strip():
                            font_size_1 = int(canvas_height * (lane1_size_val / 100))
                            font_size_1 = max(12, font_size_1)
                            
                            try:
                                font_1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_1)
                            except:
                                font_1 = ImageFont.load_default()
                            
                            try:
                                bbox = draw.textbbox((0, 0), lane1_text_val, font=font_1)
                                text_w1, text_h1 = bbox[2] - bbox[0], bbox[3] - bbox[1]
                            except:
                                text_w1, text_h1 = int(len(lane1_text_val) * font_size_1 * 0.6), font_size_1
                            
                            pos1, ptype1 = get_lane_placement(json_data, "#FF8C00", canvas_width, canvas_height, font_size_1, 1, text_w1)
                            
                            if ptype1 == "midpoint":
                                tx1 = pos1[0] - text_w1 // 2
                                ty1 = pos1[1]
                            else:
                                tx1, ty1 = pos1[0], pos1[1]
                            
                            tx1 = max(5, min(tx1, canvas_width - text_w1 - 5))
                            ty1 = max(5, min(ty1, canvas_height - text_h1 - 5))
                            
                            for dx in [-2, -1, 0, 1, 2]:
                                for dy in [-2, -1, 0, 1, 2]:
                                    if dx != 0 or dy != 0:
                                        draw.text((tx1 + dx, ty1 + dy), lane1_text_val, font=font_1, fill="#000000")
                            draw.text((tx1, ty1), lane1_text_val, font=font_1, fill="#FF8C00")
                        
                        if lane2_text_val.strip():
                            font_size_2 = int(canvas_height * (lane2_size_val / 100))
                            font_size_2 = max(12, font_size_2)
                            
                            try:
                                font_2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size_2)
                            except:
                                font_2 = ImageFont.load_default()
                            
                            try:
                                bbox = draw.textbbox((0, 0), lane2_text_val, font=font_2)
                                text_w2, text_h2 = bbox[2] - bbox[0], bbox[3] - bbox[1]
                            except:
                                text_w2, text_h2 = int(len(lane2_text_val) * font_size_2 * 0.6), font_size_2
                            
                            pos2, ptype2 = get_lane_placement(json_data, "#39FF14", canvas_width, canvas_height, font_size_2, 2, text_w2)
                            
                            if ptype2 == "midpoint":
                                tx2 = pos2[0]
                                ty2 = pos2[1] - text_h2 // 2
                            else:
                                tx2, ty2 = pos2[0], pos2[1]
                            
                            tx2 = max(5, min(tx2, canvas_width - text_w2 - 5))
                            ty2 = max(5, min(ty2, canvas_height - text_h2 - 5))
                            
                            for dx in [-2, -1, 0, 1, 2]:
                                for dy in [-2, -1, 0, 1, 2]:
                                    if dx != 0 or dy != 0:
                                        draw.text((tx2 + dx, ty2 + dy), lane2_text_val, font=font_2, fill="#000000")
                            draw.text((tx2, ty2), lane2_text_val, font=font_2, fill="#39FF14")
                        
                        safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).rstrip().replace(' ', '_')
                        now = now_mountain()
                        timestamp = now.strftime("%Y%m%d_%H%M%S")
                        filename = f"{safe_name}_Site_Markup_{timestamp}.jpg"
                        
                        def add_metadata_watermark(img, gps_coords=None):
                            """Add semi-transparent watermark with timestamp and GPS to bottom-right corner."""
                            draw_wm = ImageDraw.Draw(img, 'RGBA')
                            
                            display_time = now.strftime("%b %d, %Y - %I:%M %p")
                            
                            if gps_coords:
                                watermark_text = f"{display_time}\nGPS: {gps_coords}"
                            else:
                                watermark_text = display_time
                            
                            try:
                                wm_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
                            except:
                                wm_font = ImageFont.load_default()
                            
                            try:
                                lines = watermark_text.split('\n')
                                max_width = 0
                                total_height = 0
                                for line in lines:
                                    bbox = draw_wm.textbbox((0, 0), line, font=wm_font)
                                    max_width = max(max_width, bbox[2] - bbox[0])
                                    total_height += bbox[3] - bbox[1] + 2
                            except:
                                max_width = len(display_time) * 7
                                total_height = 14
                            
                            padding = 6
                            box_w = max_width + padding * 2
                            box_h = total_height + padding * 2
                            box_x = img.width - box_w - 8
                            box_y = img.height - box_h - 8
                            
                            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                            overlay_draw = ImageDraw.Draw(overlay)
                            overlay_draw.rectangle(
                                [(box_x, box_y), (box_x + box_w, box_y + box_h)],
                                fill=(0, 48, 73, 180)
                            )
                            
                            img_rgba = img.convert('RGBA')
                            img_with_box = Image.alpha_composite(img_rgba, overlay)
                            
                            final_draw = ImageDraw.Draw(img_with_box)
                            text_y = box_y + padding
                            for line in watermark_text.split('\n'):
                                final_draw.text((box_x + padding, text_y), line, font=wm_font, fill=(229, 229, 229, 255))
                                text_y += 14
                            
                            return img_with_box.convert('RGB')
                        
                        gps_coords = st.session_state.get(f"auto_gps_{project_id}", "")
                        final_image = add_metadata_watermark(final_image, gps_coords)
                        
                        buf = io.BytesIO()
                        final_image.save(buf, format='JPEG', quality=95)
                        buf.seek(0)
                        image_bytes = buf.getvalue()
                        
                        st.session_state[f"marked_up_image_{project_id}"] = image_bytes
                        st.session_state[f"marked_up_filename_{project_id}"] = filename
                        
                        from services.database_manager import save_project_photo
                        if save_project_photo(project_id, filename, image_bytes, "markup"):
                            st.success(f"✅ Markup saved to database: {filename}")
                            st.session_state[f"photos_updated_{project_id}"] = True
                            st.rerun()
                        else:
                            st.warning(f"⚠️ Saved locally but database save failed: {filename}")
                    else:
                        st.warning("Draw on the canvas first before saving.")
            
            with save_col2:
                if f"marked_up_image_{project_id}" in st.session_state:
                    st.download_button(
                        label="📥 Download Markup",
                        data=st.session_state[f"marked_up_image_{project_id}"],
                        file_name=st.session_state.get(f"marked_up_filename_{project_id}", "markup.jpg"),
                        mime="image/jpeg",
                        use_container_width=True,
                        key=f"download_markup_{project_id}"
                    )
            
            with close_col:
                if st.button("❌ Close", key=f"close_markup_{project_id}", use_container_width=True):
                    st.session_state[markup_key] = False
                    st.rerun()
            
            if f"marked_up_image_{project_id}" in st.session_state:
                st.markdown(
                    '<p style="color: #00A8E8; font-size: 14px; margin: 16px 0 8px 0;">✅ Saved Markup Preview:</p>',
                    unsafe_allow_html=True
                )
                st.image(
                    st.session_state[f"marked_up_image_{project_id}"],
                    caption=st.session_state.get(f"marked_up_filename_{project_id}", "Markup"),
                    use_container_width=True
                )
    
    if production_locked and master_spec_file_name:
        st.markdown(
            '''
                </div>
            </details>
            ''',
            unsafe_allow_html=True
        )


def render_block_b_design_loop(project_id: str, client_name: str, notes: str, google_drive_link: str, design_proof_drive_id: str = "", design_proof_name: str = "", no_design_required: bool = False, status: str = "") -> bool:
    """Block B: The Design Loop - Matt's workflow. Returns True if design is uploaded or not required."""
    from services.database_manager import get_photos_by_categories
    
    has_assigned_design = bool(design_proof_drive_id)
    
    # Check if status is Design or higher (email already sent)
    status_lower = (status or "").lower().replace(" ", "_").replace("-", "_")
    design_or_higher_statuses = ["design", "quoting", "proposal", "pricing", "awaiting_deposit", "awaiting", "confirmed", "approved", "active_production", "production", "in_production", "installed", "completed", "invoiced", "permit_pending"]
    email_already_sent = status_lower in design_or_higher_statuses
    
    st.markdown(
        '''
        <div class="liquid-card" style="
            background: linear-gradient(145deg, #003049 0%, #001d2e 100%);
            border-radius: 20px;
            padding: 24px;
            margin: 16px 0;
            box-shadow: 0 4px 20px rgba(0, 168, 232, 0.25), 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1.5px solid #00A8E8;
        ">
            <h3 style="color: #00A8E8; margin: 0 0 8px 0; font-size: 18px;">🎨 Block B: The Design Loop (Matt)</h3>
            <p style="color: #FFFFFF; margin: 0; font-size: 14px;">Request design and upload proofs</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    repair_mode_key = f"no_design_required_{project_id}"
    current_repair_mode = st.checkbox(
        "🛠️ No Design Required (Repair/Service Job)",
        value=no_design_required,
        key=repair_mode_key,
        help="Check this if the project is a repair or service job that doesn't need a design proof"
    )
    
    if current_repair_mode != no_design_required:
        update_no_design_required(project_id, current_repair_mode)
        st.rerun()
    
    if current_repair_mode:
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 12px 16px;
                margin: 8px 0;
                border: 1px solid #4CAF50;
            ">
                <p style="color: #4CAF50; margin: 0; font-size: 13px;">✅ Design bypassed - Repair/Service mode active. Block C is unlocked.</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        return True
    
    if has_assigned_design:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px;
                margin: 12px 0;
                border: 1px solid #4CAF50;
            ">
                <p style="color: #4CAF50; margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">✅ Design Proof Assigned</p>
                <p style="color: #E5E5E5; margin: 0; font-size: 13px;">📄 {design_proof_name}</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        drive_view_url = f"https://drive.google.com/file/d/{design_proof_drive_id}/view"
        st.link_button("👁️ View Design Proof PDF", drive_view_url, use_container_width=True, type="primary")
    
    design_key = f"design_uploaded_{project_id}"
    if has_assigned_design:
        st.session_state[design_key] = True
    elif design_key not in st.session_state:
        st.session_state[design_key] = False
    
    design_file = None
    
    with st.container():
        # Show status message if email already sent, otherwise show email controls
        if email_already_sent:
            st.markdown(
                '''
                <div style="
                    background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                    border-radius: 12px;
                    padding: 16px;
                    margin: 12px 0;
                    border: 1px solid #4CAF50;
                ">
                    <p style="color: #4CAF50; margin: 0; font-size: 14px;">✅ Design request sent to Matt. Waiting for response.</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        else:
            matt_email = st.text_input(
                "Matt's Email",
                value="matt@kbsignconstruction.com",
                key=f"matt_email_{project_id}",
                help="Email address for design requests"
            )
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                notes_preview = notes[:100] + "..." if len(notes) > 100 else notes
                design_request_text = f"Matt, please design for {client_name}. Notes: {notes_preview if notes else 'No notes provided.'}"
                
                st.markdown(
                    f'''
                    <div style="
                        background: linear-gradient(145deg, #0d1b2a 0%, #1b263b 100%);
                        border-radius: 12px;
                        padding: 16px;
                        margin: 8px 0;
                        border: 1px solid #E5E5E5;
                    ">
                        <p style="color: #FFFFFF; margin: 0; font-size: 13px; font-family: monospace;">
                            {design_request_text}
                        </p>
                        <p style="color: #E5E5E5; margin: 8px 0 0 0; font-size: 11px;">
                            Drive Link: {google_drive_link if google_drive_link else "Not linked"}
                        </p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
            
            with col2:
                if st.button("Request Design", key=f"open_design_dialog_{project_id}", use_container_width=True, type="primary"):
                    st.session_state[f"show_design_dialog_{project_id}"] = True
                    photos = get_photos_by_categories(project_id)
                    site_count = len(photos.get("site", []))
                    markup_count = len(photos.get("markup", []))
                    logo_count = len(photos.get("logo", []))
                    ref_count = len(photos.get("reference", []))
                    photo_summary = f"Site Photos: {site_count}, Markups: {markup_count}, Logos: {logo_count}, Reference: {ref_count}"
                    if site_count + markup_count + logo_count + ref_count == 0:
                        photo_summary = "No photos uploaded yet."
                    st.session_state[f"design_email_body_{project_id}"] = draft_design_email(client_name, notes, google_drive_link, photo_summary)
                    st.rerun()
            
            if st.session_state.get(f"show_design_dialog_{project_id}", False):
                render_design_approval_dialog(project_id, matt_email, client_name)
        
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        
        # Client clarification button always visible
        if st.button("Draft Client Clarification", key=f"blue_unicorn_{project_id}", use_container_width=True, help="Send a clarification email to the client with action notes and site photos"):
            from services.database_manager import get_project_by_id as get_proj
            proj = get_proj(project_id)
            action_note = proj.get("action_note", "") if proj else ""
            st.session_state[f"show_client_clarification_{project_id}"] = True
            st.session_state[f"client_clarification_note_{project_id}"] = action_note
            st.rerun()
        
        if st.session_state.get(f"show_client_clarification_{project_id}", False):
            render_client_clarification_dialog(project_id, client_name)
        
        if not has_assigned_design:
            st.markdown(
                '<p style="color: #FFFFFF; font-size: 14px; margin: 20px 0 8px 0;">Upload Design Proof from Matt:</p>',
                unsafe_allow_html=True
            )
            
            design_file = st.file_uploader(
                "Upload Design Proof",
                type=["jpg", "jpeg", "png", "pdf"],
                key=f"design_proof_{project_id}",
                help="Upload Matt's design proof (JPG or PDF)",
                label_visibility="collapsed"
            )
            
            if design_file:
                st.session_state[design_key] = True
                st.success(f"✅ Design proof uploaded: {design_file.name}")
                
                if design_file.type.startswith("image"):
                    st.image(design_file, caption="Design Proof", use_container_width=True)
                else:
                    st.info(f"📄 PDF uploaded: {design_file.name}")
            else:
                st.markdown(
                    '<p style="color: #E5E5E5; font-size: 13px; font-style: italic;">No design proof uploaded yet.</p>',
                    unsafe_allow_html=True
                )
    
    return st.session_state[design_key] or (design_file is not None)


def render_email_voice_button(project_id: str, target_key: str, dialog_type: str):
    """Render voice dictation button with visual feedback and proper Streamlit integration.
    
    Uses streamlit_js_eval with async promise pattern for reliable speech recognition.
    - Visual feedback: 🎙️ changes to 🔴 with "Recording..." text
    - Appends text (doesn't overwrite)
    - Console logs for debugging
    """
    import streamlit.components.v1 as components
    from streamlit_js_eval import streamlit_js_eval
    import json
    
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
        
        st.toast(f"✅ Added: {result}", icon="🎤")
        st.rerun()
    
    # Process any pending error
    if error_key in st.session_state and st.session_state[error_key]:
        error = st.session_state[error_key]
        st.session_state[error_key] = None
        st.session_state[recording_key] = False
        st.error(f"🎤 Voice error: {error}")
    
    is_recording = st.session_state.get(recording_key, False)
    
    if is_recording:
        # Show recording indicator with red button
        if st.button("🔴", key=f"{voice_key}_stop", help="Click to cancel recording"):
            st.session_state[recording_key] = False
            st.rerun()
        
        # Inject visual indicator and start speech recognition via JS
        components.html(f"""
        <style>
            @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}
            .rec {{ color:#e74c3c; animation:pulse 1s infinite; padding:4px 8px; background:#2a0a0a; border-radius:6px; border:1px solid #e74c3c; font-size:12px; }}
        </style>
        <div class="rec">🔴 Recording...</div>
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
        """, height=30)
        
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


@st.dialog("Review Design Request - Kam's Approval")
def render_design_approval_dialog(project_id: str, to_email: str, client_name: str):
    """Approval gate dialog for design request email with visual attachment station."""
    from components.attachment_station import render_attachment_station, prepare_attachments, get_attachment_filenames
    from services.email_service import send_email_with_attachments, is_test_mode
    from services.database_manager import get_project_by_id
    
    st.markdown(
        '<p style="color: #FFFFFF; font-size: 14px; margin-bottom: 16px;">Review and edit the email before sending:</p>',
        unsafe_allow_html=True
    )
    
    recipient = st.text_input("To:", value=to_email, key=f"dialog_design_to_{project_id}")
    subject = st.text_input("Subject:", value=f"Design Request: {client_name}", key=f"dialog_design_subject_{project_id}")
    
    col_label, col_mic = st.columns([9, 1])
    with col_label:
        st.markdown('<p style="color: #E5E5E5; font-size: 13px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_email_voice_button(project_id, f"dialog_design_body_{project_id}", "design")
    
    body = st.text_area(
        "",
        value=st.session_state.get(f"design_email_body_{project_id}", ""),
        height=180,
        key=f"dialog_design_body_{project_id}",
        label_visibility="collapsed"
    )
    
    attachment_result = render_attachment_station(project_id, "design")
    selected_files = attachment_result["selected_files"]
    use_drive_links = attachment_result["use_drive_links"]
    
    col1, col2 = st.columns(2)
    
    if use_drive_links:
        project_for_link = get_project_by_id(project_id)
        drive_link = project_for_link.get("google_drive_link", "") if project_for_link else ""
        if not drive_link:
            st.warning("Selected files exceed 10MB. Link a Google Drive folder first, or deselect some files.")
    
    with col1:
        send_disabled = use_drive_links and not (get_project_by_id(project_id) or {}).get("google_drive_link", "")
        if st.button("Send Final Email", type="primary", use_container_width=True, key=f"confirm_design_{project_id}", disabled=send_disabled):
            from services.database_manager import add_project_touch, update_project_status, add_project_history, get_project_by_id as get_proj
            
            attached_filenames = get_attachment_filenames(selected_files)
            
            if use_drive_links:
                project = get_proj(project_id)
                drive_link = project.get("google_drive_link", "") if project else ""
                body_with_link = f"{body}\n\n---\nProject Files (Drive Link): {drive_link}"
                success, message = send_email(recipient, subject, body_with_link)
                attachment_note = f" (Files via Drive link - {len(selected_files)} files exceeded 10MB limit)"
            elif selected_files:
                attachments = prepare_attachments(selected_files)
                success, message = send_email_with_attachments(recipient, subject, body, attachments)
                attachment_note = f" with {len(attached_filenames)} attachments: {', '.join(attached_filenames[:3])}"
                if len(attached_filenames) > 3:
                    attachment_note += f"... (+{len(attached_filenames) - 3} more)"
            else:
                success, message = send_email(recipient, subject, body)
                attachment_note = ""
            
            if success:
                add_project_touch(project_id, "email_sent", f"Design request sent to Matt ({recipient}){attachment_note}")
                
                project = get_proj(project_id)
                current_status = (project.get("status", "") if project else "").lower()
                if current_status in ["migrated", "lead", "new", "pending"]:
                    update_project_status(project_id, "Design")
                    add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Email sent to Matt - Project moved to Design")
                else:
                    add_project_history(project_id, "EMAIL_SENT", f"[SYSTEM] Design request email sent to Matt{attachment_note}")
                
                if attached_filenames:
                    add_project_history(project_id, "EMAIL_ATTACHMENT", f"[ATTACHMENTS] Sent to Matt: {', '.join(attached_filenames)}")
                
                if is_test_mode():
                    st.success(f"Email sent to Matt! (Test mode: redirected from {recipient})")
                else:
                    st.success("Email sent to Matt!")
                st.session_state[f"show_design_dialog_{project_id}"] = False
                st.rerun()
            else:
                st.error(f"Failed: {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_design_{project_id}"):
            st.session_state[f"show_design_dialog_{project_id}"] = False
            st.rerun()


@st.dialog("Client Clarification - Blue Unicorn")
def render_client_clarification_dialog(project_id: str, client_name: str):
    """Blue Unicorn dialog - send clarification email to client with action notes and site photos."""
    from services.database_manager import get_photos_by_categories, get_project_by_id as get_proj
    from services.email_service import send_email_with_attachments, is_test_mode
    
    project = get_proj(project_id)
    action_note = st.session_state.get(f"client_clarification_note_{project_id}", "")
    
    st.markdown(
        '''
        <div style="
            background: linear-gradient(145deg, #1a2a4a 0%, #0d1b2a 100%);
            border-radius: 12px;
            padding: 12px;
            margin-bottom: 16px;
            border: 1px solid #00A8E8;
        ">
            <p style="color: #00A8E8; margin: 0; font-size: 13px;">
                🦄 Blue Unicorn: This email includes your action notes and site photos.
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    client_email = st.text_input("Client Email:", value="", key=f"clarify_to_{project_id}", placeholder="client@example.com")
    subject = st.text_input("Subject:", value=f"Clarification Needed - {client_name} Sign Project", key=f"clarify_subject_{project_id}")
    
    default_body = f"""Hi,

We're working on your sign project and need some clarification before we can proceed.

{action_note if action_note else "Please review the attached site photos and let us know your thoughts."}

Best regards,
KB Signs Team"""
    
    # Email body with microphone support
    col_label, col_mic = st.columns([9, 1])
    with col_label:
        st.markdown('<p style="color: #E5E5E5; font-size: 13px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_email_voice_button(project_id, f"clarify_body_{project_id}", "clarify")
    
    body = st.text_area("", value=default_body, height=150, key=f"clarify_body_{project_id}", label_visibility="collapsed")
    
    photos = get_photos_by_categories(project_id)
    site_photos = photos.get("site", [])
    
    selected_paths = []
    if site_photos:
        st.markdown('<p style="color: #E5E5E5; font-size: 14px; margin: 12px 0 8px 0;">📸 Attach Site Photos:</p>', unsafe_allow_html=True)
        for i, photo in enumerate(site_photos[:5]):
            photo_path = photo.get("file_path", "")
            photo_name = photo.get("file_name", f"photo_{i+1}.jpg")
            if photo_path and os.path.exists(photo_path):
                if st.checkbox(f"📷 {photo_name}", value=True, key=f"attach_site_{project_id}_{i}"):
                    selected_paths.append({"path": photo_path, "name": photo_name})
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Final Email", type="primary", use_container_width=True, key=f"send_clarify_{project_id}"):
            if not client_email:
                st.error("Please enter a client email address")
            else:
                from services.database_manager import add_project_touch, add_project_history
                from io import BytesIO
                import mimetypes
                
                attachments = []
                attached_filenames = []
                for item in selected_paths:
                    try:
                        with open(item["path"], "rb") as f:
                            file_data = f.read()
                        file_buffer = BytesIO(file_data)
                        mime_type, _ = mimetypes.guess_type(item["name"])
                        attachments.append({
                            "buffer": file_buffer,
                            "filename": item["name"],
                            "mime_type": mime_type or "application/octet-stream"
                        })
                        attached_filenames.append(item["name"])
                    except Exception as e:
                        print(f"Warning: Could not read file {item['path']}: {e}")
                
                if attachments:
                    success, message = send_email_with_attachments(client_email, subject, body, attachments)
                else:
                    from services.email_service import send_email
                    success, message = send_email(client_email, subject, body)
                
                if success:
                    add_project_touch(project_id, "email_sent", f"Client clarification sent to {client_email}")
                    for fname in attached_filenames:
                        add_project_history(project_id, "EMAIL_ATTACHMENT", f"[SYSTEM] File permissions updated and attachment attempted for {fname}")
                    add_project_history(project_id, "EMAIL_SENT", f"[CLARIFICATION] Sent to client: {action_note[:50]}...")
                    if is_test_mode():
                        st.success(f"✅ Clarification email sent! (Test mode: redirected from {client_email})")
                    else:
                        st.success("✅ Clarification email sent to client!")
                    st.session_state[f"show_client_clarification_{project_id}"] = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_clarify_{project_id}"):
            st.session_state[f"show_client_clarification_{project_id}"] = False
            st.rerun()


def render_block_c_pricing_loop(project_id: str, client_name: str, design_uploaded: bool, google_drive_link: str, proposal_drive_id: str = "", proposal_name: str = ""):
    """Block C: The Pricing Loop - Bruno's workflow. Locked until design is uploaded."""
    
    has_assigned_proposal = bool(proposal_drive_id)
    
    if design_uploaded:
        border_color = "#00A8E8"
        opacity = "1"
        header_color = "#00A8E8"
        locked_badge = ""
    else:
        border_color = "#666"
        opacity = "0.5"
        header_color = "#666"
        locked_badge = '<span style="background: #dc3545; color: white; padding: 4px 8px; border-radius: 8px; font-size: 11px; margin-left: 10px; border: 2px solid white;">🔒 LOCKED</span>'
    
    st.markdown(
        f'''
        <div class="liquid-card" style="
            background: linear-gradient(145deg, #003049 0%, #001d2e 100%);
            border-radius: 20px;
            padding: 24px;
            margin: 16px 0;
            box-shadow: 0 4px 20px rgba(0, 168, 232, 0.25), 0 8px 32px rgba(0, 0, 0, 0.3);
            border: 1.5px solid {border_color};
            opacity: {opacity};
        ">
            <h3 style="color: {header_color}; margin: 0 0 8px 0; font-size: 18px;">
                💰 Block C: The Pricing Loop (Bruno) {locked_badge}
            </h3>
            <p style="color: #FFFFFF; margin: 0; font-size: 14px;">Request pricing and upload final proposal</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    if has_assigned_proposal:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px;
                margin: 12px 0;
                border: 1px solid #4CAF50;
            ">
                <p style="color: #4CAF50; margin: 0 0 8px 0; font-size: 14px; font-weight: bold;">✅ Proposal Assigned</p>
                <p style="color: #E5E5E5; margin: 0; font-size: 13px;">📄 {proposal_name}</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        proposal_view_url = f"https://drive.google.com/file/d/{proposal_drive_id}/view"
        st.link_button("👁️ View Proposal PDF", proposal_view_url, use_container_width=True, type="primary")
    
    if not design_uploaded:
        st.markdown(
            '<p style="color: #E5E5E5; font-size: 13px; font-style: italic;">⚠️ Upload a design proof in Block B to unlock pricing.</p>',
            unsafe_allow_html=True
        )
        return
    
    with st.container():
        bruno_email = st.text_input(
            "Bruno's Email",
            value="bruno@kbsignconstruction.com",
            key=f"bruno_email_{project_id}",
            help="Email address for pricing requests"
        )
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            pricing_request_text = f"Bruno, please price the attached design for {client_name}."
            
            st.markdown(
                f'''
                <div style="
                    background: linear-gradient(145deg, #0d1b2a 0%, #1b263b 100%);
                    border-radius: 12px;
                    padding: 16px;
                    margin: 8px 0;
                    border: 1px solid #E5E5E5;
                ">
                    <p style="color: #FFFFFF; margin: 0; font-size: 13px; font-family: monospace;">
                        {pricing_request_text}
                    </p>
                    <p style="color: #E5E5E5; margin: 8px 0 0 0; font-size: 11px;">
                        Drive Link: {google_drive_link if google_drive_link else "Not linked"}
                    </p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        with col2:
            if st.button("📧 Request Pricing", key=f"open_pricing_dialog_{project_id}", use_container_width=True, type="primary"):
                st.session_state[f"show_pricing_dialog_{project_id}"] = True
                st.session_state[f"pricing_email_body_{project_id}"] = draft_pricing_email(client_name, google_drive_link)
                st.rerun()
        
        if st.session_state.get(f"show_pricing_dialog_{project_id}", False):
            render_pricing_approval_dialog(project_id, bruno_email, client_name)
        
        proposal_uploaded = has_assigned_proposal
        proposal_file = None
        
        if not has_assigned_proposal:
            st.markdown(
                '<p style="color: #FFFFFF; font-size: 14px; margin: 20px 0 8px 0;">Upload Final Proposal from Bruno:</p>',
                unsafe_allow_html=True
            )
            
            proposal_file = st.file_uploader(
                "Upload Final Proposal",
                type=["pdf", "jpg", "jpeg", "png"],
                key=f"proposal_{project_id}",
                help="Upload Bruno's final proposal (PDF preferred)",
                label_visibility="collapsed"
            )
            
            if proposal_file:
                proposal_uploaded = True
                st.success(f"✅ Proposal uploaded: {proposal_file.name}")
                
                if proposal_file.type.startswith("image"):
                    st.image(proposal_file, caption="Final Proposal", use_container_width=True)
                else:
                    st.info(f"📄 PDF uploaded: {proposal_file.name}")
            else:
                st.markdown(
                    '<p style="color: #E5E5E5; font-size: 13px; font-style: italic;">No proposal uploaded yet.</p>',
                    unsafe_allow_html=True
                )
        
        if proposal_uploaded:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '''
                <div style="
                    background: linear-gradient(145deg, #0d1b2a 0%, #1b263b 100%);
                    border-radius: 12px;
                    padding: 16px;
                    margin: 8px 0;
                    border: 1.5px solid #00A8E8;
                    box-shadow: 0 2px 12px rgba(0, 168, 232, 0.2);
                ">
                    <h4 style="color: #00A8E8; margin: 0 0 12px 0; font-size: 16px;">📨 Send Proposal to Customer</h4>
                </div>
                ''',
                unsafe_allow_html=True
            )
            
            customer_email = st.text_input(
                "Customer Email",
                value="",
                key=f"customer_email_{project_id}",
                placeholder="customer@email.com",
                help="Enter customer's email address"
            )
            
            if st.button("📧 Send Proposal", key=f"open_proposal_dialog_{project_id}", use_container_width=True, type="primary"):
                if customer_email:
                    st.session_state[f"show_proposal_dialog_{project_id}"] = True
                    st.session_state[f"proposal_email_body_{project_id}"] = draft_proposal_email(client_name, google_drive_link)
                    st.session_state[f"proposal_customer_email_{project_id}"] = customer_email
                    st.rerun()
                else:
                    st.warning("Please enter a customer email address.")
            
            if st.session_state.get(f"show_proposal_dialog_{project_id}", False):
                render_proposal_approval_dialog(
                    project_id, 
                    st.session_state.get(f"proposal_customer_email_{project_id}", ""),
                    client_name,
                    proposal_drive_id
                )
    
    legacy_sent_key = f"legacy_proposal_sent_{project_id}"
    project_data = get_project_by_id(project_id)
    current_status = project_data.get("status", "") if project_data else ""
    already_sent = "PROPOSAL SENT" in current_status.upper() or "AWAITING CUSTOMER" in current_status.upper()
    
    if not st.session_state.get(legacy_sent_key, False) and not already_sent:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            '''
            <div style="
                border-top: 1px solid #333;
                padding-top: 16px;
                margin-top: 8px;
            ">
                <p style="color: #888; font-size: 12px; margin: 0 0 8px 0;">Legacy Migration Tool</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        if st.button(
            "📤 Proposal Already Sent (Legacy)",
            key=f"legacy_sent_btn_{project_id}",
            use_container_width=True,
            type="secondary"
        ):
            timestamp = get_timestamp_mountain()
            note = f"[{timestamp}] Project moved to Sent status via legacy migration."
            
            success = update_project_status_with_note(
                project_id,
                "PROPOSAL SENT - AWAITING CUSTOMER",
                note
            )
            
            if success:
                st.session_state[legacy_sent_key] = True
                st.success("Project moved to 'Awaiting Customer' status!")
                st.rerun()
            else:
                st.error("Failed to update project status.")


@st.dialog("Review Pricing Request - Kam's Approval")
def render_pricing_approval_dialog(project_id: str, to_email: str, client_name: str):
    """Approval gate dialog for pricing request email."""
    from services.database_manager import add_project_touch, get_project_proposals
    from services.email_service import is_test_mode, send_email_with_attachments
    import glob
    
    st.markdown(
        '<p style="color: #FFFFFF; font-size: 14px; margin-bottom: 16px;">Review and edit the email before sending:</p>',
        unsafe_allow_html=True
    )
    
    recipient = st.text_input("To:", value=to_email, key=f"dialog_pricing_to_{project_id}")
    subject = st.text_input("Subject:", value=f"Pricing Request: {client_name}", key=f"dialog_pricing_subject_{project_id}")
    
    # Email body with microphone support
    col_label, col_mic = st.columns([9, 1])
    with col_label:
        st.markdown('<p style="color: #E5E5E5; font-size: 13px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_email_voice_button(project_id, f"dialog_pricing_body_{project_id}", "pricing")
    
    body = st.text_area(
        "",
        value=st.session_state.get(f"pricing_email_body_{project_id}", ""),
        height=150,
        key=f"dialog_pricing_body_{project_id}",
        label_visibility="collapsed"
    )
    
    proposals = get_project_proposals(project_id)
    project_files = glob.glob(f"./project_files/{project_id}_*")
    
    selected_file_paths = []
    if proposals or project_files:
        st.markdown("**📎 Attach Files:**")
        
        for prop in proposals:
            file_path = prop.get("file_path", "")
            file_name = prop.get("file_name", os.path.basename(file_path))
            if os.path.exists(file_path):
                if st.checkbox(f"📄 {file_name}", key=f"attach_prop_{prop.get('id')}_{project_id}"):
                    selected_file_paths.append({"path": file_path, "name": file_name})
        
        for pf in project_files:
            if pf not in [p.get("file_path") for p in proposals]:
                fname = os.path.basename(pf)
                if st.checkbox(f"📄 {fname}", key=f"attach_file_{fname}_{project_id}"):
                    selected_file_paths.append({"path": pf, "name": fname})
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Final Email", type="primary", use_container_width=True, key=f"confirm_pricing_{project_id}"):
            from services.database_manager import update_project_status, add_project_history, get_project_by_id as get_proj
            from io import BytesIO
            import mimetypes
            
            attachments = []
            attached_filenames = []
            for item in selected_file_paths:
                try:
                    with open(item["path"], "rb") as f:
                        file_data = f.read()
                    file_buffer = BytesIO(file_data)
                    mime_type, _ = mimetypes.guess_type(item["name"])
                    attachments.append({
                        "buffer": file_buffer,
                        "filename": item["name"],
                        "mime_type": mime_type or "application/octet-stream"
                    })
                    attached_filenames.append(item["name"])
                except Exception as e:
                    print(f"Warning: Could not read file {item['path']}: {e}")
            
            if attachments:
                success, message = send_email_with_attachments(recipient, subject, body, attachments)
            else:
                success, message = send_email(recipient, subject, body)
            
            if success:
                attach_note = f" with {len(attached_filenames)} file(s)" if attached_filenames else ""
                add_project_touch(project_id, "email_sent", f"Pricing request sent to Bruno ({recipient}){attach_note}")
                
                for fname in attached_filenames:
                    add_project_history(project_id, "EMAIL_ATTACHMENT", f"[SYSTEM] File permissions updated and attachment attempted for {fname}")
                
                project = get_proj(project_id)
                current_status = (project.get("status", "") if project else "").lower()
                if current_status in ["migrated", "lead", "new", "pending", "design"]:
                    update_project_status(project_id, "Quoting")
                    add_project_history(project_id, "STATUS_CHANGE", "[SYSTEM] Email sent to Bruno - Project moved to Quoting")
                else:
                    add_project_history(project_id, "EMAIL_SENT", "[SYSTEM] Pricing request email sent to Bruno")
                
                if is_test_mode():
                    st.success(f"✅ Email sent to Bruno! (Test mode: redirected from {recipient})")
                else:
                    st.success("✅ Email sent to Bruno!")
                st.session_state[f"show_pricing_dialog_{project_id}"] = False
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_pricing_{project_id}"):
            st.session_state[f"show_pricing_dialog_{project_id}"] = False
            st.rerun()


@st.dialog("Review Customer Proposal - Kam's Approval")
def render_proposal_approval_dialog(project_id: str, to_email: str, client_name: str, proposal_drive_id: str = ""):
    """Approval gate dialog for customer proposal email with PDF attachment."""
    from services.email_service import is_test_mode, set_drive_file_public, download_drive_file, send_email_with_attachments
    from services.database_manager import add_project_touch, add_project_history
    
    st.markdown(
        '<p style="color: #FFFFFF; font-size: 14px; margin-bottom: 16px;">Review and edit the proposal email before sending to the customer:</p>',
        unsafe_allow_html=True
    )
    
    if proposal_drive_id:
        st.markdown(
            '''<div style="background: #28a74533; border: 1px solid #28a745; border-radius: 8px; padding: 10px; margin-bottom: 12px;">
                <p style="color: #28a745; margin: 0; font-size: 13px;">📎 Primary Proposal PDF will be attached</p>
            </div>''',
            unsafe_allow_html=True
        )
    
    recipient = st.text_input("To:", value=to_email, key=f"dialog_proposal_to_{project_id}")
    subject = st.text_input("Subject:", value=f"Your Sign Proposal from KB Signs - {client_name}", key=f"dialog_proposal_subject_{project_id}")
    
    # Email body with microphone support
    col_label, col_mic = st.columns([9, 1])
    with col_label:
        st.markdown('<p style="color: #E5E5E5; font-size: 13px; margin-bottom: 4px;">Email Body:</p>', unsafe_allow_html=True)
    with col_mic:
        render_email_voice_button(project_id, f"dialog_proposal_body_{project_id}", "proposal")
    
    body = st.text_area(
        "",
        value=st.session_state.get(f"proposal_email_body_{project_id}", ""),
        height=200,
        key=f"dialog_proposal_body_{project_id}",
        label_visibility="collapsed"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Final Email", type="primary", use_container_width=True, key=f"confirm_proposal_{project_id}"):
            attachments = []
            attached_filenames = []
            
            if proposal_drive_id:
                # Step 1: Set 'Anyone with link can view' permission (Skeleton Key)
                perm_success, perm_msg = set_drive_file_public(proposal_drive_id)
                print(f"[PROPOSAL] Permission update: {perm_success} - {perm_msg}")
                
                # Step 2: Download raw bytes using get_media equivalent
                raw_bytes, filename, mime_type, err = download_drive_file(proposal_drive_id)
                if raw_bytes and not err:
                    # Step 3: Pass raw bytes for Base64 encoding
                    attachments.append({
                        "data": raw_bytes,
                        "filename": filename
                    })
                    attached_filenames.append(filename)
                    print(f"[PROPOSAL] File ready for attachment: {filename} ({len(raw_bytes)} bytes)")
                else:
                    print(f"[PROPOSAL ERROR] Download failed: {err}")
            
            if attachments:
                success, message = send_email_with_attachments(recipient, subject, body, attachments)
            else:
                success, message = send_email(recipient, subject, body)
            
            if success:
                add_project_touch(project_id, "email_sent", f"Proposal sent to customer ({recipient})")
                
                for fname in attached_filenames:
                    add_project_history(project_id, "EMAIL_ATTACHMENT", f"[SYSTEM] File permissions updated and attachment attempted for {fname}")
                
                add_project_history(project_id, "EMAIL_SENT", f"[SYSTEM] Proposal email sent to customer ({recipient})")
                
                if is_test_mode():
                    attach_note = f" with {len(attached_filenames)} attachment(s)" if attached_filenames else ""
                    st.success(f"✅ Proposal sent{attach_note}! (Test mode: redirected from {recipient})")
                else:
                    st.success(f"✅ Proposal sent to {recipient}!")
                st.session_state[f"show_proposal_dialog_{project_id}"] = False
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_proposal_{project_id}"):
            st.session_state[f"show_proposal_dialog_{project_id}"] = False
            st.rerun()


def render_block_d_deposit_handoff(project_id: str, client_name: str, status: str,
                                    deposit_invoice_requested: bool, deposit_invoice_sent: bool,
                                    deposit_received_date, deposit_amount: float,
                                    google_drive_link: str = None, estimated_value: float = 0.0,
                                    master_spec_file_id: str = None, master_spec_file_name: str = None,
                                    signed_spec_file_id: str = None, signed_spec_file_name: str = None,
                                    production_locked: bool = False):
    """Block D: Deposit & Handoff - New workflow for production kickoff with Production Lockdown."""
    from services.database_manager import update_deposit_stage, mark_deposit_received, add_project_note, add_project_touch, get_project_touches, update_project_estimated_value, save_commission_amounts, get_primary_contact_email, get_commission_notes, get_project_proposals, save_project_proposal, set_proposal_as_primary, update_proposal_scan_results, delete_proposal, set_master_spec, set_signed_spec, lock_production, get_photos_by_categories
    from services.email_service import send_deposit_invoice_request, send_deposit_invoice_to_customer, is_test_mode
    from services.gemini_service import scan_invoice_for_amounts
    
    BRUNO_EMAIL = "bruno@kbsignconstruction.com"
    customer_email = get_primary_contact_email(project_id) or "customer@example.com"
    
    current_stage = "waiting_invoice"
    stage_label = "⏳ Waiting: Bruno to create deposit invoice"
    stage_color = "#FFB800"
    
    if deposit_received_date:
        current_stage = "complete"
        stage_label = "✅ Deposit Received - ACTIVE PRODUCTION"
        stage_color = "#28a745"
    elif deposit_invoice_sent:
        current_stage = "waiting_payment"
        stage_label = "⏳ Waiting: Customer payment"
        stage_color = "#00A8E8"
    elif deposit_invoice_requested:
        current_stage = "waiting_invoice_creation"
        stage_label = "⏳ Waiting: Bruno creating invoice"
        stage_color = "#FF6B35"
    
    st.markdown(
        f'''
        <p style="color: #E5E5E5; margin: 0 0 12px 0; font-size: 14px;">Get deposit and kick off production</p>
        ''',
        unsafe_allow_html=True
    )
    
    st.markdown(
        f'''
        <div style="
            background: linear-gradient(145deg, {stage_color}22 0%, {stage_color}11 100%);
            border-radius: 12px;
            padding: 14px 20px;
            margin: 8px 0 16px 0;
            border: 2px solid {stage_color};
        ">
            <p style="color: {stage_color}; margin: 0; font-size: 15px; font-weight: 600;">
                {stage_label}
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    if current_stage == "complete":
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px 20px;
                margin: 8px 0;
                border: 1px solid #28a745;
            ">
                <p style="color: #28a745; margin: 0; font-size: 14px;">
                    ✅ <strong>Deposit received on {deposit_received_date}</strong><br>
                    💰 Amount: ${deposit_amount:,.2f}
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        return
    
    proposals = get_project_proposals(project_id)
    
    if proposals:
        st.markdown("**📁 Uploaded Proposals/Invoices:**")
        for prop in proposals:
            prop_id = str(prop.get("id"))
            prop_name = prop.get("file_name", "Unknown")
            prop_path = prop.get("file_path", "")
            is_primary = prop.get("is_primary", False)
            scanned_total = prop.get("scanned_total")
            scanned_deposit = prop.get("scanned_deposit")
            
            primary_badge = "⭐ PRIMARY" if is_primary else ""
            value_info = ""
            if scanned_total:
                value_info = f" | ${float(scanned_total):,.2f}"
            
            prop_col1, prop_col2, prop_col3, prop_col4 = st.columns([3, 1, 1, 1])
            
            with prop_col1:
                badge_style = "background: #28a745; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;" if is_primary else ""
                if is_primary:
                    st.markdown(f"📄 **{prop_name}** <span style='{badge_style}'>{primary_badge}</span>{value_info}", unsafe_allow_html=True)
                else:
                    st.caption(f"📄 {prop_name}{value_info}")
            
            with prop_col2:
                if not is_primary:
                    if st.button("⭐ Set Primary", key=f"set_primary_{prop_id}"):
                        success, err = set_proposal_as_primary(prop_id, project_id)
                        if success:
                            st.success("✅ Set as primary!")
                            st.rerun()
                        else:
                            st.error(f"Error: {err}")
            
            with prop_col3:
                if os.path.exists(prop_path):
                    if st.button("🤖 Scan", key=f"scan_prop_{prop_id}"):
                        with st.spinner(f"Scanning {prop_name}..."):
                            with open(prop_path, "rb") as f:
                                file_bytes = f.read()
                            
                            is_pdf = prop_path.lower().endswith(".pdf")
                            if is_pdf:
                                result = scan_invoice_for_amounts(pdf_bytes=file_bytes)
                            else:
                                result = scan_invoice_for_amounts(image_bytes=file_bytes)
                            
                            if result.get("error"):
                                st.error(f"Scan error: {result['error']}")
                            else:
                                update_proposal_scan_results(
                                    prop_id,
                                    result.get("total_value", 0),
                                    result.get("deposit_amount", 0),
                                    result.get("notes")
                                )
                                if is_primary:
                                    st.session_state[f"scanned_total_{project_id}"] = result["total_value"]
                                    st.session_state[f"scanned_deposit_{project_id}"] = result["deposit_amount"]
                                    st.session_state[f"has_scanned_{project_id}"] = True
                                st.success("✅ Scanned!")
                                st.rerun()
            
            with prop_col4:
                if st.button("🗑️", key=f"delete_prop_{prop_id}", help="Delete this proposal"):
                    if delete_proposal(prop_id):
                        if os.path.exists(prop_path):
                            try:
                                os.remove(prop_path)
                            except:
                                pass
                        st.rerun()
        
        st.markdown("---")
    
    is_first_proposal = len(proposals) == 0
    set_as_primary = st.checkbox("Set as Primary Proposal", value=is_first_proposal, key=f"set_primary_new_{project_id}")
    
    uploaded_invoice = st.file_uploader(
        "📄 Upload New Proposal/Invoice (PDF/Image)",
        type=["pdf", "jpg", "jpeg", "png"],
        key=f"invoice_upload_{project_id}"
    )
    
    scan_error_key = f"scan_error_{project_id}"
    
    if uploaded_invoice:
        scan_col1, scan_col2 = st.columns([2, 1])
        
        with scan_col1:
            if st.button("🤖 Save & Scan", key=f"scan_invoice_{project_id}", type="primary"):
                file_bytes = uploaded_invoice.read()
                uploaded_invoice.seek(0)
                
                os.makedirs("./project_files", exist_ok=True)
                safe_name = uploaded_invoice.name.replace(" ", "_").replace("/", "_")
                save_path = f"./project_files/{project_id}_{safe_name}"
                
                file_saved = False
                try:
                    with open(save_path, "wb") as f:
                        f.write(file_bytes)
                    print(f"[SUCCESS] File saved to {save_path}")
                    file_saved = True
                except Exception as save_err:
                    st.error(f"Failed to save file: {save_err}")
                    print(f"[ERROR] File save failed: {save_err}")
                
                if file_saved:
                    with st.spinner("Scanning for amounts..."):
                        if uploaded_invoice.type == "application/pdf":
                            result = scan_invoice_for_amounts(pdf_bytes=file_bytes)
                        else:
                            result = scan_invoice_for_amounts(image_bytes=file_bytes)
                        
                        scanned_total = result.get("total_value") if not result.get("error") else None
                        scanned_deposit = result.get("deposit_amount") if not result.get("error") else None
                        scan_notes = result.get("notes")
                        
                        prop_id, err = save_project_proposal(
                            project_id=project_id,
                            file_name=uploaded_invoice.name,
                            file_path=save_path,
                            scanned_total=scanned_total,
                            scanned_deposit=scanned_deposit,
                            scan_notes=scan_notes,
                            is_primary=set_as_primary
                        )
                        
                        if err:
                            st.error(f"Database error: {err}")
                        else:
                            if set_as_primary and scanned_total:
                                st.session_state[f"scanned_total_{project_id}"] = scanned_total
                                st.session_state[f"scanned_deposit_{project_id}"] = scanned_deposit
                                st.session_state[f"has_scanned_{project_id}"] = True
                            
                            if result.get("error"):
                                st.warning(f"Scan issue: {result['error']} - File saved, manual entry available.")
                            else:
                                st.success("✅ Proposal saved and scanned!")
                            st.rerun()
        
        with scan_col2:
            if st.button("💾 Save Only", key=f"skip_scan_{project_id}"):
                file_bytes = uploaded_invoice.read()
                uploaded_invoice.seek(0)
                
                os.makedirs("./project_files", exist_ok=True)
                safe_name = uploaded_invoice.name.replace(" ", "_").replace("/", "_")
                save_path = f"./project_files/{project_id}_{safe_name}"
                
                try:
                    with open(save_path, "wb") as f:
                        f.write(file_bytes)
                    
                    prop_id, err = save_project_proposal(
                        project_id=project_id,
                        file_name=uploaded_invoice.name,
                        file_path=save_path,
                        is_primary=set_as_primary
                    )
                    
                    if err:
                        st.error(f"Database error: {err}")
                    else:
                        st.success("✅ Proposal saved!")
                        if set_as_primary:
                            st.session_state[f"manual_entry_{project_id}"] = True
                        st.rerun()
                except Exception as save_err:
                    st.warning(f"File save error: {save_err}")
    
    if st.session_state.get(scan_error_key):
        st.warning(f"⚠️ Last scan error: {st.session_state[scan_error_key]}")
        if st.button("✏️ Continue with Manual Entry", key=f"manual_after_error_{project_id}", type="primary"):
            st.session_state[f"manual_entry_{project_id}"] = True
            st.session_state.pop(scan_error_key, None)
            st.rerun()
    
    has_scanned = st.session_state.get(f"has_scanned_{project_id}", False)
    scanned_total = st.session_state.get(f"scanned_total_{project_id}")
    scanned_deposit = st.session_state.get(f"scanned_deposit_{project_id}")
    scan_notes = st.session_state.get(f"scan_notes_{project_id}")
    manual_entry_key = f"manual_entry_{project_id}"
    manual_entry = st.session_state.get(manual_entry_key, False)
    
    if scan_notes:
        st.info(f"AI Notes: {scan_notes}")
    
    st.markdown("### 💰 Project & Deposit Amounts")
    
    show_fields = has_scanned or manual_entry
    
    if has_scanned and (scanned_total is not None or scanned_deposit is not None):
        st.markdown("""
        <div style="background: rgba(76, 175, 80, 0.1); border-radius: 8px; padding: 10px; margin-bottom: 10px; border-left: 3px solid #4CAF50;">
            <span style="color: #4CAF50; font-weight: 600;">✨ AI-Extracted Values</span>
            <span style="color: #888; font-size: 12px; margin-left: 8px;">(Editable - adjust if needed)</span>
        </div>
        """, unsafe_allow_html=True)
        
        amt_col1, amt_col2 = st.columns(2)
        with amt_col1:
            default_total = float(scanned_total) if scanned_total is not None else 0.0
            edited_total = st.number_input(
                "Total Project Value ($)", 
                min_value=0.0, 
                value=default_total, 
                step=100.0, 
                key=f"edit_total_{project_id}",
                format="%.2f"
            )
        with amt_col2:
            default_deposit = float(scanned_deposit) if scanned_deposit is not None else 0.0
            edited_deposit = st.number_input(
                "Deposit Amount ($)", 
                min_value=0.0, 
                value=default_deposit, 
                step=100.0, 
                key=f"edit_deposit_{project_id}",
                format="%.2f"
            )
    elif manual_entry:
        st.markdown("""
        <div style="background: rgba(255, 184, 0, 0.1); border-radius: 8px; padding: 10px; margin-bottom: 10px; border-left: 3px solid #FFB800;">
            <span style="color: #FFB800; font-weight: 600;">✏️ Manual Entry Mode</span>
            <span style="color: #888; font-size: 12px; margin-left: 8px;">(Enter amounts below)</span>
        </div>
        """, unsafe_allow_html=True)
        
        amt_col1, amt_col2 = st.columns(2)
        with amt_col1:
            total_str = st.text_input(
                "Total Project Value ($)", 
                value="",
                key=f"edit_total_text_{project_id}",
                placeholder="e.g., 22374.24"
            )
            try:
                edited_total = float(total_str.replace(",", "").replace("$", "")) if total_str.strip() else None
            except ValueError:
                edited_total = None
                if total_str.strip():
                    st.error("Invalid number format")
        with amt_col2:
            deposit_str = st.text_input(
                "Deposit Amount ($)", 
                value="",
                key=f"edit_deposit_text_{project_id}",
                placeholder="e.g., 11187.12"
            )
            try:
                edited_deposit = float(deposit_str.replace(",", "").replace("$", "")) if deposit_str.strip() else None
            except ValueError:
                edited_deposit = None
                if deposit_str.strip():
                    st.error("Invalid number format")
    else:
        st.markdown("""
        <div style="background: rgba(0, 168, 232, 0.1); border-radius: 8px; padding: 16px; margin-bottom: 10px; border-left: 3px solid #00A8E8;">
            <p style="color: #E5E5E5; margin: 0 0 8px 0;">
                <strong style="color: #00A8E8;">📄 No amounts entered yet</strong>
            </p>
            <p style="color: #888; font-size: 13px; margin: 0;">
                Upload an invoice above for AI extraction, or click below to enter amounts manually.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✏️ Enter Amounts Manually", key=f"enable_manual_{project_id}"):
            st.session_state[manual_entry_key] = True
            st.rerun()
        
        edited_total = None
        edited_deposit = None
    
    if show_fields:
        existing_notes = get_commission_notes(project_id)
        commission_notes = st.text_area(
            "Accounting & Commission Notes", 
            value=existing_notes,
            placeholder="Manual overrides, legacy details, special commission arrangements...",
            key=f"commission_notes_{project_id}",
            height=100
        )
        
        has_valid_amounts = (edited_total is not None and edited_total > 0) or (edited_deposit is not None and edited_deposit > 0)
        
        if st.button("✅ Confirm Amounts & Update Commission", key=f"confirm_amounts_{project_id}", type="primary", disabled=not has_valid_amounts):
            final_total = edited_total if edited_total is not None else 0.0
            final_deposit = edited_deposit if edited_deposit is not None else 0.0
            
            update_project_estimated_value(project_id, final_total)
            commission_saved = save_commission_amounts(project_id, final_total, final_deposit, notes=commission_notes)
            st.session_state[f"confirmed_total_{project_id}"] = final_total
            st.session_state[f"confirmed_deposit_{project_id}"] = final_deposit
            add_project_note(project_id, f"Confirmed project value: ${final_total:,.2f}, Deposit: ${final_deposit:,.2f}")
            add_project_touch(project_id, "commission_update", f"Commission updated - Total: ${final_total:,.2f}, Deposit: ${final_deposit:,.2f}")
            if commission_saved:
                st.success("✅ Amounts confirmed and saved to commission ledger!")
            else:
                st.success("✅ Amounts confirmed! (Commission table not available)")
            st.rerun()
        
        if not has_valid_amounts:
            st.caption("Enter valid amounts above before confirming.")
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stage1_done = deposit_invoice_requested
        btn_style = "secondary" if stage1_done else "primary"
        btn_label = "✅ Invoice Requested" if stage1_done else "🔔 Notify Bruno: Request Deposit Invoice"
        
        if st.button(btn_label, key=f"request_invoice_{project_id}", type=btn_style, use_container_width=True, disabled=stage1_done):
            success, msg = send_deposit_invoice_request(BRUNO_EMAIL, client_name, google_drive_link)
            if success:
                add_project_note(project_id, "Deposit invoice requested from Bruno via email")
                add_project_touch(project_id, "email_sent", f"Deposit invoice requested from Bruno ({BRUNO_EMAIL})")
                update_deposit_stage(project_id, "invoice_requested", True)
                if is_test_mode():
                    st.success(f"✅ Email sent to Bruno! (Test mode: redirected from {BRUNO_EMAIL})")
                else:
                    st.success("✅ Email sent to Bruno!")
            else:
                add_project_note(project_id, f"Email to Bruno failed: {msg}")
                update_deposit_stage(project_id, "invoice_requested", True)
                st.warning(f"Request logged, but email failed: {msg}")
            st.rerun()
    
    with col2:
        stage2_enabled = deposit_invoice_requested and not deposit_invoice_sent
        stage2_done = deposit_invoice_sent
        btn_style2 = "secondary" if stage2_done else "primary"
        btn_label2 = "✅ Invoice Sent" if stage2_done else "✉️ Send Deposit Invoice to Customer"
        
        if st.button(btn_label2, key=f"send_invoice_{project_id}", type=btn_style2, use_container_width=True, disabled=not stage2_enabled):
            success, msg = send_deposit_invoice_to_customer(customer_email, client_name, None, google_drive_link)
            if success:
                add_project_note(project_id, "Deposit invoice sent to customer via email")
                add_project_touch(project_id, "email_sent", f"Deposit invoice sent to customer ({customer_email})")
                update_deposit_stage(project_id, "invoice_sent", True)
                if is_test_mode():
                    st.success(f"✅ Invoice sent to customer! (Test mode: redirected from {customer_email})")
                else:
                    st.success(f"✅ Invoice sent to {customer_email}!")
            else:
                add_project_note(project_id, f"Email to customer failed: {msg}")
                update_deposit_stage(project_id, "invoice_sent", True)
                st.warning(f"Stage updated, but email failed: {msg}")
            st.rerun()
    
    with col3:
        stage3_enabled = deposit_invoice_sent
        
        if st.button("💰 Deposit Received & Verified", key=f"deposit_received_{project_id}", type="primary", use_container_width=True, disabled=not stage3_enabled):
            st.session_state[f"show_deposit_form_{project_id}"] = True
            st.rerun()
    
    if st.session_state.get(f"show_deposit_form_{project_id}", False):
        st.markdown("---")
        st.markdown('<p style="color: #00A8E8; font-weight: 600;">Enter Final Deposit Details:</p>', unsafe_allow_html=True)
        
        confirmed_deposit = st.session_state.get(f"confirmed_deposit_{project_id}", scanned_deposit)
        
        deposit_col1, deposit_col2 = st.columns(2)
        
        with deposit_col1:
            deposit_amt = st.number_input("Deposit Amount ($)", min_value=0.0, value=float(confirmed_deposit), step=100.0, key=f"deposit_amt_{project_id}")
        
        with deposit_col2:
            deposit_date = st.date_input("Date Received", value=today_mountain(), key=f"deposit_date_{project_id}")
        
        st.markdown("---")
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #1b4332 0%, #0d1b2a 100%);
                border-radius: 12px;
                padding: 16px;
                margin: 12px 0;
                border: 2px solid #39FF14;
            ">
                <p style="color: #39FF14; margin: 0 0 8px 0; font-size: 16px; font-weight: 600;">
                    🔒 PRODUCTION LOCKDOWN
                </p>
                <p style="color: #E5E5E5; font-size: 13px; margin: 0;">
                    Select the final approved design and upload signed specs before starting production.
                </p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        proposals = get_project_proposals(project_id)
        photos = get_photos_by_categories(project_id)
        all_files = []
        
        for prop in proposals:
            all_files.append({
                "id": f"proposal_{prop.get('id')}",
                "name": prop.get("file_name", "Unknown Proposal"),
                "type": "proposal",
                "is_primary": prop.get("is_primary", False)
            })
        
        for photo in photos.get("markup", []):
            all_files.append({
                "id": f"photo_{photo.get('id')}",
                "name": photo.get("filename", "Unknown"),
                "type": "markup"
            })
        
        for photo in photos.get("site", []):
            all_files.append({
                "id": f"photo_{photo.get('id')}",
                "name": photo.get("filename", "Unknown"),
                "type": "site"
            })
        
        golden_col1, golden_col2 = st.columns([2, 1])
        
        with golden_col1:
            file_options = ["-- Select Final Approved Design --"]
            file_options += [f.get("name") + (" ⭐" if f.get("is_primary") else "") for f in all_files]
            
            current_master_idx = 0
            if master_spec_file_name:
                for i, f in enumerate(all_files):
                    if f.get("name") in master_spec_file_name:
                        current_master_idx = i + 1
                        break
            
            selected_golden = st.selectbox(
                "🏆 Select Golden Proof (Final Approved Design)",
                options=file_options,
                index=current_master_idx,
                key=f"golden_proof_{project_id}"
            )
        
        with golden_col2:
            if selected_golden and selected_golden != "-- Select Final Approved Design --":
                clean_name = selected_golden.replace(" ⭐", "")
                selected_file = next((f for f in all_files if f.get("name") == clean_name), None)
                
                if selected_file and not master_spec_file_id:
                    if st.button("🔒 Lock as Master", key=f"lock_master_{project_id}", type="primary"):
                        success = set_master_spec(project_id, selected_file.get("id"), clean_name, client_name)
                        if success:
                            st.success("✅ Master Spec locked!")
                            st.rerun()
                elif master_spec_file_id:
                    st.markdown(
                        '''<span style="color: #39FF14; font-size: 13px;">✅ PRODUCTION READY</span>''',
                        unsafe_allow_html=True
                    )
        
        if master_spec_file_name:
            st.markdown(
                f'''
                <div style="
                    background: rgba(57, 255, 20, 0.1);
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin: 8px 0;
                    border: 1px solid #39FF14;
                ">
                    <p style="color: #39FF14; margin: 0; font-size: 14px; font-weight: 600;">
                        ✅ MASTER SPEC: {master_spec_file_name}
                    </p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        st.markdown('<p style="color: #FFB800; font-weight: 600;">✍️ Signed Specs/Design (Required for Production)</p>', unsafe_allow_html=True)
        
        if signed_spec_file_name:
            st.markdown(
                f'''
                <div style="
                    background: rgba(40, 167, 69, 0.1);
                    border-radius: 8px;
                    padding: 10px 14px;
                    margin: 8px 0;
                    border: 1px solid #28a745;
                ">
                    <p style="color: #28a745; margin: 0; font-size: 14px;">
                        ✅ Signed spec uploaded: {signed_spec_file_name}
                    </p>
                </div>
                ''',
                unsafe_allow_html=True
            )
        else:
            signed_spec_upload = st.file_uploader(
                "Upload signed design/proposal (PDF or Image)",
                type=["pdf", "jpg", "jpeg", "png"],
                key=f"signed_spec_upload_{project_id}"
            )
            
            if signed_spec_upload:
                if st.button("💾 Save Signed Spec", key=f"save_signed_{project_id}", type="primary"):
                    os.makedirs("./project_files", exist_ok=True)
                    safe_name = signed_spec_upload.name.replace(" ", "_")
                    save_path = f"./project_files/{project_id}_signed_{safe_name}"
                    
                    try:
                        with open(save_path, "wb") as f:
                            f.write(signed_spec_upload.read())
                        
                        success = set_signed_spec(project_id, save_path, signed_spec_upload.name)
                        if success:
                            st.success("✅ Signed spec saved!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
        
        has_signed_spec = bool(signed_spec_file_id)
        has_master_spec = bool(master_spec_file_id)
        
        st.markdown("---")
        confirm_col1, confirm_col2 = st.columns(2)
        
        with confirm_col1:
            btn_disabled = not has_signed_spec or not has_master_spec
            if not has_master_spec:
                st.warning("🚨 STOP: You must select and lock a Golden Proof (Master Spec) before production.")
            elif not has_signed_spec:
                st.warning("🚨 STOP: You must upload the signed design/proposal before locking production.")
            
            if st.button("✅ Confirm Deposit & Lock Production", key=f"confirm_deposit_{project_id}", type="primary", use_container_width=True, disabled=btn_disabled):
                success = mark_deposit_received(project_id, deposit_date, deposit_amt)
                if success:
                    lock_production(project_id)
                    add_project_note(project_id, f"Deposit received: ${deposit_amt:,.2f}. Status changed to ACTIVE PRODUCTION.")
                    add_project_touch(project_id, "deposit_received", f"Deposit of ${deposit_amt:,.2f} received. Production started.")
                    st.session_state[f"show_deposit_form_{project_id}"] = False
                    st.success("✅ Deposit recorded! Project is now in ACTIVE PRODUCTION.")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Failed to record deposit.")
        
        with confirm_col2:
            if st.button("Cancel", key=f"cancel_deposit_{project_id}", use_container_width=True):
                st.session_state[f"show_deposit_form_{project_id}"] = False
                st.rerun()


def render_project_history(project_id: str):
    """Render project touch history section."""
    from services.database_manager import get_project_touches
    
    st.markdown("---")
    st.markdown("### 📜 Project History")
    
    touches = get_project_touches(project_id, limit=15)
    
    if not touches:
        st.markdown('<p style="color: #888;">No history records yet.</p>', unsafe_allow_html=True)
        return
    
    for touch in touches:
        touch_type = touch.get("touch_type", "action")
        note = touch.get("note", "")
        touched_at = touch.get("touched_at")
        
        timestamp_str = touched_at.strftime("%Y-%m-%d %H:%M") if touched_at else ""
        
        icon = "📧" if "email" in touch_type else "💰" if "deposit" in touch_type else "📝"
        
        st.markdown(
            f'''
            <div style="
                background: #1a2a3a;
                border-radius: 8px;
                padding: 10px 14px;
                margin: 4px 0;
                border-left: 3px solid #00A8E8;
            ">
                <span style="color: #00A8E8; font-size: 12px;">{timestamp_str}</span>
                <p style="color: #E5E5E5; margin: 4px 0 0 0; font-size: 14px;">{icon} {note}</p>
            </div>
            ''',
            unsafe_allow_html=True
        )


def render_block_e_production_logistics(project_id: str, client_name: str, status: str, deposit_received_date):
    """Block E: Production & Logistics - Only visible in ACTIVE PRODUCTION status."""
    from services.database_manager import get_production_logistics, save_production_logistics, add_project_touch, get_deposit_received_date
    from datetime import date, timedelta
    
    production_statuses = ["ACTIVE PRODUCTION", "in_production", "production", "ready_for_install", 
                           "installed", "completed", "invoiced", "permit_pending"]
    status_lower = (status or "").lower().replace(" ", "_")
    
    is_production = status_lower in [s.lower().replace(" ", "_") for s in production_statuses]
    
    if not is_production:
        return
    
    st.markdown("---")
    st.markdown("### 🏭 Block E: Production & Logistics")
    
    logistics = get_production_logistics(project_id)
    
    actual_deposit_date = deposit_received_date or get_deposit_received_date(project_id)
    
    if actual_deposit_date:
        today = today_mountain()
        if isinstance(actual_deposit_date, str):
            actual_deposit_date = datetime.strptime(actual_deposit_date, "%Y-%m-%d").date()
        
        days_since_deposit = (today - actual_deposit_date).days
        
        pulse_10_day = days_since_deposit >= 10
        pulse_14_day = days_since_deposit >= 14
        
        if pulse_10_day or pulse_14_day:
            st.markdown("#### ⏰ Pulse Checks")
            
            if pulse_10_day and days_since_deposit < 14:
                st.warning("⚠️ **10-Day Pulse:** Check in with Kristen on permit status")
            
            if pulse_14_day:
                st.warning("⚠️ **2-Week Huddle:** Coordinate with Bruno and customer on site readiness")
                
                if days_since_deposit >= 10:
                    st.info("✅ 10-Day Pulse: Check in with Kristen on permit status (Due)")
    
    st.markdown("#### 📅 Installation Planning")
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_date = logistics.get("target_installation_date")
        if current_date and isinstance(current_date, str):
            from datetime import datetime
            current_date = datetime.strptime(current_date, "%Y-%m-%d").date()
        
        target_date = st.date_input(
            "Target Installation Date",
            value=current_date,
            key=f"target_install_date_{project_id}"
        )
        
        if target_date != current_date:
            save_production_logistics(project_id, target_date=target_date)
            add_project_touch(project_id, "logistics_update", f"Target installation date set to {target_date}")
            st.rerun()
    
    with col2:
        status_options = ["Waiting", "In Production", "Ready for Install", "Delayed"]
        current_status = logistics.get("production_status", "waiting")
        
        status_map = {
            "waiting": "Waiting",
            "in_production": "In Production",
            "ready_for_install": "Ready for Install",
            "delayed": "Delayed"
        }
        reverse_map = {v: k for k, v in status_map.items()}
        
        current_display = status_map.get(current_status, "Waiting")
        
        new_status = st.selectbox(
            "Production Status",
            options=status_options,
            index=status_options.index(current_display) if current_display in status_options else 0,
            key=f"prod_status_{project_id}"
        )
        
        new_status_key = reverse_map.get(new_status, "waiting")
        if new_status_key != current_status:
            save_production_logistics(project_id, status=new_status_key)
            add_project_touch(project_id, "logistics_update", f"Production status changed to {new_status}")
            st.rerun()
    
    st.markdown("#### ✅ Pre-Installation Checklist")
    
    check_col1, check_col2 = st.columns(2)
    
    with check_col1:
        paint_approved = st.checkbox(
            "Paint/Vinyl Samples Approved",
            value=logistics.get("paint_samples_approved", False),
            key=f"paint_approved_{project_id}"
        )
        
        if paint_approved != logistics.get("paint_samples_approved", False):
            save_production_logistics(project_id, paint_approved=paint_approved)
            status_text = "approved" if paint_approved else "unapproved"
            add_project_touch(project_id, "checklist_update", f"Paint/Vinyl samples marked as {status_text}")
            st.rerun()
    
    with check_col2:
        measurements_verified = st.checkbox(
            "Final Site Measurements Verified",
            value=logistics.get("site_measurements_verified", False),
            key=f"measurements_verified_{project_id}"
        )
        
        if measurements_verified != logistics.get("site_measurements_verified", False):
            save_production_logistics(project_id, measurements_verified=measurements_verified)
            status_text = "verified" if measurements_verified else "unverified"
            add_project_touch(project_id, "checklist_update", f"Site measurements marked as {status_text}")
            st.rerun()
    
    if logistics.get("paint_samples_approved") and logistics.get("site_measurements_verified"):
        st.success("✅ All pre-installation checks complete!")
    else:
        remaining = []
        if not logistics.get("paint_samples_approved"):
            remaining.append("Paint/Vinyl Samples")
        if not logistics.get("site_measurements_verified"):
            remaining.append("Site Measurements")
        st.info(f"⏳ Remaining checks: {', '.join(remaining)}")


def render_block_f_installation_prep(project_id: str, client_name: str, status: str, google_drive_link: str = None):
    """Block F: The Final Week (Installation Prep) - Activates when Target Installation Date is set."""
    from services.database_manager import get_production_logistics, get_commission_data, add_project_touch, add_project_note, get_primary_contact_email
    from services.email_service import send_3day_prep_email, send_final_invoice_request, send_night_before_confirmation, is_test_mode
    from datetime import date, timedelta
    
    logistics = get_production_logistics(project_id)
    target_date = logistics.get("target_installation_date")
    
    if not target_date:
        return
    
    if isinstance(target_date, str):
        from datetime import datetime
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    st.markdown("---")
    st.markdown("### 📋 Block F: Installation Prep (The Final Week)")
    
    commission_data = get_commission_data(project_id)
    total_value = float(commission_data.get("total_value") or 0)
    deposit_amount = float(commission_data.get("deposit_amount") or 0)
    balance_due = total_value - deposit_amount
    
    BRUNO_EMAIL = "bruno@kbsignconstruction.com"
    customer_email = get_primary_contact_email(project_id) or "customer@example.com"
    
    st.markdown(f"""
    <div style="background: #1a2a3a; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
        <h4 style="color: #00A8E8; margin: 0 0 10px 0;">💰 Project Financials</h4>
        <div style="display: flex; justify-content: space-between;">
            <div><span style="color: #888;">Total Value:</span> <strong style="color: #E5E5E5;">${total_value:,.2f}</strong></div>
            <div><span style="color: #888;">Deposit Received:</span> <strong style="color: #4CAF50;">${deposit_amount:,.2f}</strong></div>
            <div><span style="color: #888;">Current Balance:</span> <strong style="color: {'#FFB800' if balance_due > 0 else '#4CAF50'};">${balance_due:,.2f}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    today = today_mountain()
    days_until_install = (target_date - today).days
    install_date_str = target_date.strftime("%B %d, %Y")
    
    if days_until_install <= 3 and days_until_install >= 0:
        st.info(f"📅 Installation scheduled in {days_until_install} day(s) - {install_date_str}")
    elif days_until_install < 0:
        st.warning(f"⚠️ Installation date passed ({install_date_str})")
    else:
        st.info(f"📅 Installation scheduled for {install_date_str} ({days_until_install} days away)")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 3-Day Prep Email")
        if st.button("✉️ Send 3-Day Prep Email to Customer", key=f"send_3day_{project_id}", use_container_width=True):
            success, msg = send_3day_prep_email(customer_email, client_name, install_date_str, balance_due)
            if success:
                add_project_note(project_id, f"3-day prep email sent to customer ({customer_email})")
                add_project_touch(project_id, "email_sent", f"3-day prep email sent to customer ({customer_email})")
                if is_test_mode():
                    st.success(f"✅ 3-day prep email sent! (Test mode: redirected from {customer_email})")
                else:
                    st.success(f"✅ 3-day prep email sent to {customer_email}!")
            else:
                st.error(f"Failed to send email: {msg}")
            st.rerun()
    
    with col2:
        st.markdown("#### Final Invoice")
        if balance_due <= 0:
            st.success("✅ Fully Paid - No Final Invoice Needed")
        else:
            if st.button("🔔 Request Final Invoice from Bruno", key=f"request_final_invoice_{project_id}", use_container_width=True):
                success, msg = send_final_invoice_request(BRUNO_EMAIL, client_name, balance_due, google_drive_link)
                if success:
                    add_project_note(project_id, f"Final invoice requested from Bruno - Balance: ${balance_due:,.2f}")
                    add_project_touch(project_id, "email_sent", f"Final invoice requested from Bruno ({BRUNO_EMAIL})")
                    if is_test_mode():
                        st.success(f"✅ Final invoice request sent! (Test mode: redirected from {BRUNO_EMAIL})")
                    else:
                        st.success("✅ Final invoice request sent to Bruno!")
                else:
                    st.error(f"Failed to send request: {msg}")
                st.rerun()
    
    with col3:
        st.markdown("#### Night-Before Confirmation")
        
        cc_bruno = st.checkbox(
            "📧 Send CC/FYI to Bruno",
            value=False,
            key=f"cc_bruno_{project_id}",
            help="Send a copy to Bruno when confirming the installation"
        )
        
        if st.button("📱 Send Night-Before Text/Email", key=f"send_night_before_{project_id}", use_container_width=True):
            success, msg = send_night_before_confirmation(customer_email, client_name, install_date_str)
            if success:
                add_project_note(project_id, f"Night-before confirmation sent to customer ({customer_email})")
                add_project_touch(project_id, "email_sent", f"Night-before confirmation sent ({customer_email})")
                
                if cc_bruno:
                    from services.email_service import send_email
                    bruno_subject = f"FYI: Installation Confirmed - {client_name}"
                    bruno_body = f"""Hi Bruno,

FYI: Just confirmed {install_date_str}'s install with {client_name}.

The customer has been notified and we're all set for tomorrow.

- KB Signs Team
"""
                    send_email(BRUNO_EMAIL, bruno_subject, bruno_body)
                    add_project_note(project_id, f"Bruno notified of installation confirmation")
                
                from services.database_manager import clear_action_status
                clear_action_status(project_id)
                add_project_history(project_id, "AUTO_COMPLETE", f"✅ AUTO-COMPLETED: Night-before confirmation sent for installation")
                
                if is_test_mode():
                    st.success(f"✅ Night-before confirmation sent! (Test mode: redirected from {customer_email})")
                else:
                    st.success(f"✅ Night-before confirmation sent to {customer_email}!")
                if cc_bruno:
                    st.info("📧 Bruno has been notified")
            else:
                st.error(f"Failed to send confirmation: {msg}")
            st.rerun()


def render_block_g_project_closeout(project_id: str, client_name: str, status: str):
    """Block G: Project Closeout & Final Commission."""
    from services.database_manager import get_commission_data, close_project_with_final_payment, add_project_touch, add_project_note
    
    production_statuses = ["ACTIVE PRODUCTION", "in_production", "production", "ready_for_install", 
                           "installed", "permit_pending"]
    status_lower = (status or "").lower().replace(" ", "_")
    
    is_production = status_lower in [s.lower().replace(" ", "_") for s in production_statuses]
    is_completed = status_lower == "completed"
    
    if not is_production and not is_completed:
        return
    
    st.markdown("---")
    st.markdown("### 🏁 Block G: Project Closeout & Final Commission")
    
    commission_data = get_commission_data(project_id)
    total_value = float(commission_data.get("total_value") or 0)
    deposit_amount = float(commission_data.get("deposit_amount") or 0)
    final_payment_date = commission_data.get("final_payment_date")
    total_received = float(commission_data.get("total_amount_received") or 0)
    
    balance_due = total_value - deposit_amount
    display_total_received = total_received if total_received > 0 else total_value
    balance_color = '#FFB800' if balance_due > 0 else '#4CAF50'
    
    st.markdown(f"""
    <div style="background: #1a2a3a; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
        <h4 style="color: #00A8E8; margin: 0 0 10px 0;">📊 Final Commission Summary</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
            <div><span style="color: #888;">Total Project Value:</span> <strong style="color: #E5E5E5;">${total_value:,.2f}</strong></div>
            <div><span style="color: #888;">Deposit Received:</span> <strong style="color: #4CAF50;">${deposit_amount:,.2f}</strong></div>
            <div><span style="color: #888;">Final Balance Due:</span> <strong style="color: {balance_color};">${balance_due:,.2f}</strong></div>
            <div><span style="color: #888;">Total Received:</span> <strong style="color: #4CAF50;">${display_total_received:,.2f}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if is_completed and final_payment_date:
        st.success(f"✅ Project Completed - Final payment received on {final_payment_date}")
        st.markdown(f"**Total Amount Received:** ${total_received:,.2f}")
    else:
        final_amount = st.number_input(
            "Total Amount Received ($)",
            min_value=0.0,
            value=float(total_value),
            step=100.0,
            key=f"final_amount_{project_id}"
        )
        
        if st.button("🏁 Final Balance Received - Close Project", key=f"close_project_{project_id}", type="primary", use_container_width=True):
            success = close_project_with_final_payment(project_id, final_amount)
            if success:
                add_project_note(project_id, f"Project COMPLETED - Final payment: ${final_amount:,.2f}")
                add_project_touch(project_id, "project_closed", f"Project closed with final payment: ${final_amount:,.2f}")
                st.success("🎉 Project marked as COMPLETED! Final commission locked.")
                st.balloons()
            else:
                st.error("Failed to close project. Please try again.")
            st.rerun()


@st.dialog("Mark Project as Lost")
def render_project_lost_dialog(project_id: str, client_name: str):
    """Dialog to capture reason when marking a project as lost."""
    KB_GREEN = "#39FF14"
    KB_TEXT = "#E5E5E5"
    KB_MUTED = "#888888"
    KB_CARD_BG = "#111111"
    
    st.markdown(
        f'''
        <div style="background: {KB_CARD_BG}; padding: 12px; border-radius: 8px; margin-bottom: 12px; border: 1px solid #ff4444;">
            <p style="color: #ff4444; margin: 0; font-size: 14px;">
                🪦 Marking <strong>{client_name}</strong> as Lost
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    loss_reason = st.text_input(
        "Why was this deal lost? (1 sentence)",
        placeholder="e.g., Price too high, Went with competitor, Budget constraints...",
        key=f"loss_reason_{project_id}"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("❌ Confirm Lost", type="primary", use_container_width=True):
            success = mark_project_lost(project_id, loss_reason)
            if success:
                st.toast(f"Project marked as Lost", icon="🪦")
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Failed to mark project as lost")
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


def render_project_decision(project_id: str, client_name: str, status: str, deposit_received_date=None):
    """Render Project Decision section with Won/Lost buttons.
    
    Only shows inside Block D when deposit has been received OR project is in production.
    This ensures Won/Lost buttons appear at the proper final stage.
    """
    KB_GREEN = "#39FF14"
    KB_TEXT = "#E5E5E5"
    KB_MUTED = "#888888"
    KB_CARD_BG = "#111111"
    
    status_lower = (status or "").lower().replace(" ", "_")
    
    if status_lower in ['closed_-_won', 'closed_-_lost', 'completed', 'archived', 'new']:
        return
    
    is_deposit_received = deposit_received_date is not None
    production_statuses = ['active_production', 'in_production', 'production', 
                           'ready_for_install', 'installed', 'confirmed']
    is_in_production = status_lower in production_statuses
    
    if not is_deposit_received and not is_in_production:
        return
    
    st.markdown("---")
    st.markdown(
        f'''
        <div style="margin: 16px 0;">
            <p style="color: {KB_GREEN}; font-size: 16px; font-weight: 600; margin: 0 0 8px 0;">
                🏆 Ready to Close as Won?
            </p>
            <p style="color: {KB_MUTED}; font-size: 12px; margin: 0;">
                Deposit received and production in sight - mark this deal as a Win!
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    if st.button("🏆 Project Won", key=f"mark_won_{project_id}", type="primary", use_container_width=True):
        success = mark_project_won(project_id)
        if success:
            st.toast(f"Project marked as Won!", icon="🏆")
            st.balloons()
            st.session_state.page = "dashboard"
            st.rerun()
        else:
            st.error("Failed to mark project as won")
