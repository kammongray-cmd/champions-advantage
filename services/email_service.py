import smtplib
import os
import requests
import mimetypes
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email import encoders

# TEST MODE: Redirect all emails to test account
TEST_MODE = True
TEST_EMAIL_RECIPIENT = "kammongray@gmail.com"

# Max file size for email attachments (10MB)
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024


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


def set_drive_file_public(file_id: str) -> tuple:
    """
    Set a Google Drive file to 'Anyone with the link can view' permission.
    Returns (success: bool, message: str).
    """
    if not file_id:
        return False, "No file ID provided"
    
    access_token, err = get_drive_access_token()
    if err:
        return False, f"Drive auth error: {err}"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # Create 'anyone with link' permission
        permission_data = {
            "role": "reader",
            "type": "anyone"
        }
        
        response = requests.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            headers=headers,
            json=permission_data,
            params={"supportsAllDrives": "true"},
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return True, "File permissions updated to 'Anyone with link can view'"
        elif response.status_code == 403:
            return False, "Permission denied - cannot modify file sharing settings"
        else:
            return False, f"Failed to update permissions: HTTP {response.status_code}"
    except Exception as e:
        return False, f"Permission update error: {str(e)}"


def download_drive_file(file_id: str) -> tuple:
    """
    Robust file download from Google Drive using get_media equivalent.
    Returns (raw_bytes: bytes, filename: str, mime_type: str, error: str).
    If file exceeds MAX_ATTACHMENT_SIZE, returns (None, None, None, "FILE_TOO_LARGE").
    """
    if not file_id:
        return None, None, None, "No file ID provided"
    
    access_token, err = get_drive_access_token()
    if err:
        print(f"[DRIVE ERROR] Auth failed: {err}")
        return None, None, None, f"Drive auth error: {err}"
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Get file metadata first
        print(f"[DRIVE] Fetching metadata for file: {file_id}")
        meta_response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"fields": "name,mimeType,size", "supportsAllDrives": "true"},
            timeout=10
        )
        
        if meta_response.status_code != 200:
            print(f"[DRIVE ERROR] Metadata failed: HTTP {meta_response.status_code} - {meta_response.text}")
            return None, None, None, f"Metadata fetch failed: HTTP {meta_response.status_code}"
        
        meta = meta_response.json()
        filename = meta.get("name", "attachment")
        mime_type = meta.get("mimeType", "application/octet-stream")
        file_size = int(meta.get("size", 0) or 0)
        
        print(f"[DRIVE] File: {filename}, Type: {mime_type}, Size: {file_size} bytes")
        
        # Check if Google Docs format (needs export)
        if mime_type.startswith("application/vnd.google-apps"):
            print(f"[DRIVE ERROR] Cannot download Google Docs format: {mime_type}")
            return None, None, None, "Google Docs files cannot be directly downloaded"
        
        # Check file size limit
        if file_size > MAX_ATTACHMENT_SIZE:
            print(f"[DRIVE ERROR] File too large: {file_size} > {MAX_ATTACHMENT_SIZE}")
            return None, None, None, "FILE_TOO_LARGE"
        
        # Download raw bytes using alt=media (equivalent to service.files().get_media())
        print(f"[DRIVE] Downloading file content...")
        content_response = requests.get(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers=headers,
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=60
        )
        
        if content_response.status_code != 200:
            print(f"[DRIVE ERROR] Download failed: HTTP {content_response.status_code} - {content_response.text}")
            return None, None, None, f"Download failed: HTTP {content_response.status_code}"
        
        # Return raw bytes (not BytesIO) for proper MIME encoding
        raw_bytes = content_response.content
        print(f"[DRIVE] Downloaded {len(raw_bytes)} bytes successfully")
        
        return raw_bytes, filename, mime_type, None
        
    except Exception as e:
        print(f"[DRIVE ERROR] Exception during download: {str(e)}")
        return None, None, None, f"Download error: {str(e)}"


