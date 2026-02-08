"""
Temporary Migration Utility for bulk-importing legacy projects from Google Drive.
DELETE THIS FILE after migration is complete.
"""

import streamlit as st
import os
import requests
import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from services.timezone_utils import now_mountain

TENANT_ID = "357145e4-b5a1-43e3-a9ba-f8e834b38034"
SIGN_PROJECTS_FOLDER_ID = "0ALUqW4toI01BUk9PVA"


def fuzzy_match(name1: str, name2: str, threshold: float = 0.7) -> bool:
    """Check if two names have at least threshold% character overlap."""
    if not name1 or not name2:
        return False
    
    n1 = name1.lower().strip()
    n2 = name2.lower().strip()
    
    if n1 == n2:
        return True
    
    if n1 in n2 or n2 in n1:
        return True
    
    words1 = set(n1.replace('_', ' ').replace('-', ' ').split())
    words2 = set(n2.replace('_', ' ').replace('-', ' ').split())
    
    if not words1 or not words2:
        return False
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    similarity = intersection / union if union > 0 else 0
    
    return similarity >= threshold


def find_drive_folder_fuzzy(access_token: str, project_name: str) -> tuple:
    """Find a Drive folder by fuzzy matching the project name (70% threshold)."""
    folders, err = list_drive_folders(access_token, SIGN_PROJECTS_FOLDER_ID)
    if err:
        return None, err
    
    for folder in folders:
        if fuzzy_match(project_name, folder.get("name", ""), threshold=0.7):
            return folder, None
    
    return None, "No matching folder found"


def update_project_drive_folder(project_id: str, folder_id: str, folder_link: str = "") -> tuple:
    """Update a project's Google Drive folder ID."""
    from services.database_manager import get_engine
    
    engine = get_engine()
    if engine is None:
        return False, "Database connection not available"
    
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    UPDATE projects 
                    SET google_drive_folder_id = :folder_id,
                        google_drive_link = :folder_link
                    WHERE id = :project_id AND tenant_id = :tenant_id
                """),
                {
                    "folder_id": folder_id,
                    "folder_link": folder_link,
                    "project_id": project_id,
                    "tenant_id": TENANT_ID
                }
            )
            if result.rowcount > 0:
                return True, None
            return False, "Project not found"
    except SQLAlchemyError as e:
        return False, str(e)


def extract_folder_id_from_url(url: str) -> str:
    """Extract folder ID from a Google Drive URL."""
    import re
    
    patterns = [
        r'folders/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    if len(url) > 20 and '/' not in url and '.' not in url:
        return url.strip()
    
    return ""


def get_drive_access_token():
    """Get Google Drive access token from Replit connector."""
    hostname = os.environ.get("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.environ.get("REPL_IDENTITY")
    web_repl_renewal = os.environ.get("WEB_REPL_RENEWAL")
    
    if repl_identity:
        x_replit_token = f"repl {repl_identity}"
    elif web_repl_renewal:
        x_replit_token = f"depl {web_repl_renewal}"
    else:
        return None, "Replit identity token not found"
    
    if not hostname:
        return None, "Connector hostname not found"
    
    try:
        response = requests.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-drive",
            headers={
                "Accept": "application/json",
                "X_REPLIT_TOKEN": x_replit_token
            },
            timeout=10
        )
        data = response.json()
        items = data.get("items", [])
        if not items:
            return None, "Google Drive not connected"
        
        connection = items[0]
        settings = connection.get("settings", {})
        access_token = settings.get("access_token") or settings.get("oauth", {}).get("credentials", {}).get("access_token")
        
        if not access_token:
            return None, "No access token found"
        
        return access_token, None
    except Exception as e:
        return None, f"Error getting access token: {str(e)}"


def list_drive_folders(access_token: str, parent_folder_id: str):
    """List folders in a Shared Drive folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    query = f"'{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    
    try:
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "q": query,
                "fields": "files(id,name,webViewLink)",
                "pageSize": 100,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "corpora": "allDrives"
            },
            timeout=15
        )
        data = response.json()
        return data.get("files", []), None
    except Exception as e:
        return [], f"Error listing folders: {str(e)}"


ALLOWED_IMAGE_MIMES = ["image/jpeg", "image/png", "image/jpg", "image/gif", "image/webp"]


