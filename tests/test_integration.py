import os
import tempfile
import shutil
from unittest.mock import patch
from dist_gcs_pdf_processing.unified_worker import *

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
    # Patch download_from_gcs to copy the sample PDF to the temp dir
    def fake_download(file_name, dest_dir, trace_id=None):
        dest_path = os.path.join(dest_dir, os.path.basename(file_name))
        shutil.copy(SAMPLE_PDF, dest_path)
        return dest_path
    mock_download.side_effect = fake_download
    # Patch gemini_ocr_page to return dummy markdown
    mock_gemini_ocr.return_value = "# Dummy OCR\nSome text."
    # Patch upload_to_gcs to just record call
    mock_upload.return_value = True
    # Run the worker on the sample file
    process_file(os.path.basename(SAMPLE_PDF))
    # Check that download, upload, and OCR were called
    assert mock_download.called
    assert mock_gemini_ocr.called
    assert mock_upload.called
    # Check logs
    assert mock_log_json.call_count > 0
    # No dead letter or supabase error for success
    mock_log_dead.assert_not_called()
    mock_log_supabase.assert_not_called()