def extract_file_id_from_link(link: str) -> str:
    """Extract Google Drive file ID from various URL formats."""
    import re
    
    if not link:
        return None
    
    patterns = [
        r'/file/d/([a-zA-Z0-9_-]+)',
        r'id=([a-zA-Z0-9_-]+)',
        r'/d/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, link)
        if match:
            return match.group(1)
    
    return None


def is_test_mode() -> bool:
    """Check if email test mode is active."""
    return TEST_MODE


def get_smtp_config():
    """Get SMTP configuration from environment/secrets."""
    return {
        "server": os.environ.get("SMTP_SERVER", ""),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "email": os.environ.get("SMTP_EMAIL", ""),
        "password": os.environ.get("SMTP_PASSWORD", "")
    }


def send_email(to_email: str, subject: str, body: str, reply_to: str = None) -> tuple[bool, str]:
    """
    Send an email via SMTP from kam@kbsignconstruction.com.
    Returns (success: bool, message: str)
    """
    config = get_smtp_config()
    
    if not all([config["server"], config["port"], config["email"], config["password"]]):
        return False, "SMTP configuration incomplete. Check secrets."
    
    sender_email = config["email"]
    
    # TEST MODE: Override recipient and subject
    original_recipient = to_email
    if TEST_MODE:
        to_email = TEST_EMAIL_RECIPIENT
        subject = f"[TEST] {subject}"
        body = f"[Original recipient: {original_recipient}]\n\n{body}"
    
    try:
        msg = MIMEMultipart()
        msg["From"] = f"KB Signs <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        if reply_to:
            msg["Reply-To"] = reply_to
        
        msg.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(config["server"], config["port"]) as server:
            server.starttls()
            server.login(config["email"], config["password"])
            server.send_message(msg)
        
        return True, f"Email sent to {to_email}"
    
    except smtplib.SMTPAuthenticationError as e:
        return False, f"SMTP Authentication failed: {e.smtp_code} - {e.smtp_error}"
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP Connection failed: {e.smtp_code} - {e.smtp_error}"
    except smtplib.SMTPException as e:
        return False, f"SMTP Error: {str(e)}"
    except Exception as e:
        return False, f"Email error: {str(e)}"


def send_email_with_attachments(to_email: str, subject: str, body: str, 
                                 attachments: list = None, reply_to: str = None) -> tuple[bool, str]:
    """
    Send an email with file attachments using proper Base64 encoding.
    
    CRITICAL: Uses MIMEBase + encode_base64 for ALL attachments to prevent
    the 'disappearing attachment' issue in email clients.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        attachments: List of dicts with {data: bytes, filename: str}
                     (data can be bytes or BytesIO)
        reply_to: Optional reply-to address
    
    Returns (success: bool, message: str)
    """
    config = get_smtp_config()
    
    if not all([config["server"], config["port"], config["email"], config["password"]]):
        return False, "SMTP configuration incomplete. Check secrets."
    
    sender_email = config["email"]
    
    original_recipient = to_email
    if TEST_MODE:
        to_email = TEST_EMAIL_RECIPIENT
        subject = f"[TEST] {subject}"
        body = f"[Original recipient: {original_recipient}]\n\n{body}"
    
    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"KB Signs <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        if reply_to:
            msg["Reply-To"] = reply_to
        
        msg.attach(MIMEText(body, "plain"))
        
        attached_files = []
        if attachments:
            for attachment in attachments:
                try:
                    # Get file data - accept both bytes and BytesIO
                    file_data = attachment.get("data") or attachment.get("buffer")
                    filename = attachment.get("filename", "attachment")
                    
                    if file_data is None:
                        print(f"[EMAIL ERROR] No data for attachment: {filename}")
                        continue
                    
                    # Convert BytesIO to bytes if needed
                    if hasattr(file_data, 'read'):
                        file_data.seek(0)
                        file_data = file_data.read()
                    
                    if not file_data or len(file_data) == 0:
                        print(f"[EMAIL ERROR] Empty data for attachment: {filename}")
                        continue
                    
                    print(f"[EMAIL] Attaching file: {filename} ({len(file_data)} bytes)")
                    
                    # CRITICAL: Use MIMEBase with application/octet-stream for ALL files
                    # This ensures consistent Base64 encoding across all email clients
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file_data)
                    
                    # CRITICAL: encode_base64 makes the attachment readable by all clients
                    encoders.encode_base64(part)
                    
                    # Add Content-Disposition header with filename
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename="{filename}"'
                    )
                    
                    msg.attach(part)
                    attached_files.append(filename)
                    print(f"[EMAIL] Successfully attached: {filename}")
                    
                except Exception as attach_err:
                    print(f"[EMAIL ERROR] Could not attach file {filename}: {attach_err}")
        
        print(f"[EMAIL] Sending email to {to_email} with {len(attached_files)} attachments...")
        
        with smtplib.SMTP(config["server"], config["port"]) as server:
            server.starttls()
            server.login(config["email"], config["password"])
            server.send_message(msg)
        
        attach_count = len(attached_files)
        print(f"[EMAIL] SUCCESS: Email sent with {attach_count} attachment(s)")
        return True, f"Email sent to {to_email} with {attach_count} attachment(s): {', '.join(attached_files)}"
    
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL ERROR] SMTP Auth failed: {e}")
        return False, f"SMTP Authentication failed: {e.smtp_code} - {e.smtp_error}"
    except smtplib.SMTPConnectError as e:
        print(f"[EMAIL ERROR] SMTP Connect failed: {e}")
        return False, f"SMTP Connection failed: {e.smtp_code} - {e.smtp_error}"
    except smtplib.SMTPException as e:
        print(f"[EMAIL ERROR] SMTP Error: {e}")
        return False, f"SMTP Error: {str(e)}"
    except Exception as e:
        print(f"[EMAIL ERROR] Exception: {e}")
        return False, f"Email error: {str(e)}"