def list_drive_images(access_token: str, folder_id: str):
    """List image files in a Shared Drive folder, excluding shortcuts, invalid files, and unsupported types."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    query = f"'{folder_id}' in parents and (mimeType contains 'image/') and trashed=false"
    
    try:
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "q": query,
                "fields": "files(id,name,mimeType,thumbnailLink,webViewLink,size)",
                "pageSize": 50,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true"
            },
            timeout=15
        )
        data = response.json()
        files = data.get("files", [])
        
        valid_files = []
        for f in files:
            mime = f.get("mimeType", "")
            size = int(f.get("size", 0) or 0)
            
            if mime.startswith("application/vnd.google-apps.shortcut"):
                continue
            
            if size == 0:
                continue
            
            if mime not in ALLOWED_IMAGE_MIMES:
                continue
            
            valid_files.append(f)
        
        return valid_files, None
    except Exception as e:
        return [], f"Error listing images: {str(e)}"


def list_drive_pdfs(access_token: str, folder_id: str):
    """List PDF files in a Shared Drive folder."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    
    try:
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "q": query,
                "fields": "files(id,name,mimeType,webViewLink)",
                "pageSize": 50,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
                "corpora": "allDrives"
            },
            timeout=15
        )
        data = response.json()
        return data.get("files", []), None
    except Exception as e:
        return [], f"Error listing PDFs: {str(e)}"


def create_archive_folder(access_token: str, parent_folder_id: str):
    """Create _ARCHIVE subfolder in a Shared Drive folder."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "supportsAllDrives": "true"
            },
            json={
                "name": "_ARCHIVE",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_folder_id]
            },
            timeout=15
        )
        data = response.json()
        return data.get("id"), None
    except Exception as e:
        return None, f"Error creating archive folder: {str(e)}"


def get_or_create_archive_folder(access_token: str, parent_folder_id: str):
    """Get existing _ARCHIVE folder or create one in Shared Drive."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    query = f"'{parent_folder_id}' in parents and name='_ARCHIVE' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    
    try:
        response = requests.get(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            params={
                "q": query,
                "fields": "files(id)",
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true"
            },
            timeout=10
        )
        data = response.json()
        files = data.get("files", [])
        
        if files:
            return files[0]["id"], None
        else:
            return create_archive_folder(access_token, parent_folder_id)
    except Exception as e:
        return None, f"Error checking archive folder: {str(e)}"


