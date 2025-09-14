import os
import tempfile
from dist_gcs_pdf_processing.unified_worker import (
    split_pdf_to_pages,
    markdown_to_pdf,
    is_valid_pdf,
    get_pdf_page_count
)


def test_pdf_validation():
    """Test PDF validation functions."""
    # Test with a non-existent file
    assert not is_valid_pdf("nonexistent.pdf")
    assert get_pdf_page_count("nonexistent.pdf") == 0


def test_markdown_to_pdf():
    """Test markdown to PDF conversion."""
    markdown_content = "# Test Document\n\nThis is a test document with **bold** text."
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        pdf_path = tmp_file.name
    
    try:
        result_path = markdown_to_pdf(markdown_content, pdf_path)
        assert result_path == pdf_path
        assert os.path.exists(pdf_path)
        assert is_valid_pdf(pdf_path)
        assert get_pdf_page_count(pdf_path) == 1
    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)