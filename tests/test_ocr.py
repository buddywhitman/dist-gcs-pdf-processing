import os
from unittest.mock import patch

from dist_gcs_pdf_processing.ocr import gemini_ocr_page
import tempfile


@patch("dist_gcs_pdf_processing.ocr.requests.post")
def test_gemini_ocr_page_success(mock_post):
    # Simulate Gemini API returning markdown
    mock_response = mock_post.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": "# Test Document\n\nThis is a test."}]
            }
        }]
    }
    
    # Test with a temporary PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf content")
        tmp_file.flush()
        
        result = gemini_ocr_page(tmp_file.name, "test_trace")
        
        # Clean up
        os.unlink(tmp_file.name)
    
    assert result == "# Test Document\n\nThis is a test."
    mock_post.assert_called_once()


@patch("dist_gcs_pdf_processing.ocr.requests.post")
def test_gemini_ocr_page_failure(mock_post):
    # Simulate API failure
    mock_response = mock_post.return_value
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("API Error")
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf content")
        tmp_file.flush()
        
        result = gemini_ocr_page(tmp_file.name, "test_trace")
        
        # Clean up
        os.unlink(tmp_file.name)
    
    assert result is None
    mock_post.assert_called_once()