def move_file_to_archive(access_token: str, file_id: str, current_parent_id: str, archive_folder_id: str):
    """Move a file to the archive folder in Shared Drive."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.patch(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={
                "addParents": archive_folder_id,
                "removeParents": current_parent_id,
                "supportsAllDrives": "true"
            },
            timeout=10
        )
        return response.status_code == 200, None
    except Exception as e:
        return False, f"Error moving file: {str(e)}"


def get_existing_project_names():
    """Get list of existing project client names from database."""
    from services.database_manager import get_engine
    
    engine = get_engine()
    if engine is None:
        return []
    
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT client_name, google_drive_link FROM projects WHERE tenant_id = :tenant_id"),
                {"tenant_id": TENANT_ID}
            )
            return [(row[0], row[1]) for row in result.fetchall()]
    except SQLAlchemyError:
        return []


def create_migrated_project(folder_name: str, drive_link: str, drive_folder_id: str):
    """Create a new project with MIGRATED status."""
    from services.database_manager import get_engine
    
    engine = get_engine()
    if engine is None:
        return None, "Database not connected"
    
    project_id = str(uuid.uuid4())
    
    try:
        with engine.connect() as conn:
            conn.execute(
                text("""
                    INSERT INTO projects (id, tenant_id, client_name, status, notes, google_drive_link, google_drive_folder_id, is_active_v3, created_at)
                    VALUES (:id, :tenant_id, :client_name, :status, :notes, :drive_link, :drive_folder_id, TRUE, NOW())
                """),
                {
                    "id": project_id,
                    "tenant_id": TENANT_ID,
                    "client_name": folder_name,
                    "status": "MIGRATED",
                    "notes": f"Imported from Google Drive on {now_mountain().strftime('%Y-%m-%d')}",
                    "drive_link": drive_link,
                    "drive_folder_id": drive_folder_id
                }
            )
            conn.commit()
            return project_id, None
    except SQLAlchemyError as e:
        return None, f"Database error: {str(e)}"


def render_migration_dashboard():
    """Render the temporary migration dashboard."""
    st.markdown(
        '''
        <div style="
            background: linear-gradient(145deg, #FF6B35 0%, #F7931E 100%);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            text-align: center;
        ">
            <h1 style="color: #FFFFFF; margin: 0; font-size: 28px;">🔄 Migration Dashboard</h1>
            <p style="color: #FFFFFF; margin: 8px 0 0 0; opacity: 0.9;">Temporary utility for bulk-importing legacy projects from Google Drive</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    access_token, error = get_drive_access_token()
    
    if error:
        st.error(f"❌ Google Drive Connection Error: {error}")
        st.info("Please ensure Google Drive is connected via the Replit integration.")
        return
    
    st.success("✅ Google Drive connected (Shared Drive: Shared KB)")
    
    st.info(f"📁 Scanning folder ID: **{SIGN_PROJECTS_FOLDER_ID}**")
    
    with st.spinner("Scanning Shared Drive folders..."):
        project_folders, err = list_drive_folders(access_token, SIGN_PROJECTS_FOLDER_ID)
    
    if err:
        st.error(f"Error scanning folders: {err}")
        return
    
    existing_projects = get_existing_project_names()
    existing_names = {name.lower().strip() for name, _ in existing_projects}
    existing_links = {link for _, link in existing_projects if link}
    
    unlinked_folders = []
    for folder in project_folders:
        folder_name = folder["name"]
        folder_link = folder.get("webViewLink", "")
        
        if folder_name.startswith("_"):
            continue
        
        is_linked = (
            folder_name.lower().strip() in existing_names or
            folder_link in existing_links
        )
        
        if not is_linked:
            unlinked_folders.append(folder)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Drive Folders", len(project_folders))
    with col2:
        st.metric("Already Linked", len(project_folders) - len(unlinked_folders))
    with col3:
        st.metric("Unlinked (Ready to Import)", len(unlinked_folders))
    
    st.markdown("---")
    
    if not unlinked_folders:
        st.success("🎉 All Drive folders are already linked to projects!")
        return
    
    st.markdown(
        '<h3 style="color: #00A8E8; margin-bottom: 16px;">📂 Unlinked Drive Folders</h3>',
        unsafe_allow_html=True
    )
    
    select_all = st.checkbox("✅ Select All", key="select_all_migrate", value=False)
    st.markdown("---")
    
    selected_folders = []
    
    for folder in unlinked_folders:
        col1, col2 = st.columns([0.1, 0.9])
        with col1:
            default_val = select_all
            is_selected = st.checkbox("", key=f"migrate_{folder['id']}", label_visibility="collapsed", value=default_val)
        with col2:
            st.markdown(
                f'''
                <div style="
                    background: #1b263b;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 8px;
                    border-left: 4px solid {'#00A8E8' if is_selected else '#666'};
                ">
                    <span style="color: #FFFFFF; font-weight: 600;">{folder["name"]}</span>
                    <a href="{folder.get('webViewLink', '#')}" target="_blank" style="color: #00A8E8; margin-left: 12px; font-size: 12px;">Open in Drive ↗</a>
                </div>
                ''',
                unsafe_allow_html=True
            )
        
        if is_selected:
            selected_folders.append(folder)
    
    st.markdown("---")
    
    if selected_folders:
        st.info(f"**{len(selected_folders)}** folder(s) selected for import")
        
        if st.button("🚀 Import Selected as Projects", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            imported_count = 0
            errors = []
            
            for idx, folder in enumerate(selected_folders):
                status_text.text(f"Importing: {folder['name']}...")
                progress_bar.progress((idx + 1) / len(selected_folders))
                
                project_id, err = create_migrated_project(
                    folder["name"],
                    folder.get("webViewLink", ""),
                    folder["id"]
                )
                
                if err:
                    errors.append(f"{folder['name']}: {err}")
                else:
                    imported_count += 1
            
            progress_bar.progress(1.0)
            status_text.empty()
            
            if imported_count > 0:
                st.success(f"✅ Successfully imported {imported_count} project(s) with status 'MIGRATED'")
            
            if errors:
                st.error("Some imports failed:")
                for err in errors:
                    st.write(f"- {err}")
            
            st.rerun()
    else:
        st.warning("Select folders above to import them as projects")
    
    st.markdown("---")
    st.markdown(
        '''
        <div style="
            background: rgba(255, 107, 53, 0.1);
            border: 1px dashed #FF6B35;
            border-radius: 8px;
            padding: 16px;
            margin-top: 20px;
        ">
            <p style="color: #FF6B35; margin: 0; font-size: 13px;">
                ⚠️ <strong>Temporary Utility</strong>: Delete views/migration_util.py and remove the /migrate route from main.py when migration is complete.
            </p>
        </div>
        ''',
        unsafe_allow_html=True
    )


def delete_drive_file(access_token: str, file_id: str):
    """Delete a file from Shared Drive."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.delete(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"supportsAllDrives": "true"},
            timeout=10
        )
        return response.status_code in [200, 204], None
    except Exception as e:
        return False, f"Error deleting file: {str(e)}"


