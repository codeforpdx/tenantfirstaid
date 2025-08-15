import os
import uuid
from pathlib import Path
from flask import request, stream_with_context, Response, session, abort
from flask.views import View
from werkzeug.utils import secure_filename
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.oauth2 import service_account

# Constants
UPLOAD_FOLDER = Path(os.getenv("DATA_DIR", "data")) / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Create uploads directory if it doesn't exist
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

DOCUMENT_ANALYSIS_PROMPT = """
You are a legal expert analyzing a document that may be related to housing law in Oregon. 

Please analyze this document thoroughly and provide:

1. **Document Type**: What type of document this appears to be (e.g., eviction notice, lease agreement, court summons, etc.)

2. **Key Information**: Extract and summarize the most important details from the document, such as:
   - Property address
   - Tenant/landlord names
   - Important dates (notice dates, compliance deadlines, court dates)
   - Amounts owed (if any)
   - Reason for action (if applicable)

3. **Legal Analysis**: Look for any potential legal issues or deficiencies in the document, especially:
   - Missing required information
   - Incorrect formatting or language
   - Improper service methods mentioned
   - Violations of Oregon housing law requirements
   - Procedural errors

4. **Recommendations**: Based on your analysis, provide specific advice on:
   - What the tenant should do next
   - Any deadlines they need to be aware of
   - Potential defenses or challenges to consider
   - Whether they should seek legal assistance

5. **Citations**: Reference relevant Oregon housing laws (ORS statutes) where applicable, and mention if this should comply with any local city ordinances (Portland, Eugene, etc.)

Focus particularly on finding any technical deficiencies that might invalidate the notice or document. Be thorough but concise in your analysis.

If you cannot clearly read the document or if it's not related to housing law, please explain what you can see and suggest the user provide a clearer image or confirm the document type.
"""


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


class DocumentAnalyzer:
    def __init__(self):
        creds = service_account.Credentials.from_service_account_file(
            os.getenv(
                "GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_FILE", "google-service-account.json"
            )
        )
        vertexai.init(
            project="tenantfirstaid",
            location="us-west1",
            credentials=creds,
        )
        self.model = GenerativeModel(
            model_name=os.getenv("MODEL_NAME", "gemini-2.5-pro"),
            system_instruction=DOCUMENT_ANALYSIS_PROMPT,
        )

    def analyze_document(self, file_path: str, stream: bool = False):
        """Analyze a document using Google Gemini Vision API."""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read the file
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        # Determine the MIME type based on file extension
        file_extension = file_path_obj.suffix.lower()
        mime_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".pdf": "application/pdf",
        }
        mime_type = mime_type_map.get(file_extension, "application/octet-stream")
        
        # Create the part for the multimodal input
        file_part = Part.from_data(file_data, mime_type=mime_type)
        
        # Generate content with the document
        response = self.model.generate_content([file_part], stream=stream)
        
        return response


class UploadView(View):
    def __init__(self, tenant_session):
        self.tenant_session = tenant_session
        self.analyzer = DocumentAnalyzer()

    def dispatch_request(self, *args, **kwargs) -> Response:
        # Check if user has a valid session
        if not session.get("site_user"):
            abort(403, "Unauthorized: session missing")

        # Check if file is in request
        if "file" not in request.files:
            abort(400, "No file uploaded")

        file = request.files["file"]
        if file.filename == "":
            abort(400, "No file selected")

        # Validate file
        if not file or not allowed_file(file.filename):
            abort(400, "Invalid file type. Please upload PNG, JPG, JPEG, or PDF files.")

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset file pointer
        
        if file_size > MAX_FILE_SIZE:
            abort(400, "File size exceeds 10MB limit")

        try:
            # Save file with unique name
            filename = secure_filename(file.filename)
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            unique_filename = f"{file_id}{file_extension}"
            file_path = UPLOAD_FOLDER / unique_filename

            file.save(str(file_path))

            # Analyze the document and stream the response
            def generate():
                try:
                    response_stream = self.analyzer.analyze_document(str(file_path), stream=True)
                    
                    assistant_chunks = []
                    for event in response_stream:
                        chunk_text = event.candidates[0].content.parts[0].text
                        assistant_chunks.append(chunk_text)
                        yield chunk_text

                    # Save the complete response to session
                    assistant_msg = "".join(assistant_chunks)
                    current_session = self.tenant_session.get()
                    current_session["messages"].append(
                        {"role": "model", "content": assistant_msg}
                    )
                    self.tenant_session.set(current_session)

                except Exception as e:
                    error_msg = f"Error analyzing document: {str(e)}"
                    yield error_msg

                finally:
                    # Clean up: remove the uploaded file
                    try:
                        if file_path.exists():
                            file_path.unlink()
                    except Exception as cleanup_error:
                        print(f"Warning: Could not delete uploaded file: {cleanup_error}")

            return Response(
                stream_with_context(generate()),
                mimetype="text/plain",
            )

        except Exception as e:
            # Clean up file if it was saved
            try:
                if 'file_path' in locals() and file_path.exists():
                    file_path.unlink()
            except:
                pass
            abort(500, f"Upload processing failed: {str(e)}")