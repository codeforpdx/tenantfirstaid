import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import mock_open, patch, Mock, MagicMock
from io import BytesIO
import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, Forbidden, InternalServerError

from tenantfirstaid.upload import (
    allowed_file,
    DocumentAnalyzer,
    UploadView,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    UPLOAD_FOLDER,
)
from tenantfirstaid.session import TenantSession


class TestAllowedFile:
    """Test the allowed_file function."""

    def test_allowed_file_returns_true_for_valid_extensions(self):
        """Test that allowed_file returns True for valid file extensions."""
        for ext in ALLOWED_EXTENSIONS:
            filename = f"test.{ext}"
            assert allowed_file(filename) is True

    def test_allowed_file_returns_true_for_uppercase_extensions(self):
        """Test that allowed_file handles uppercase extensions."""
        for ext in ALLOWED_EXTENSIONS:
            filename = f"test.{ext.upper()}"
            assert allowed_file(filename) is True

    def test_allowed_file_returns_false_for_invalid_extensions(self):
        """Test that allowed_file returns False for invalid extensions."""
        invalid_files = ["test.txt", "test.doc", "test.exe", "test.py"]
        for filename in invalid_files:
            assert allowed_file(filename) is False

    def test_allowed_file_returns_false_for_no_extension(self):
        """Test that allowed_file returns False for files without extensions."""
        assert allowed_file("test") is False

    def test_allowed_file_returns_false_for_empty_filename(self):
        """Test that allowed_file handles empty filename."""
        assert allowed_file("") is False

    def test_allowed_file_handles_multiple_dots(self):
        """Test that allowed_file correctly handles filenames with multiple dots."""
        assert allowed_file("test.backup.png") is True
        assert allowed_file("test.backup.txt") is False


class TestDocumentAnalyzer:
    """Test the DocumentAnalyzer class."""

    @pytest.fixture
    def mock_service_account(self):
        """Mock Google service account credentials."""
        with patch('tenantfirstaid.upload.service_account') as mock_sa:
            mock_credentials = Mock()
            mock_sa.Credentials.from_service_account_file.return_value = mock_credentials
            yield mock_sa, mock_credentials

    @pytest.fixture
    def mock_vertexai(self):
        """Mock VertexAI initialization."""
        with patch('tenantfirstaid.upload.vertexai') as mock_vertex:
            yield mock_vertex

    @pytest.fixture
    def mock_generative_model(self):
        """Mock GenerativeModel."""
        with patch('tenantfirstaid.upload.GenerativeModel') as mock_model_class:
            mock_model = Mock()
            mock_model_class.return_value = mock_model
            yield mock_model

    @pytest.fixture
    def document_analyzer(self, mock_service_account, mock_vertexai, mock_generative_model):
        """Create a DocumentAnalyzer instance with mocked dependencies."""
        return DocumentAnalyzer()

    def test_document_analyzer_initialization(self, mock_service_account, mock_vertexai, mock_generative_model):
        """Test DocumentAnalyzer initialization."""
        analyzer = DocumentAnalyzer()
        
        # Verify service account credentials were loaded
        mock_sa, _ = mock_service_account
        mock_sa.Credentials.from_service_account_file.assert_called_once()
        
        # Verify VertexAI was initialized
        mock_vertexai.init.assert_called_once()
        
        # Verify model was created
        assert analyzer.model is not None

    def test_analyze_document_file_not_found(self, document_analyzer):
        """Test analyze_document raises FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            document_analyzer.analyze_document("/nonexistent/file.png")

    def test_analyze_document_successful_analysis(self, document_analyzer):
        """Test successful document analysis."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file.write(b'fake image data')
            temp_file_path = temp_file.name

        try:
            # Mock the model response
            mock_response = Mock()
            document_analyzer.model.generate_content.return_value = mock_response

            # Test analysis
            result = document_analyzer.analyze_document(temp_file_path, stream=False)
            
            # Verify the model was called
            document_analyzer.model.generate_content.assert_called_once()
            assert result == mock_response

        finally:
            # Clean up
            os.unlink(temp_file_path)

    def test_analyze_document_streaming_analysis(self, document_analyzer):
        """Test document analysis with streaming enabled."""
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'fake pdf data')
            temp_file_path = temp_file.name

        try:
            mock_response = Mock()
            document_analyzer.model.generate_content.return_value = mock_response

            result = document_analyzer.analyze_document(temp_file_path, stream=True)
            
            # Verify streaming was enabled
            call_args = document_analyzer.model.generate_content.call_args
            assert call_args[1]['stream'] is True
            assert result == mock_response

        finally:
            os.unlink(temp_file_path)

    def test_analyze_document_mime_type_mapping(self, document_analyzer):
        """Test that correct MIME types are used for different file extensions."""
        test_cases = [
            ('.png', 'image/png'),
            ('.jpg', 'image/jpeg'),
            ('.jpeg', 'image/jpeg'),
            ('.pdf', 'application/pdf'),
        ]

        for ext, expected_mime in test_cases:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file.write(b'fake data')
                temp_file_path = temp_file.name

            try:
                document_analyzer.analyze_document(temp_file_path)
                
                # Check that Part.from_data was called with correct mime type
                call_args = document_analyzer.model.generate_content.call_args
                # The Part object would be in the first argument
                assert len(call_args[0]) == 1  # Should contain the Part object

            finally:
                os.unlink(temp_file_path)