def send_test_email() -> tuple[bool, str]:
    """Send a test email to verify SMTP configuration."""
    config = get_smtp_config()
    return send_email(
        to_email=config["email"],
        subject="Grayco Lite V3 - System Test",
        body="This is a test email from Grayco Lite V3.\n\nIf you received this, your SMTP configuration is working correctly.\n\n- Grayco Lite V3 System"
    )


def send_design_request(to_email: str, client_name: str, notes: str, drive_link: str, site_photo_file_ids: list = None) -> tuple[bool, str, list]:
    """
    Send design request email to Matt with site photo attachments if available.
    Returns (success: bool, message: str, attached_filenames: list).
    """
    subject = f"Design Request: {client_name}"
    
    attachments = []
    attached_filenames = []
    attachment_note = ""
    
    # Try to attach site photos
    if site_photo_file_ids:
        for file_id in site_photo_file_ids[:3]:  # Limit to 3 photos
            # Set public permission before download
            set_drive_file_public(file_id)
            
            file_buffer, filename, mime_type, err = download_drive_file(file_id)
            if file_buffer and not err:
                attachments.append({
                    "buffer": file_buffer,
                    "filename": filename,
                    "mime_type": mime_type
                })
                attached_filenames.append(filename)
            elif err == "FILE_TOO_LARGE":
                pass  # Skip large files, use Drive link
        if attached_filenames:
            attachment_note = f"\n\n({len(attached_filenames)} site photo(s) attached)"
    
    body = f"""Hi Matt,

Please create a design for {client_name}.

PROJECT NOTES:
{notes if notes else "No additional notes provided."}

GOOGLE DRIVE FOLDER:
{drive_link if drive_link else "No Drive folder linked yet."}
{attachment_note}

Thanks,
KB Signs Team
"""
    
    if attachments:
        success, message = send_email_with_attachments(to_email, subject, body, attachments)
        return success, message, attached_filenames
    else:
        success, message = send_email(to_email, subject, body)
        return success, message, []


