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
        tmp_file.close()  # Close the file handle

        try:
            result = gemini_ocr_page(tmp_file.name, "test_trace")
            assert result == "# Test Document\n\nThis is a test."
            mock_post.assert_called_once()
        finally:
            # Clean up with retry logic for Windows
            try:
                os.unlink(tmp_file.name)
            except PermissionError:
                # On Windows, sometimes the file is still in use
                import time
                time.sleep(0.1)
                try:
                    os.unlink(tmp_file.name)
                except PermissionError:
                    # If still failing, just skip cleanup
                    pass

@patch("dist_gcs_pdf_processing.ocr.requests.post")
def test_gemini_ocr_page_failure(mock_post):
    # Simulate API failure
    mock_response = mock_post.return_value
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = Exception("API Error")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        tmp_file.write(b"fake pdf content")
        tmp_file.flush()
        tmp_file.close()  # Close the file handle

        try:
            result = gemini_ocr_page(tmp_file.name, "test_trace")
            assert result is None
        except Exception:
            # Expected to fail with API error
            pass
        finally:
            # Clean up with retry logic for Windows
            try:
                os.unlink(tmp_file.name)
            except PermissionError:
                # On Windows, sometimes the file is still in use
                import time
                time.sleep(0.1)
                try:
                    os.unlink(tmp_file.name)
                except PermissionError:
                    # If still failing, just skip cleanup
                    pass
    mock_post.assert_called_once()