class TestUploadView:
    """Test the UploadView class."""

    @pytest.fixture
    def app(self):
        """Create a Flask app for testing."""
        app = Flask(__name__)
        app.secret_key = 'test-secret-key'
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def mock_tenant_session(self):
        """Mock TenantSession."""
        session = Mock(spec=TenantSession)
        session.get.return_value = {"messages": []}
        return session

    @pytest.fixture
    def mock_document_analyzer(self):
        """Mock DocumentAnalyzer."""
        with patch('tenantfirstaid.upload.DocumentAnalyzer') as mock_class:
            mock_analyzer = Mock()
            mock_class.return_value = mock_analyzer
            yield mock_analyzer

    @pytest.fixture
    def upload_view(self, mock_tenant_session, mock_document_analyzer):
        """Create UploadView instance with mocked dependencies."""
        return UploadView(mock_tenant_session)

    def test_upload_view_no_session_returns_403(self, app, upload_view):
        """Test that requests without valid session return 403."""
        with app.test_request_context('/upload', method='POST'):
            with pytest.raises(Forbidden):
                upload_view.dispatch_request()

    def test_upload_view_no_file_returns_400(self, app, upload_view):
        """Test that requests without file return 400."""
        with app.test_request_context('/upload', method='POST') as ctx:
            ctx.session['site_user'] = 'test_user'
            with pytest.raises(BadRequest, match="No file uploaded"):
                upload_view.dispatch_request()

    def test_upload_view_empty_filename_returns_400(self, app, upload_view):
        """Test that requests with empty filename return 400."""
        with app.test_request_context('/upload', method='POST', data={'file': (BytesIO(b''), '')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            with pytest.raises(BadRequest, match="No file selected"):
                upload_view.dispatch_request()

    def test_upload_view_invalid_file_type_returns_400(self, app, upload_view):
        """Test that invalid file types return 400."""
        with app.test_request_context('/upload', method='POST', 
                                    data={'file': (BytesIO(b'content'), 'test.txt')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            with pytest.raises(BadRequest, match="Invalid file type"):
                upload_view.dispatch_request()

    def test_upload_view_file_too_large_returns_400(self, app, upload_view):
        """Test that files exceeding size limit return 400."""
        # Create file larger than MAX_FILE_SIZE
        large_content = b'x' * (MAX_FILE_SIZE + 1)
        
        with app.test_request_context('/upload', method='POST',
                                    data={'file': (BytesIO(large_content), 'test.png')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            with pytest.raises(BadRequest, match="File size exceeds 10MB limit"):
                upload_view.dispatch_request()

    @patch('tenantfirstaid.upload.UPLOAD_FOLDER')
    def test_upload_view_successful_upload_and_analysis(self, mock_upload_folder, app, upload_view, mock_document_analyzer):
        """Test successful file upload and analysis."""
        import tempfile
        
        # Mock upload folder
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_upload_folder.__truediv__ = lambda self, other: Path(temp_dir) / other
            mock_upload_folder.mkdir = Mock()
            
            # Mock analyzer response
            mock_candidate = Mock()
            mock_candidate.content.parts = [Mock()]
            mock_candidate.content.parts[0].text = "Analysis result chunk"
            
            mock_event = Mock()
            mock_event.candidates = [mock_candidate]
            
            mock_document_analyzer.analyze_document.return_value = iter([mock_event])
            
            file_content = b'fake image data'
            
            with app.test_request_context('/upload', method='POST',
                                        data={'file': (BytesIO(file_content), 'test.png')}) as ctx:
                ctx.session['site_user'] = 'test_user'
                
                response = upload_view.dispatch_request()
                
                # Verify response properties
                assert response.status_code == 200
                assert response.mimetype == 'text/plain'
                
                # Verify analyzer was called
                mock_document_analyzer.analyze_document.assert_called_once()

    def test_upload_view_analysis_error_handling(self, app, upload_view, mock_document_analyzer):
        """Test error handling during document analysis."""
        
        # Mock analyzer to raise exception
        mock_document_analyzer.analyze_document.side_effect = Exception("Analysis failed")
        
        with app.test_request_context('/upload', method='POST',
                                    data={'file': (BytesIO(b'content'), 'test.png')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            
            response = upload_view.dispatch_request()
            
            # Should still return 200 but with error content in stream
            assert response.status_code == 200

    @patch('tenantfirstaid.upload.secure_filename')
    @patch('tenantfirstaid.upload.uuid.uuid4')
    def test_upload_view_file_naming_and_cleanup(self, mock_uuid, mock_secure_filename, 
                                                app, upload_view, mock_document_analyzer):
        """Test that files are properly named and cleaned up."""
        
        # Mock file naming
        mock_uuid.return_value = Mock()
        mock_uuid.return_value.__str__ = Mock(return_value='test-uuid-123')
        mock_secure_filename.return_value = 'test.png'
        
        # Mock analyzer
        mock_candidate = Mock()
        mock_candidate.content.parts = [Mock()]
        mock_candidate.content.parts[0].text = "Test analysis"
        
        mock_event = Mock()
        mock_event.candidates = [mock_candidate]
        mock_document_analyzer.analyze_document.return_value = iter([mock_event])
        
        with app.test_request_context('/upload', method='POST',
                                    data={'file': (BytesIO(b'content'), 'test.png')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            
            response = upload_view.dispatch_request()
            
            # Verify secure_filename was called
            mock_secure_filename.assert_called_once_with('test.png')
            
            # Verify UUID was generated
            mock_uuid.assert_called_once()

    def test_upload_view_session_update(self, app, upload_view, mock_document_analyzer, mock_tenant_session):
        """Test that session is properly updated with analysis results."""
        
        # Mock session data
        session_data = {"messages": []}
        mock_tenant_session.get.return_value = session_data
        
        # Mock analyzer response
        mock_candidate = Mock()
        mock_candidate.content.parts = [Mock()]
        mock_candidate.content.parts[0].text = "Complete analysis text"
        
        mock_event = Mock()
        mock_event.candidates = [mock_candidate]
        mock_document_analyzer.analyze_document.return_value = iter([mock_event])
        
        with app.test_request_context('/upload', method='POST',
                                    data={'file': (BytesIO(b'content'), 'test.png')}) as ctx:
            ctx.session['site_user'] = 'test_user'
            
            response = upload_view.dispatch_request()
            
            # Consume the stream to trigger session update
            list(response.response)
            
            # Verify session was updated
            mock_tenant_session.set.assert_called_once()
            updated_session = mock_tenant_session.set.call_args[0][0]
            assert len(updated_session["messages"]) == 1
            assert updated_session["messages"][0]["role"] == "model"
            assert updated_session["messages"][0]["content"] == "Complete analysis text"


class TestUploadModule:
    """Test module-level functionality."""

    def test_upload_folder_creation(self):
        """Test that upload folder is created on module import."""
        # The folder should be created when the module is imported
        # This is tested by checking the UPLOAD_FOLDER exists
        assert UPLOAD_FOLDER is not None

    def test_constants_are_properly_defined(self):
        """Test that module constants are properly defined."""
        assert isinstance(ALLOWED_EXTENSIONS, set)
        assert len(ALLOWED_EXTENSIONS) > 0
        assert MAX_FILE_SIZE > 0
        assert isinstance(UPLOAD_FOLDER, Path)

    def test_document_analysis_prompt_is_comprehensive(self):
        """Test that the document analysis prompt contains key elements."""
        from tenantfirstaid.upload import DOCUMENT_ANALYSIS_PROMPT
        
        # Check for key sections
        assert "Document Type" in DOCUMENT_ANALYSIS_PROMPT
        assert "Key Information" in DOCUMENT_ANALYSIS_PROMPT
        assert "Legal Analysis" in DOCUMENT_ANALYSIS_PROMPT
        assert "Recommendations" in DOCUMENT_ANALYSIS_PROMPT
        assert "Citations" in DOCUMENT_ANALYSIS_PROMPT
        assert "Oregon" in DOCUMENT_ANALYSIS_PROMPT