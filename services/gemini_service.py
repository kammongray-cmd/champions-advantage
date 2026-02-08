import os
import json
import google.generativeai as genai


def get_gemini_client():
    """Initialize and return Gemini client for stable v1 API."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')


def extract_lead_info(raw_text: str) -> dict:
    """
    Use Gemini to extract Name, Phone, and Notes from raw text.
    Returns dict with 'name', 'phone', 'email', 'notes' keys.
    """
    model = get_gemini_client()
    if not model:
        return {"name": "", "phone": "", "email": "", "site_address": "", "notes": raw_text, "error": "Google API key not configured"}
    
    prompt = f"""Extract contact information from the following text. Return ONLY a valid JSON object with these exact keys:
- "name": the person's or company's name (string)
- "phone": phone number if found - prioritize extracting this for click-to-dial (string)
- "email": email address if found - prioritize extracting this for contact (string)
- "site_address": physical address or location for the sign installation if mentioned (string)
- "notes": any other relevant information like project details or requirements NOT including address/phone/email (string)

IMPORTANT: If you are unsure about a field, leave it blank rather than guessing. However, prioritize extracting phone and email even if partial.

If a field is not found, use an empty string.

Text to analyze:
{raw_text}

Return ONLY the JSON object, no markdown formatting or explanation."""

    try:
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1])
        
        data = json.loads(result_text)
        return {
            "name": data.get("name", ""),
            "phone": data.get("phone", ""),
            "email": data.get("email", ""),
            "site_address": data.get("site_address", ""),
            "notes": data.get("notes", ""),
            "error": None
        }
    except json.JSONDecodeError as e:
        return {"name": "", "phone": "", "email": "", "site_address": "", "notes": raw_text, "error": f"Failed to parse AI response: {e}"}
    except Exception as e:
        return {"name": "", "phone": "", "email": "", "site_address": "", "notes": raw_text, "error": f"AI extraction error: {e}"}


def draft_design_email(client_name: str, notes: str, drive_link: str, photo_summary: str = None) -> str:
    """Use Gemini to draft a design request email with photo summary."""
    model = get_gemini_client()
    
    photo_info = photo_summary if photo_summary else "No photos uploaded yet."
    
    if not model:
        return f"""Hi Matt,

Please create a design for {client_name}.

PROJECT NOTES:
{notes if notes else "No additional notes provided."}

UPLOADED PHOTOS:
{photo_info}

GOOGLE DRIVE FOLDER:
{drive_link if drive_link else "No Drive folder linked yet."}

Thanks,
KB Signs Team"""

    prompt = f"""Write a professional but friendly email requesting a sign design. Keep it concise (under 150 words).

Client: {client_name}
Project Notes: {notes if notes else "No specific notes"}
Uploaded Photos: {photo_info}
Google Drive Link: {drive_link if drive_link else "Not available"}

The email should:
- Be addressed to Matt (the designer)
- Reference the client name and project notes
- Mention the uploaded photos (site photos, markups, logos) if available
- Include the Google Drive link if available
- Be signed as "KB Signs Team"

Return ONLY the email body text, no subject line."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return f"""Hi Matt,

Please create a design for {client_name}.

PROJECT NOTES:
{notes if notes else "No additional notes provided."}

UPLOADED PHOTOS:
{photo_info}

GOOGLE DRIVE FOLDER:
{drive_link if drive_link else "No Drive folder linked yet."}

Thanks,
KB Signs Team"""


def draft_pricing_email(client_name: str, drive_link: str) -> str:
    """Use Gemini to draft a pricing request email."""
    model = get_gemini_client()
    if not model:
        return f"""Hi Bruno,

Please price the attached design for {client_name}.

GOOGLE DRIVE FOLDER (Design files here):
{drive_link if drive_link else "No Drive folder linked yet."}

Thanks,
KB Signs Team"""

    prompt = f"""Write a professional but friendly email requesting pricing for a sign project. Keep it concise (under 100 words).

Client: {client_name}
Google Drive Link: {drive_link if drive_link else "Not available"}

The email should:
- Be addressed to Bruno (the pricing specialist)
- Reference that the design is ready for pricing
- Include the Google Drive link for design files
- Be signed as "KB Signs Team"

Return ONLY the email body text, no subject line."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return f"""Hi Bruno,

Please price the attached design for {client_name}.

GOOGLE DRIVE FOLDER (Design files here):
{drive_link if drive_link else "No Drive folder linked yet."}

Thanks,
KB Signs Team"""


def draft_proposal_email(client_name: str, drive_link: str) -> str:
    """Use Gemini to draft a customer proposal email."""
    model = get_gemini_client()
    if not model:
        return f"""Hello,

Thank you for your interest in KB Signs!

Please find your proposal attached or view it in our shared folder:
{drive_link if drive_link else "Proposal will be shared separately."}

If you have any questions, please don't hesitate to reach out.

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com"""

    prompt = f"""Write a professional and warm email to send a sign proposal to a customer. Keep it concise (under 120 words).

Client: {client_name}
Proposal/Files Link: {drive_link if drive_link else "Will be shared separately"}