def download_drive_image(access_token: str, file_id: str) -> tuple:
    """Download image file content from Shared Drive. Returns (bytes, filename, mime_type, error)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        meta_response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"fields": "name,mimeType,size", "supportsAllDrives": "true"},
            timeout=10
        )
        meta = meta_response.json()
        filename = meta.get("name", "image.jpg")
        mime_type = meta.get("mimeType", "")
        file_size = int(meta.get("size", 0) or 0)
        
        if mime_type.startswith("application/vnd.google-apps.shortcut"):
            return None, None, None, "File is a shortcut, not a real file"
        
        if file_size == 0:
            return None, None, None, "File is empty (zero bytes)"
        
        content_response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=30
        )
        
        if content_response.status_code == 200:
            content = content_response.content
            
            if len(content) < 100:
                return None, None, None, f"File too small ({len(content)} bytes), likely corrupted"
            
            return content, filename, mime_type, None
        else:
            return None, None, None, f"Failed to download: {content_response.status_code}"
    except Exception as e:
        return None, None, None, f"Error downloading: {str(e)}"


def is_valid_image_data(file_data: bytes) -> bool:
    """Check if bytes represent a valid image that PIL can open."""
    if not file_data or len(file_data) < 100:
        return False
    
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file_data))
        img.verify()
        return True
    except Exception:
        return False


def save_drive_image_to_db(project_id: str, file_id: str, photo_type: str, drive_folder_id: str):
    """Download Drive image and save to project_photos with specified category."""
    from services.database_manager import save_project_photo
    
    access_token, error = get_drive_access_token()
    if error:
        return False, error
    
    file_data, filename, mime_type, err = download_drive_image(access_token, file_id)
    if err:
        return False, err
    
    if not file_data:
        return False, "No file data received"
    
    if mime_type and mime_type.startswith("application/pdf"):
        return False, "File is a PDF, not an image. Use PDF assignment instead."
    
    if not is_valid_image_data(file_data):
        return False, "File is not a valid image (corrupted or unsupported format)"
    
    try:
        save_project_photo(project_id, filename, file_data, photo_type)
        
        archive_folder_id, err = get_or_create_archive_folder(access_token, drive_folder_id)
        if not err:
            move_file_to_archive(access_token, file_id, drive_folder_id, archive_folder_id)
        
        return True, None
    except Exception as e:
        return False, f"Error saving to database: {str(e)}"


def archive_all_remaining_legacy(project_id: str, drive_folder_id: str) -> tuple:
    """Archive all remaining legacy images in the Drive folder."""
    access_token, error = get_drive_access_token()
    if error:
        return 0, error
    
    images, err = list_drive_images(access_token, drive_folder_id)
    if err:
        return 0, err
    
    if not images:
        return 0, "No images to archive"
    
    archive_folder_id, err = get_or_create_archive_folder(access_token, drive_folder_id)
    if err:
        return 0, err
    
    archived_count = 0
    for image in images:
        file_id = image.get("id")
        success, _ = move_file_to_archive(access_token, file_id, drive_folder_id, archive_folder_id)
        if success:
            archived_count += 1
    
    return archived_count, None


def render_legacy_thumbnails(project_id: str, drive_folder_id: str):
    """Render legacy Drive images with one-click category assignment and AI Smart-Sort."""
    if not drive_folder_id:
        return
    
    access_token, error = get_drive_access_token()
    if error:
        return
    
    images, err = list_drive_images(access_token, drive_folder_id)
    if err or not images:
        return
    
    ai_suggestions = st.session_state.get(f"ai_suggestions_{project_id}", {})
    
    st.markdown(
        f'''
        <div style="
            background: linear-gradient(145deg, #2d3a4a 0%, #1b263b 100%);
            border-radius: 12px;
            padding: 16px;
            margin: 16px 0;
            border: 1px solid #FF6B35;
        ">
            <h4 style="color: #FF6B35; margin: 0 0 8px 0; font-size: 16px;">📁 Legacy Drive Images ({len(images)})</h4>
            <p style="color: #888; font-size: 12px; margin: 0;">Click a category button to import and categorize each image</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    header_cols = st.columns([1, 1, 1])
    with header_cols[0]:
        if st.button("🤖 Run AI Smart-Sort", key=f"ai_sort_{project_id}", use_container_width=True, type="secondary"):
            from services.gemini_service import batch_analyze_images
            with st.spinner("Analyzing images with AI..."):
                suggestions = batch_analyze_images(images)
                st.session_state[f"ai_suggestions_{project_id}"] = suggestions
                st.success(f"AI analyzed {len(suggestions)} images!")
                st.rerun()
    
    with header_cols[1]:
        if st.button("📦 Archive All Remaining", key=f"archive_all_{project_id}", use_container_width=True, type="secondary"):
            with st.spinner("Archiving remaining images..."):
                count, err = archive_all_remaining_legacy(project_id, drive_folder_id)
                if err:
                    st.error(f"Error: {err}")
                else:
                    st.success(f"Archived {count} images!")
                    st.rerun()
    
    with header_cols[2]:
        if ai_suggestions:
            st.markdown(
                '<p style="color: #4CAF50; font-size: 12px; text-align: center; margin-top: 8px;">✅ AI suggestions active</p>',
                unsafe_allow_html=True
            )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/jpg", "image/gif", "image/webp"]
    
    for idx, image in enumerate(images[:12]):
        with cols[idx % 3]:
            thumbnail_url = image.get("thumbnailLink", "")
            file_id = image.get("id", "")
            file_name = image.get("name", "Image")
            mime_type = image.get("mimeType", "")
            
            suggested_cat = ai_suggestions.get(file_id, None)
            
            web_link = image.get("webViewLink", "")
            
            is_pdf = mime_type == "application/pdf"
            is_supported_image = mime_type in SUPPORTED_IMAGE_TYPES
            
            if is_pdf:
                st.markdown(
                    f'''
                    <div style="
                        background: #1b263b;
                        border-radius: 8px;
                        padding: 20px;
                        text-align: center;
                        border: 1px solid #333;
                    ">
                        <span style="color: #00A8E8; font-size: 24px;">📄</span>
                        <p style="color: #888; font-size: 11px; margin: 4px 0 0 0;">{file_name[:20]}...</p>
                        <p style="color: #00A8E8; font-size: 10px; margin: 4px 0 0 0;">PDF Document</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                if web_link:
                    st.link_button("View PDF in Drive", web_link, use_container_width=True)
                continue
            
            if not is_supported_image:
                st.markdown(
                    f'''
                    <div style="
                        background: #1b263b;
                        border-radius: 8px;
                        padding: 20px;
                        text-align: center;
                        border: 1px solid #333;
                    ">
                        <span style="color: #666; font-size: 24px;">📁</span>
                        <p style="color: #888; font-size: 11px; margin: 4px 0 0 0;">{file_name[:20]}...</p>
                        <p style="color: #ff9800; font-size: 10px; margin: 4px 0 0 0;">⚠️ File type not supported for preview</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                if web_link:
                    st.link_button("Open in Drive", web_link, use_container_width=True)
                continue
            
            try:
                if thumbnail_url:
                    st.image(thumbnail_url, caption=file_name[:30], use_container_width=True)
                else:
                    raise ValueError("No thumbnail available")
            except Exception:
                st.markdown(
                    f'''
                    <div style="
                        background: #1b263b;
                        border-radius: 8px;
                        padding: 20px;
                        text-align: center;
                        border: 1px solid #333;
                    ">
                        <span style="color: #666; font-size: 24px;">🖼️</span>
                        <p style="color: #888; font-size: 11px; margin: 4px 0 0 0;">{file_name[:20]}...</p>
                        <p style="color: #ff9800; font-size: 10px; margin: 4px 0 0 0;">⚠️ Preview not available for this file type</p>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                if web_link:
                    st.link_button("Open in Drive", web_link, use_container_width=True)
            
            cat_cols = st.columns(3)
            
            with cat_cols[0]:
                btn_type = "primary" if suggested_cat == "logo" else "secondary"
                label = "🎨 Logo" if suggested_cat != "logo" else "🎨 Logo ✓"
                if st.button(label, key=f"cat_logo_{project_id}_{file_id}", use_container_width=True, type=btn_type):
                    with st.spinner("Importing..."):
                        success, err = save_drive_image_to_db(project_id, file_id, "logo", drive_folder_id)
                        if success:
                            st.success("Added as Logo!")
                            if file_id in ai_suggestions:
                                del st.session_state[f"ai_suggestions_{project_id}"][file_id]
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")
            
            with cat_cols[1]:
                btn_type = "primary" if suggested_cat == "site" else "secondary"
                label = "🏗️ Site" if suggested_cat != "site" else "🏗️ Site ✓"
                if st.button(label, key=f"cat_site_{project_id}_{file_id}", use_container_width=True, type=btn_type):
                    with st.spinner("Importing..."):
                        success, err = save_drive_image_to_db(project_id, file_id, "site", drive_folder_id)
                        if success:
                            st.success("Added as Site Photo!")
                            if file_id in ai_suggestions:
                                del st.session_state[f"ai_suggestions_{project_id}"][file_id]
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")
            
            with cat_cols[2]:
                btn_type = "primary" if suggested_cat == "reference" else "secondary"
                label = "💡 Ref" if suggested_cat != "reference" else "💡 Ref ✓"
                if st.button(label, key=f"cat_ref_{project_id}_{file_id}", use_container_width=True, type=btn_type):
                    with st.spinner("Importing..."):
                        success, err = save_drive_image_to_db(project_id, file_id, "reference", drive_folder_id)
                        if success:
                            st.success("Added as Reference!")
                            if file_id in ai_suggestions:
                                del st.session_state[f"ai_suggestions_{project_id}"][file_id]
                            st.rerun()
                        else:
                            st.error(f"Failed: {err}")
            
            archive_del_cols = st.columns(2)
            with archive_del_cols[0]:
                if st.button("📦", key=f"arch_{project_id}_{file_id}", use_container_width=True, help="Archive"):
                    archive_folder_id, err = get_or_create_archive_folder(access_token, drive_folder_id)
                    if not err:
                        success, err = move_file_to_archive(access_token, file_id, drive_folder_id, archive_folder_id)
                        if success:
                            st.rerun()
            with archive_del_cols[1]:
                if st.button("🗑️", key=f"del_{project_id}_{file_id}", use_container_width=True, help="Delete"):
                    success, err = delete_drive_file(access_token, file_id)
                    if success:
                        st.rerun()
            
            st.markdown("<hr style='border: none; border-top: 1px solid #333; margin: 12px 0;'>", unsafe_allow_html=True)


def archive_drive_file(file_id: str, parent_folder_id: str):
    """Archive a file by moving it to _ARCHIVE subfolder."""
    access_token, error = get_drive_access_token()
    if error:
        return False, error
    
    archive_folder_id, err = get_or_create_archive_folder(access_token, parent_folder_id)
    if err:
        return False, err
    
    success, err = move_file_to_archive(access_token, file_id, parent_folder_id, archive_folder_id)
    return success, err


def get_pdf_slot_suggestion(filename: str) -> str:
    """Determine suggested slot based on filename keywords."""
    name_lower = filename.lower()
    
    proposal_keywords = ["proposal", "estimate", "quote", "price", "pricing", "bid"]
    design_keywords = ["design", "proof", "layout", "mockup", "mock-up", "artwork", "art"]
    
    for kw in proposal_keywords:
        if kw in name_lower:
            return "proposal"
    
    for kw in design_keywords:
        if kw in name_lower:
            return "design"
    
    return None


def assign_pdf_to_slot(project_id: str, file_id: str, filename: str, slot_type: str, drive_folder_id: str) -> tuple:
    """Assign a legacy PDF to a project slot (design or proposal)."""
    from services.database_manager import update_design_proof, update_proposal
    
    if slot_type == "design":
        success = update_design_proof(project_id, file_id, filename)
    elif slot_type == "proposal":
        success = update_proposal(project_id, file_id, filename)
    else:
        return False, "Invalid slot type"
    
    if success:
        access_token, error = get_drive_access_token()
        if not error:
            archive_folder_id, err = get_or_create_archive_folder(access_token, drive_folder_id)
            if not err:
                move_file_to_archive(access_token, file_id, drive_folder_id, archive_folder_id)
        return True, None
    else:
        return False, "Failed to update database"


def render_legacy_pdfs(project_id: str, drive_folder_id: str):
    """Render legacy PDFs with direct-to-slot assignment buttons."""
    if not drive_folder_id:
        return
    
    access_token, error = get_drive_access_token()
    if error:
        return
    
    pdfs, err = list_drive_pdfs(access_token, drive_folder_id)
    if err or not pdfs:
        return
    
    st.markdown(
        f'''
        <div style="
            background: linear-gradient(145deg, #2d3a4a 0%, #1b263b 100%);
            border-radius: 12px;
            padding: 16px;
            margin: 16px 0;
            border: 1px solid #9C27B0;
        ">
            <h4 style="color: #9C27B0; margin: 0 0 8px 0; font-size: 16px;">📄 Legacy PDFs ({len(pdfs)})</h4>
            <p style="color: #888; font-size: 12px; margin: 0;">Assign PDFs to Design Proof or Proposal slots</p>
        </div>
        ''',
        unsafe_allow_html=True
    )
    
    for pdf in pdfs[:10]:
        file_id = pdf.get("id", "")
        file_name = pdf.get("name", "Document.pdf")
        web_link = pdf.get("webViewLink", "")
        
        suggested_slot = get_pdf_slot_suggestion(file_name)
        
        st.markdown(
            f'''
            <div style="
                background: #1b263b;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                border: 1px solid #333;
                display: flex;
                align-items: center;
            ">
                <span style="font-size: 28px; margin-right: 12px;">📄</span>
                <div>
                    <p style="color: #E5E5E5; margin: 0; font-size: 14px; font-weight: 500;">{file_name[:40]}</p>
                    <p style="color: #666; margin: 2px 0 0 0; font-size: 11px;">PDF Document</p>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
        
        btn_cols = st.columns([1, 1, 1, 1])
        
        with btn_cols[0]:
            proposal_type = "primary" if suggested_slot == "proposal" else "secondary"
            proposal_label = "📄 Proposal ✓" if suggested_slot == "proposal" else "📄 Proposal"
            if st.button(proposal_label, key=f"pdf_proposal_{project_id}_{file_id}", use_container_width=True, type=proposal_type):
                with st.spinner("Assigning..."):
                    success, err = assign_pdf_to_slot(project_id, file_id, file_name, "proposal", drive_folder_id)
                    if success:
                        st.success("Assigned as Proposal!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
        
        with btn_cols[1]:
            design_type = "primary" if suggested_slot == "design" else "secondary"
            design_label = "🎨 Design ✓" if suggested_slot == "design" else "🎨 Design"
            if st.button(design_label, key=f"pdf_design_{project_id}_{file_id}", use_container_width=True, type=design_type):
                with st.spinner("Assigning..."):
                    success, err = assign_pdf_to_slot(project_id, file_id, file_name, "design", drive_folder_id)
                    if success:
                        st.success("Assigned as Design Proof!")
                        st.rerun()
                    else:
                        st.error(f"Failed: {err}")
        
        with btn_cols[2]:
            if web_link:
                st.link_button("👁️ View", web_link, use_container_width=True)
        
        with btn_cols[3]:
            if st.button("📦", key=f"pdf_arch_{project_id}_{file_id}", use_container_width=True, help="Archive"):
                archive_folder_id, err = get_or_create_archive_folder(access_token, drive_folder_id)
                if not err:
                    success, err = move_file_to_archive(access_token, file_id, drive_folder_id, archive_folder_id)
                    if success:
                        st.rerun()
