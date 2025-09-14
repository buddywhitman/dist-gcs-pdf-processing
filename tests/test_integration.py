import os
import shutil
from unittest.mock import patch

from dist_gcs_pdf_processing.unified_worker import (
    process_file_with_resume,
    split_pdf_to_pages,
    markdown_to_pdf,
    is_valid_pdf,
    get_pdf_page_count
)

SAMPLE_PDF = os.path.join(
    os.path.dirname(__file__),
    "testdata",
    "2022-03-07 Survey Dept. fees 2022-23.pdf"
)


@patch("dist_gcs_pdf_processing.unified_worker.upload_to_gcs")
@patch("dist_gcs_pdf_processing.unified_worker.download_from_gcs")
@patch("dist_gcs_pdf_processing.unified_worker.gemini_ocr_page")
@patch("dist_gcs_pdf_processing.unified_worker.log_supabase_error")
@patch("dist_gcs_pdf_processing.unified_worker.log_dead_letter")
@patch("dist_gcs_pdf_processing.unified_worker.log_json")
def test_full_pipeline(
    mock_log_json,
    mock_log_dead,
    mock_log_supabase,
    mock_gemini_ocr,
    mock_download,
    mock_upload
):
    """Test the full PDF processing pipeline."""
    # Mock the download to return a local file
    mock_download.return_value = SAMPLE_PDF
    
    # Mock the Gemini OCR to return markdown
    mock_gemini_ocr.return_value = "# Test Document\n\nThis is a test."
    
    # Mock the upload to succeed
    mock_upload.return_value = True
    
    # Process the file
    result = process_file_with_resume("test.pdf", "test_trace")
    
    # Verify the pipeline was called
    mock_download.assert_called_once()
    mock_upload.assert_called_once()
    mock_gemini_ocr.assert_called()
    
    # Verify logging was called
    mock_log_json.assert_called()
    
    assert result is not None


def test_pdf_processing_functions():
    """Test individual PDF processing functions."""
    # Test PDF validation
    if os.path.exists(SAMPLE_PDF):
        assert is_valid_pdf(SAMPLE_PDF)
        assert get_pdf_page_count(SAMPLE_PDF) > 0
        
        # Test page splitting
        pages = split_pdf_to_pages(SAMPLE_PDF)
        assert len(pages) > 0
        
        # Test markdown to PDF conversion
        markdown_content = "# Test\n\nThis is a test document."
        pdf_path = markdown_to_pdf(markdown_content, "test_output.pdf")
        assert os.path.exists(pdf_path)
        
        # Clean up
        if os.path.exists(pdf_path):
            os.remove(pdf_path)