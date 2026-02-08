"""
Visual Attachment Station Component
Displays thumbnail grid with checkboxes for selecting files to attach to emails.
Includes 10MB size warning and automatic Drive link fallback.
"""
import streamlit as st
import os
import base64
from io import BytesIO

KB_GREEN = "#39FF14"
KB_DARK = "#0a0a0a"
KB_CARD_BG = "#111111"
KB_BORDER = "#222222"
KB_TEXT = "#E5E5E5"
KB_MUTED = "#888888"

MAX_ATTACHMENT_SIZE_MB = 10
MAX_ATTACHMENT_SIZE_BYTES = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024


def get_file_size(file_path: str) -> int:
    """Get file size in bytes, returns 0 if file doesn't exist."""
    try:
        if file_path and os.path.exists(file_path):
            return os.path.getsize(file_path)
    except:
        pass
    return 0


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


def get_thumbnail_html(file_path: str, file_name: str, category: str) -> str:
    """Generate thumbnail HTML for a file."""
    icon_map = {
        "site": "camera",
        "logo": "palette",
        "reference": "image",
        "markup": "edit-3"
    }
    icon = icon_map.get(category, "file")
    
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            ext = file_name.lower().split('.')[-1] if '.' in file_name else 'jpg'
            mime = f"image/{ext}" if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp'] else "application/octet-stream"
            return f'''
                <img src="data:{mime};base64,{img_data}" 
                     style="width: 48px; height: 48px; object-fit: cover; border-radius: 6px; border: 1px solid {KB_BORDER};"
                     alt="{file_name}"/>
            '''
        except:
            pass
    
    return f'''
        <div style="width: 48px; height: 48px; background: {KB_CARD_BG}; border-radius: 6px; 
                    border: 1px solid {KB_BORDER}; display: flex; align-items: center; justify-content: center;">
            <span style="color: {KB_MUTED}; font-size: 20px;">📄</span>
        </div>
    '''