The email should:
- Thank them for their interest
- Reference where to find the proposal
- Invite questions
- Be signed by Kam from KB Sign Construction

Return ONLY the email body text, no subject line."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return f"""Hello,

Thank you for your interest in KB Signs!

Please find your proposal attached or view it in our shared folder:
{drive_link if drive_link else "Proposal will be shared separately."}

If you have any questions, please don't hesitate to reach out.

Best regards,
Kam
KB Sign Construction
kam@kbsignconstruction.com"""


def get_vision_model():
    """Initialize and return Gemini 2.5 Flash model for vision tasks."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')


def scan_invoice_for_amounts(pdf_bytes: bytes = None, image_bytes: bytes = None) -> dict:
    """
    Scan an invoice PDF or image to extract Total Project Amount and Deposit Due.
    Uses Gemini 1.5 Flash Vision for image/PDF analysis.
    Returns dict with 'total_value', 'deposit_amount', 'error'.
    """
    vision_model = get_vision_model()
    if not vision_model:
        return {"total_value": 0.0, "deposit_amount": 0.0, "error": "Google API key not configured"}
    
    try:
        import PIL.Image
        import io
        
        if image_bytes:
            pil_image = PIL.Image.open(io.BytesIO(image_bytes))
        elif pdf_bytes:
            try:
                import fitz
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page = pdf_doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                pil_image = PIL.Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                pdf_doc.close()
            except ImportError:
                return {"total_value": 0.0, "deposit_amount": 0.0, "error": "PyMuPDF not installed for PDF scanning"}
        else:
            return {"total_value": 0.0, "deposit_amount": 0.0, "error": "No image or PDF provided"}
        
        prompt = """Analyze this invoice/quote document and extract the financial amounts.

Look for:
1. TOTAL PROJECT AMOUNT / Grand Total / Total Due / Total Price - the full project cost
2. DEPOSIT AMOUNT / Advance Payment / Half Down / Down Payment / Deposit Due

Return ONLY a JSON object with these exact keys:
- "total_value": the total project amount as a number (no currency symbols)
- "deposit_amount": the deposit/advance payment amount as a number
- "notes": brief description of what you found

If deposit amount is not specified, calculate 50% of total_value.
If you cannot find amounts, return 0 for both.

Return ONLY the JSON object, no markdown."""

        result = vision_model.generate_content([prompt, pil_image])
        result_text = result.text.strip()
        
        if result_text.startswith("```"):
            lines = result_text.split("\n")
            result_text = "\n".join(lines[1:-1])
        
        data = json.loads(result_text)
        total = float(data.get("total_value", 0))
        deposit = float(data.get("deposit_amount", 0))
        
        if deposit == 0 and total > 0:
            deposit = total * 0.5
        
        return {
            "total_value": total,
            "deposit_amount": deposit,
            "notes": data.get("notes", ""),
            "error": None
        }
        
    except json.JSONDecodeError as e:
        return {"total_value": 0.0, "deposit_amount": 0.0, "error": f"Failed to parse AI response: {e}"}
    except Exception as e:
        return {"total_value": 0.0, "deposit_amount": 0.0, "error": f"Invoice scan error: {e}"}


def batch_analyze_images(images: list) -> dict:
    """
    Analyze images using Gemini 1.5 Flash vision to suggest categories.
    Downloads thumbnail images and sends them to Gemini for visual analysis.
    Returns dict mapping file_id to category suggestion.
    """
    import requests
    
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return {}
    
    vision_model = get_vision_model()
    if not vision_model:
        return {}
    
    suggestions = {}
    
    for img in images[:12]:
        file_id = img.get("id", "")
        file_name = img.get("name", "unknown")
        thumbnail_url = img.get("thumbnailLink", "")
        
        if not thumbnail_url or not file_id:
            continue
        
        try:
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code != 200:
                continue
            
            image_bytes = response.content
            
            import PIL.Image
            import io
            pil_image = PIL.Image.open(io.BytesIO(image_bytes))
            
            prompt = f"""Analyze this image and determine its category for a sign shop project.

Filename hint: {file_name}

Categories:
- "logo": Business logos, brand assets, company emblems, text-based designs, vector graphics
- "site": Photos of buildings, walls, storefronts, construction sites, physical sign locations, facades
- "reference": Inspiration photos, example signs, design ideas, competitor signs, reference imagery

Look at the ACTUAL IMAGE CONTENT to determine the category:
- If it shows a logo, brand mark, or text-based design → "logo"
- If it shows a building, wall, storefront, or physical location → "site"  
- If it shows an example sign, design inspiration, or reference → "reference"

Return ONLY a JSON object: {{"category": "logo" or "site" or "reference"}}"""
            
            result = vision_model.generate_content([prompt, pil_image])
            result_text = result.text.strip()
            
            if result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1])
            
            data = json.loads(result_text)
            category = data.get("category", "site")
            if category in ["logo", "site", "reference"]:
                suggestions[file_id] = category
                
        except Exception:
            continue
    
    return suggestions
