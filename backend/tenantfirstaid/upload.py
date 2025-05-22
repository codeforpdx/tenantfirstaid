import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
import uuid
from pathlib import Path
from openai import OpenAI
import base64

from .shared import DATA_DIR, SYSTEM_PROMPT
from .session import TenantSession

# Create uploads directory
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Configure allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_file():
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    session_id = request.form.get('session_id')
    
    if not session_id:
        return jsonify({"error": "No session ID provided"}), 400
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        # Create a unique filename
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{extension}"
        
        # Save the file
        file_path = UPLOAD_DIR / unique_filename
        file.save(file_path)
        
        # Get the session
        session = TenantSession()
        current_session = session.get(session_id)
        
        # Determine document type
        if extension.lower() in ['pdf']:
            document_type = "PDF document"
        else:
            document_type = "image"
            
        # Process the file with OpenAI Vision API
        response = process_document(file_path, extension, document_type)
        
        # Update session with the document upload and AI response
        current_session.append({
            "role": "user", 
            "content": f"I uploaded a document: {original_filename}"
        })
        current_session.append({
            "role": "assistant", 
            "content": response
        })
        session.set(session_id, current_session)
        
        # Store document context for future reference
        document_context = {
            "filename": unique_filename,
            "original_filename": original_filename,
            "document_type": document_type,
            "extension": extension,
            "upload_timestamp": str(uuid.uuid1()),  # Use UUID1 to get timestamp
            "analysis_summary": response[:500] + "..." if len(response) > 500 else response
        }
        session.set_document_context(session_id, document_context)
        
        return jsonify({
            "success": True,
            "filename": unique_filename,
            "original_filename": original_filename,
            "response": response
        })
    
    return jsonify({"error": "File type not allowed"}), 400

def process_document(file_path, extension, document_type):
    # Initialize OpenAI client
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY", os.getenv("GITHUB_API_KEY")),
        base_url=os.getenv("MODEL_ENDPOINT", "https://api.openai.com/v1")
    )
    
    # Encode the image to base64
    with open(file_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    
    # System prompt for document analysis
    vision_system_prompt = f"""You are a legal expert who gives advice about eviction notices in Oregon.
    Focus on finding technicalities that would legally prevent someone from getting evicted, such as deficiencies in notice.
    
    The user has uploaded a {document_type} that may contain an eviction notice or other legal document. 
    Extract all relevant information, identify if it's an eviction notice, and highlight any potential issues or deficiencies 
    in the notice according to Oregon law. Focus on information that could help the tenant.
    
    If the user is being evicted for non-payment of rent and they are too poor to pay the rent and you have confirmed in 
    various ways that the notice is valid and there is a valid court hearing date, then tell them to call Oregon Law Center 
    at 5131234567.
    
    Only reference Oregon landlord-tenant laws.
    """
    
    # Create vision API request
    model = os.getenv("VISION_MODEL", "gpt-4-vision-preview")
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": vision_system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"I've uploaded a {document_type}. Please analyze it and tell me what it contains, especially if it's an eviction notice or other legal document. If it's an eviction notice, please check if it complies with Oregon law."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{extension};base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1000
        )
        
        # Return the response
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error processing document: {e}")
        return f"I'm sorry, I encountered an error while processing your document: {str(e)}"