def send_pricing_request(to_email: str, client_name: str, drive_link: str, design_proof_file_id: str = None) -> tuple[bool, str, list]:
    """
    Send pricing request email to Bruno with design attachment if available.
    Returns (success: bool, message: str, attached_filenames: list).
    """
    subject = f"Pricing Request: {client_name}"
    
    attachments = []
    attached_filenames = []
    attachment_note = ""
    
    # Try to attach the design proof
    if design_proof_file_id:
        # Set public permission before download
        set_drive_file_public(design_proof_file_id)
        
        file_buffer, filename, mime_type, err = download_drive_file(design_proof_file_id)
        if file_buffer and not err:
            attachments.append({
                "buffer": file_buffer,
                "filename": filename,
                "mime_type": mime_type
            })
            attached_filenames.append(filename)
            attachment_note = f"\n\n(Design proof attached: {filename})"
        elif err == "FILE_TOO_LARGE":
            attachment_note = f"\n\nNote: Design file is too large to attach. Please find it in the Google Drive folder."
    
    body = f"""Hi Bruno,

Please price the {"attached" if attachments else "latest"} design for {client_name}.

GOOGLE DRIVE FOLDER (Design files here):
{drive_link if drive_link else "No Drive folder linked yet."}
{attachment_note}

Thanks,
KB Signs Team
"""
    
    if attachments:
        success, message = send_email_with_attachments(to_email, subject, body, attachments)
        return success, message, attached_filenames
    else:
        success, message = send_email(to_email, subject, body)
        return success, message, []


def send_customer_proposal(to_email: str, client_name: str, proposal_link: str, drive_link: str, proposal_file_id: str = None) -> tuple[bool, str, list]:
    """
    Send proposal email to customer with attachment if possible.
    Returns (success: bool, message: str, attached_filenames: list).
    """
    config = get_smtp_config()
    subject = f"Your Sign Proposal from KB Signs - {client_name}"
    
    attachments = []
    attached_filenames = []
    attachment_note = ""
    
    # Try to download and attach the proposal PDF
    if proposal_file_id:
        # Set public permission FIRST so link works even if attachment fails
        set_drive_file_public(proposal_file_id)
        
        file_buffer, filename, mime_type, err = download_drive_file(proposal_file_id)
        if file_buffer and not err:
            attachments.append({
                "buffer": file_buffer,
                "filename": filename,
                "mime_type": mime_type
            })
            attached_filenames.append(filename)
            attachment_note = f"\n\n(Proposal PDF attached: {filename})"
        elif err == "FILE_TOO_LARGE":
            attachment_note = f"\n\nNote: Proposal file is too large to attach. Please view it here:\n{proposal_link}"
    
    body = f"""Hello,

Thank you for your interest in KB Signs!

Please find your proposal {"attached below" if attachments else "at the link below"}:
{proposal_link if proposal_link and not attachments else ""}
{attachment_note}

PROJECT FILES:
{drive_link if drive_link else ""}

If you have any questions, please don't hesitate to reach out.

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com
"""
    
    if attachments:
        success, message = send_email_with_attachments(to_email, subject, body, attachments, reply_to=config["email"])
        return success, message, attached_filenames
    else:
        success, message = send_email(to_email, subject, body, reply_to=config["email"])
        return success, message, []


def send_deposit_invoice_request(to_email: str, client_name: str, drive_link: str) -> tuple[bool, str]:
    """Send request for deposit invoice to Bruno."""
    subject = f"Deposit Invoice Needed: {client_name}"
    
    body = f"""Hi Bruno,

Please create a deposit invoice for the {client_name} project.

The proposal has been approved and we need a deposit invoice to send to the customer.

GOOGLE DRIVE FOLDER:
{drive_link if drive_link else "No Drive folder linked yet."}

Thanks,
KB Signs Team
"""
    return send_email(to_email, subject, body)