def render_attachment_station(project_id: str, dialog_key: str) -> dict:
    """
    Render the visual attachment station with thumbnail grid and checkboxes.
    
    Args:
        project_id: Project ID for fetching files
        dialog_key: Unique key prefix for this dialog instance
        
    Returns:
        dict with keys:
            - selected_files: List of selected file dicts (path, name, size, category)
            - total_size: Total size in bytes of selected files
            - exceeds_limit: Boolean if total exceeds 10MB
            - use_drive_links: Boolean if should fall back to Drive links
    """
    from services.database_manager import get_photos_by_categories, get_project_by_id
    
    photos = get_photos_by_categories(project_id)
    project = get_project_by_id(project_id)
    
    all_files = []
    
    for category, photo_list in photos.items():
        for photo in photo_list:
            file_path = photo.get("file_path", "")
            if not file_path:
                file_data = photo.get("file_data")
                if file_data:
                    temp_dir = os.path.join(os.path.dirname(__file__), "..", "temp_attachments")
                    os.makedirs(temp_dir, exist_ok=True)
                    temp_path = os.path.join(temp_dir, f"{photo.get('id', 'temp')}_{photo.get('filename', 'file')}")
                    try:
                        with open(temp_path, "wb") as f:
                            f.write(file_data)
                        file_path = temp_path
                    except:
                        continue
            
            if file_path and os.path.exists(file_path):
                all_files.append({
                    "id": photo.get("id", ""),
                    "path": file_path,
                    "name": photo.get("filename", "Unknown"),
                    "category": category,
                    "size": get_file_size(file_path)
                })
    
    if not all_files:
        st.markdown(
            f'<p style="color: {KB_MUTED}; font-size: 12px; font-style: italic;">No attachments available in Shoebox</p>',
            unsafe_allow_html=True
        )
        return {
            "selected_files": [],
            "total_size": 0,
            "exceeds_limit": False,
            "use_drive_links": False
        }
    
    st.markdown(
        f'<p style="color: {KB_TEXT}; font-size: 13px; margin: 12px 0 8px 0; font-weight: 600;">Attachments:</p>',
        unsafe_allow_html=True
    )
    
    session_key = f"attach_selected_{dialog_key}_{project_id}"
    if session_key not in st.session_state:
        st.session_state[session_key] = {f["id"]: True for f in all_files}
    
    selected_files = []
    total_size = 0
    
    category_order = ["site", "logo", "markup", "reference"]
    files_by_category = {cat: [] for cat in category_order}
    for f in all_files:
        cat = f.get("category", "site")
        if cat in files_by_category:
            files_by_category[cat].append(f)
        else:
            files_by_category["site"].append(f)
    
    for category in category_order:
        cat_files = files_by_category[category]
        if not cat_files:
            continue
        
        cat_labels = {
            "site": "Site Photos",
            "logo": "Logos",
            "markup": "Markups",
            "reference": "Reference"
        }
        
        cat_count_note = f" ({len(cat_files)})" if len(cat_files) > 8 else ""
        st.markdown(
            f'<p style="color: {KB_GREEN}; font-size: 11px; margin: 8px 0 4px 0; text-transform: uppercase; letter-spacing: 1px;">{cat_labels.get(category, category)}{cat_count_note}</p>',
            unsafe_allow_html=True
        )
        
        files_to_show = cat_files[:8]
        if len(cat_files) > 8:
            st.markdown(
                f'<p style="color: {KB_MUTED}; font-size: 10px; margin: 0 0 4px 0; font-style: italic;">Showing first 8 of {len(cat_files)} files</p>',
                unsafe_allow_html=True
            )
        
        cols = st.columns(min(len(files_to_show), 4))
        for i, file_info in enumerate(files_to_show):
            col_idx = i % 4
            with cols[col_idx]:
                file_id = file_info["id"]
                checkbox_key = f"{dialog_key}_attach_{file_id}"
                
                is_selected = st.session_state[session_key].get(file_id, True)
                
                st.markdown(
                    get_thumbnail_html(file_info["path"], file_info["name"], category),
                    unsafe_allow_html=True
                )
                
                short_name = file_info["name"][:12] + ".." if len(file_info["name"]) > 12 else file_info["name"]
                size_str = format_file_size(file_info["size"])
                
                new_selected = st.checkbox(
                    f"{short_name} ({size_str})",
                    value=is_selected,
                    key=checkbox_key,
                    help=file_info["name"]
                )
                
                st.session_state[session_key][file_id] = new_selected
                
                if new_selected:
                    selected_files.append(file_info)
                    total_size += file_info["size"]
    
    exceeds_limit = total_size > MAX_ATTACHMENT_SIZE_BYTES
    
    st.markdown(
        f'''<div style="margin-top: 8px; padding: 6px 10px; background: {KB_CARD_BG}; border-radius: 6px; 
                       display: flex; justify-content: space-between; align-items: center;">
            <span style="color: {KB_TEXT}; font-size: 12px;">{len(selected_files)} files selected</span>
            <span style="color: {'#e74c3c' if exceeds_limit else KB_GREEN}; font-size: 12px; font-weight: 600;">
                {format_file_size(total_size)} / {MAX_ATTACHMENT_SIZE_MB}MB
            </span>
        </div>''',
        unsafe_allow_html=True
    )
    
    if exceeds_limit:
        st.markdown(
            f'''<div style="margin-top: 6px; padding: 8px 10px; background: rgba(231, 76, 60, 0.15); 
                           border: 1px solid #e74c3c; border-radius: 6px;">
                <p style="color: #e74c3c; font-size: 12px; margin: 0;">
                    Large attachments - switching to secure Google Drive links
                </p>
            </div>''',
            unsafe_allow_html=True
        )
    
    return {
        "selected_files": selected_files,
        "total_size": total_size,
        "exceeds_limit": exceeds_limit,
        "use_drive_links": exceeds_limit
    }


def prepare_attachments(selected_files: list) -> list:
    """
    Prepare attachment data for email sending.
    
    Args:
        selected_files: List of file dicts from render_attachment_station
        
    Returns:
        List of attachment dicts with buffer, filename, mime_type
    """
    import mimetypes
    
    attachments = []
    for file_info in selected_files:
        try:
            with open(file_info["path"], "rb") as f:
                file_data = f.read()
            file_buffer = BytesIO(file_data)
            mime_type, _ = mimetypes.guess_type(file_info["name"])
            attachments.append({
                "buffer": file_buffer,
                "filename": file_info["name"],
                "mime_type": mime_type or "application/octet-stream"
            })
        except Exception as e:
            print(f"Warning: Could not read file {file_info['path']}: {e}")
    
    return attachments


def get_attachment_filenames(selected_files: list) -> list:
    """Get list of filenames from selected files for history logging."""
    return [f["name"] for f in selected_files]
