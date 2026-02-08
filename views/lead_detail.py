import streamlit as st
from datetime import datetime
from services.database_manager import get_lead_by_id, add_lead_note, update_lead_status, get_project_history
from services.email_service import send_email
from services.timezone_utils import now_mountain


def render_lead_detail():
    """Render the Lead Detail View with notes and contact options."""
    lead_id = st.session_state.get("current_lead_id")
    
    if not lead_id:
        st.warning("No lead selected.")
        if st.button("← Back to Dashboard", type="primary"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return
    
    lead = get_lead_by_id(lead_id)
    
    if not lead:
        st.error(f"Lead not found: {lead_id}")
        if st.button("← Back to Dashboard", type="primary"):
            st.session_state.page = "Dashboard"
            st.rerun()
        return
    
    lead_name = lead.get("name") or "Unknown"
    lead_phone = lead.get("phone") or ""
    lead_email = lead.get("email") or ""
    lead_notes = lead.get("notes") or ""
    lead_source = lead.get("source", "manual")
    lead_status = lead.get("status", "new")
    created_at = lead.get("created_at")
    
    source_badge = "Zapier" if lead_source == "zapier" else "Smart Intake"
    source_color = "#FFB800" if lead_source == "zapier" else "#00A8E8"
    status_color = "#e74c3c" if lead_status == "New" else "#00A8E8"
    status_text = "NEW" if lead_status == "New" else "BLOCK A"
    
    col_back, col_title = st.columns([1, 5])
    
    with col_back:
        if st.button("← Back", type="secondary"):
            st.session_state.page = "Dashboard"
            st.rerun()
    
    with col_title:
        st.markdown(
            f'''
            <div style="display: flex; align-items: center; gap: 12px;">
                <h1 style="color: #E5E5E5; margin: 0; font-size: 28px;">{lead_name}</h1>
                <span style="background: {source_color}; color: white; padding: 4px 10px; border-radius: 8px; font-size: 12px;">{source_badge}</span>
                <span style="background: {status_color}; color: white; padding: 4px 10px; border-radius: 8px; font-size: 12px;">{status_text}</span>
            </div>
            ''',
            unsafe_allow_html=True
        )
    
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(
            f'''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 16px;
                padding: 20px;
                border-left: 4px solid #00A8E8;
            ">
                <h3 style="color: #E5E5E5; margin: 0 0 16px 0;">Contact Information</h3>
                <p style="color: #E5E5E5; margin: 8px 0;">📞 <strong>Phone:</strong> {lead_phone or 'Not provided'}</p>
                <p style="color: #E5E5E5; margin: 8px 0;">✉️ <strong>Email:</strong> {lead_email or 'Not provided'}</p>
                <p style="color: #888; margin: 8px 0; font-size: 12px;">📅 Created: {created_at.strftime('%b %d, %Y at %I:%M %p') if created_at else 'Unknown'}</p>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
        
        if lead_notes:
            st.markdown(
                f'''
                <div style="
                    background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                    border-radius: 16px;
                    padding: 20px;
                    border-left: 4px solid #00A8E8;
                ">
                    <h3 style="color: #E5E5E5; margin: 0 0 12px 0;">Initial Notes</h3>
                    <p style="color: #E5E5E5; white-space: pre-wrap;">{lead_notes}</p>
                </div>
                ''',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown(
            '''
            <div style="
                background: linear-gradient(145deg, #1a2a3a 0%, #0d1b2a 100%);
                border-radius: 16px;
                padding: 20px;
                border-left: 4px solid #00A8E8;
            ">
                <h3 style="color: #E5E5E5; margin: 0 0 12px 0;">Contact Suite</h3>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        col_email, col_text, col_call = st.columns(3)
        
        with col_email:
            if st.button("📧 Email", key=f"ld_email_{lead_id}", use_container_width=True):
                st.session_state[f"show_lead_email_dialog_{lead_id}"] = True
                st.rerun()
        
        with col_text:
            if st.button("💬 Text", key=f"ld_text_{lead_id}", use_container_width=True):
                st.session_state[f"show_lead_text_dialog_{lead_id}"] = True
                st.rerun()
        
        with col_call:
            if st.button("📞 Call", key=f"ld_call_{lead_id}", use_container_width=True):
                update_lead_status(lead_id, "Block A")
                st.toast(f"📞 {lead_name} → Block A", icon="✅")
                st.rerun()
    
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    with st.expander("📝 Add Note", expanded=False):
        note_key = f"lead_note_{lead_id}"
        note_content = st.text_area(
            "Add a note about this lead",
            key=note_key,
            placeholder="Enter your notes here...",
            height=100
        )
        
        if st.button("💾 Save Note", key=f"save_note_{lead_id}", type="primary"):
            if note_content and note_content.strip():
                if add_lead_note(lead_id, note_content.strip()):
                    st.toast("✅ Note saved! → Block A", icon="📝")
                    st.session_state[note_key] = ""
                    st.rerun()
                else:
                    st.error("Failed to save note")
            else:
                st.warning("Please enter a note before saving")
    
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    
    with st.expander("📜 History", expanded=False):
        history = get_project_history(str(lead_id), limit=20)
        
        if history:
            for entry in history:
                entry_type = entry.get("entry_type", "")
                content = entry.get("content", "")
                created = entry.get("created_at")
                
                st.markdown(
                    f'''
                    <div style="
                        background: #1a2a3a;
                        padding: 10px 14px;
                        border-radius: 8px;
                        margin: 6px 0;
                        border-left: 3px solid #00A8E8;
                    ">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="color: #00A8E8; font-size: 11px; text-transform: uppercase;">{entry_type}</span>
                            <span style="color: #888; font-size: 11px;">{created.strftime('%b %d, %I:%M %p') if created else ''}</span>
                        </div>
                        <p style="color: #E5E5E5; margin: 0; font-size: 13px;">{content}</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
        else:
            st.info("No history entries yet")
    
    if st.session_state.get(f"show_lead_email_dialog_{lead_id}"):
        render_lead_email_dialog(lead)
    
    if st.session_state.get(f"show_lead_text_dialog_{lead_id}"):
        render_lead_text_dialog(lead)


@st.dialog("📧 Draft Email", width="large")
def render_lead_email_dialog(lead: dict):
    """Render email composition dialog for a lead."""
    lead_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "there"
    lead_email = lead.get("email") or ""
    
    to_key = f"lead_email_to_{lead_id}"
    subject_key = f"lead_email_subject_{lead_id}"
    body_key = f"lead_email_body_{lead_id}"
    
    if to_key not in st.session_state:
        st.session_state[to_key] = lead_email
    if subject_key not in st.session_state:
        st.session_state[subject_key] = f"KB Signs - Your Sign Project Inquiry"
    if body_key not in st.session_state:
        st.session_state[body_key] = f"""Hi {lead_name},

Thank you for reaching out to KB Signs! I'm excited to discuss your signage needs.

I'd love to learn more about your project. Could you share a few details?
- What type of sign are you looking for?
- Where will it be installed?
- Do you have a timeline in mind?

I'm available for a call whenever works best for you. Looking forward to connecting!

Best regards,
Kam Gray
KB Signs
(916) 832-6606"""
    
    to_address = st.text_input("To:", value=st.session_state[to_key], key=f"{to_key}_input")
    subject = st.text_input("Subject:", value=st.session_state[subject_key], key=f"{subject_key}_input")
    
    col_body, col_mic = st.columns([10, 1])
    with col_body:
        body = st.text_area("Message:", value=st.session_state[body_key], key=f"{body_key}_input", height=250)
    with col_mic:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        render_voice_button(lead_id, f"{body_key}_input", "lead_email")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Send Email", type="primary", use_container_width=True):
            if to_address and subject and body:
                success = send_email(to_address, subject, body)
                if success:
                    update_lead_status(lead_id, "Block A")
                    add_lead_note(lead_id, f"Sent outreach email: {subject}")
                    st.toast("✅ Email sent! → Block A", icon="📧")
                    st.session_state[f"show_lead_email_dialog_{lead_id}"] = False
                    del st.session_state[to_key]
                    del st.session_state[subject_key]
                    del st.session_state[body_key]
                    st.rerun()
                else:
                    st.error("Failed to send email")
            else:
                st.warning("Please fill in all fields")
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state[f"show_lead_email_dialog_{lead_id}"] = False
            st.rerun()


@st.dialog("💬 Draft Text", width="large")
def render_lead_text_dialog(lead: dict):
    """Render text message composition dialog for a lead."""
    lead_id = str(lead.get("id", ""))
    lead_name = lead.get("name") or "there"
    lead_phone = lead.get("phone") or ""
    
    body_key = f"lead_text_body_{lead_id}"
    
    if body_key not in st.session_state:
        st.session_state[body_key] = f"Hi {lead_name}! This is Kam from KB Signs. Thanks for reaching out about your sign project! When would be a good time to chat? - Kam"
    
    st.markdown(f"**To:** {lead_phone or 'No phone number'}")
    
    col_body, col_mic = st.columns([10, 1])
    with col_body:
        body = st.text_area("Message:", value=st.session_state[body_key], key=f"{body_key}_input", height=150)
    with col_mic:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        render_voice_button(lead_id, f"{body_key}_input", "lead_text")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Mark Text Sent", type="primary", use_container_width=True):
            update_lead_status(lead_id, "Block A")
            body_preview = (body[:100] + "...") if body and len(body) > 100 else (body or "")
            add_lead_note(lead_id, f"Sent text message: {body_preview}")
            st.toast("✅ Text sent! → Block A", icon="💬")
            st.session_state[f"show_lead_text_dialog_{lead_id}"] = False
            del st.session_state[body_key]
            st.rerun()
    
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.session_state[f"show_lead_text_dialog_{lead_id}"] = False
            st.rerun()


def render_voice_button(lead_id: str, target_key: str, dialog_type: str):
    """Render voice dictation button for lead dialogs."""
    import streamlit.components.v1 as components
    from streamlit_js_eval import streamlit_js_eval
    import json
    
    voice_key = f"voice_{dialog_type}_{lead_id}"
    recording_key = f"recording_{dialog_type}_{lead_id}"
    result_key = f"voice_result_{dialog_type}_{lead_id}"
    error_key = f"voice_error_{dialog_type}_{lead_id}"
    
    if result_key in st.session_state and st.session_state[result_key]:
        result = st.session_state[result_key]
        st.session_state[result_key] = None
        st.session_state[recording_key] = False
        
        current = st.session_state.get(target_key, "")
        if current:
            st.session_state[target_key] = current + " " + result
        else:
            st.session_state[target_key] = result
        
        st.toast(f"✅ Added: {result}", icon="🎤")
        st.rerun()
    
    if error_key in st.session_state and st.session_state[error_key]:
        error = st.session_state[error_key]
        st.session_state[error_key] = None
        st.session_state[recording_key] = False
        st.error(f"🎤 Voice error: {error}")
    
    is_recording = st.session_state.get(recording_key, False)
    
    if is_recording:
        if st.button("🔴", key=f"{voice_key}_stop", help="Click to cancel"):
            st.session_state[recording_key] = False
            st.rerun()
        
        components.html(f"""
        <style>
            @keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.5; }} }}
            .rec {{ color:#e74c3c; animation:pulse 1s infinite; font-size:12px; }}
        </style>
        <div class="rec">🔴 Recording...</div>
        <script>
        (function() {{
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) {{ sessionStorage.setItem('vd_error_{voice_key}','not_supported'); return; }}
            const r = new SR();
            r.lang = 'en-US';
            r.interimResults = false;
            r.onresult = (e) => {{ sessionStorage.setItem('vd_result_{voice_key}', e.results[0][0].transcript); }};
            r.onerror = (e) => {{ sessionStorage.setItem('vd_error_{voice_key}', e.error); }};
            r.onend = () => {{ sessionStorage.setItem('vd_ended_{voice_key}', 'true'); }};
            try {{ r.start(); }} catch(e) {{}}
        }})();
        </script>
        """, height=30)
        
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
                    st.warning("No speech detected.")
                    st.rerun()
        except Exception as e:
            print(f"[VoiceDictation] Poll error: {e}")
    else:
        if st.button("🎙️", key=f"{voice_key}_start", help="Voice dictation"):
            st.session_state[recording_key] = True
            st.rerun()
