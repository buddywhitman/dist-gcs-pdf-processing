import os
import base64
from unittest.mock import patch, MagicMock
from src.ocr import gemini_ocr_page
import tempfile

@patch("src.ocr.requests.post")
def test_gemini_ocr_page_success(mock_post):
    # Simulate Gemini API returning markdown
    mock_post.return_value.status_code = 200
    mock_post.return_value.raise_for_status = lambda: None
    mock_post.return_value.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "# Markdown output"}]}}
        ]
    }
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")
        result = gemini_ocr_page(path, 1)
        assert "Markdown output" in result
    finally:
        os.remove(path)

@patch("src.ocr.requests.post")
def test_gemini_ocr_page_error(mock_post):
    # Simulate Gemini API error response
    mock_post.return_value.status_code = 400
    mock_post.return_value.raise_for_status.side_effect = Exception("API error")
    fd, path = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(b"%PDF-1.4\n%EOF")
        try:
            gemini_ocr_page(path, 1)
        except Exception as e:
            assert "API error" in str(e)
    finally:
        os.remove(path) 