def send_deposit_invoice_to_customer(to_email: str, client_name: str, invoice_link: str = None, drive_link: str = None) -> tuple[bool, str]:
    """Send deposit invoice to customer."""
    config = get_smtp_config()
    subject = f"Deposit Invoice - {client_name} Sign Project"
    
    body = f"""Hello,

Thank you for choosing KB Signs for your project!

Please find your deposit invoice attached. Once payment is received, we will begin production on your sign.

{f"View Invoice: {invoice_link}" if invoice_link else "Your invoice is attached to this email."}

{f"PROJECT FILES: {drive_link}" if drive_link else ""}

If you have any questions about the invoice or payment, please don't hesitate to reach out.

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com
"""
    return send_email(to_email, subject, body, reply_to=config["email"])


def send_3day_prep_email(to_email: str, client_name: str, install_date: str, balance_due: float = 0) -> tuple[bool, str]:
    """Send 3-day installation prep email to customer."""
    config = get_smtp_config()
    subject = f"Your Sign Installation in 3 Days - {client_name}"
    
    balance_section = ""
    if balance_due > 0:
        balance_section = f"""
FINAL PAYMENT REMINDER:
Your remaining balance of ${balance_due:,.2f} is due before installation. Please ensure payment is completed to avoid any delays.
"""
    
    body = f"""Hello,

Your sign installation is scheduled for {install_date}! Here's what you need to know:

WHAT TO EXPECT DURING INSTALLATION:
- Our team will arrive between 8:00 AM - 9:00 AM
- Installation typically takes 2-4 hours depending on sign complexity
- We'll handle all mounting, wiring, and final positioning
- A final walkthrough will be conducted before we leave

SITE ACCESS REQUIREMENTS:
- Please ensure the installation area is clear and accessible
- If gated, please provide access codes or arrange for someone to let us in
- Electrical access may be needed for illuminated signs
- Parking space for our installation vehicle
{balance_section}
If you have any questions or need to reschedule, please contact us immediately.

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com
"""
    return send_email(to_email, subject, body, reply_to=config["email"])


def send_final_invoice_request(to_email: str, client_name: str, balance_due: float, drive_link: str = None) -> tuple[bool, str]:
    """Request final invoice from Bruno."""
    config = get_smtp_config()
    subject = f"Final Invoice Needed - {client_name}"
    
    body = f"""Hey Bruno,

We need a final invoice created for the {client_name} project.

REMAINING BALANCE: ${balance_due:,.2f}

{f"PROJECT FILES: {drive_link}" if drive_link else ""}

Please create and upload the final invoice so we can send it to the customer before installation.

Thanks,
Kam
"""
    return send_email(to_email, subject, body, reply_to=config["email"])


def send_night_before_confirmation(to_email: str, client_name: str, install_date: str) -> tuple[bool, str]:
    """Send night-before installation confirmation to customer."""
    config = get_smtp_config()
    subject = f"Tomorrow's Installation - {client_name}"
    
    body = f"""Hello,

This is a friendly reminder that your sign installation is scheduled for tomorrow, {install_date}.

ARRIVAL WINDOW: 8:00 AM - 9:00 AM

Our team will give you a call when they're on the way. Please ensure the installation area is accessible.

If you have any last-minute questions, feel free to reach out.

See you tomorrow!

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com
"""
    return send_email(to_email, subject, body, reply_to=config["email"])


def send_commission_report_email(subject: str, body: str) -> bool:
    """Send commission report email to Bruno (redirected to test email in pilot mode).
    
    Args:
        subject: Email subject (e.g., "Commission Report - January 2026 1st - 15th")
        body: Full report body text
    
    Returns:
        bool: True if sent successfully
    """
    bruno_email = "kammongray@gmail.com"
    
    success, message = send_email(bruno_email, subject, body)
    return success
