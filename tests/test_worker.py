import os
import tempfile
import pytest
from src.worker import split_pdf_to_pages, get_pdf_page_count, process_file, MAX_CONCURRENT_FILES, MAX_RETRIES, GEMINI_GLOBAL_CONCURRENCY
from pypdf import PdfWriter, PdfReader
import shutil
from unittest.mock import patch, MagicMock, call
from src.gcs_utils import list_new_files
import threading
import time
import io
import glob

def create_sample_pdf(path, num_pages=3):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        writer.write(f)

@pytest.fixture
def sample_pdf():
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "sample.pdf")
        create_sample_pdf(pdf_path, num_pages=3)
        yield pdf_path

def test_split_pdf_to_pages(sample_pdf):
    with tempfile.TemporaryDirectory() as tmpdir:
        pages = split_pdf_to_pages(sample_pdf, tmpdir)
        assert len(pages) == 3
        for page in pages:
            assert os.path.exists(page)
            assert get_pdf_page_count(page) == 1

def test_merge_pdf_pages(sample_pdf):
    with tempfile.TemporaryDirectory() as tmpdir:
        pages = split_pdf_to_pages(sample_pdf, tmpdir)
        merged_path = os.path.join(tmpdir, "merged.pdf")
        writer = PdfWriter()
        for page in pages:
            reader = PdfReader(page)
            writer.add_page(reader.pages[0])
        with open(merged_path, "wb") as f:
            writer.write(f)
        assert get_pdf_page_count(merged_path) == 3

SAMPLE_PDF = os.path.join(os.path.dirname(__file__), "testdata", "2022-03-07 Survey Dept. fees 2022-23.pdf")

@pytest.fixture
def sample_real_pdf():
    # Provide the real sample PDF path
    return SAMPLE_PDF

@patch("src.worker.log_supabase_error")
@patch("src.worker.log_dead_letter")
@patch("src.worker.log_json")
@patch("src.worker.upload_to_gcs")
@patch("src.worker.download_from_gcs")
@patch("src.worker.gemini_ocr_page")
def test_worker_processes_pdf(
    mock_gemini_ocr,
    mock_download,
    mock_upload,
    mock_log_json,
    mock_log_dead,
    mock_log_supabase,
    sample_real_pdf
):
    # Patch download_from_gcs to copy the sample PDF to the temp dir
    def fake_download(file_name, dest_dir, trace_id=None):
        dest_path = os.path.join(dest_dir, os.path.basename(file_name))
        shutil.copy(sample_real_pdf, dest_path)
        return dest_path
    mock_download.side_effect = fake_download
    # Patch gemini_ocr_page to return dummy markdown
    mock_gemini_ocr.return_value = "# Dummy OCR\nSome text."
    # Patch upload_to_gcs to just record call
    mock_upload.return_value = True
    # Run the worker on the sample file
    process_file(os.path.basename(sample_real_pdf))
    # Check that download, upload, and OCR were called
    assert mock_download.called
    assert mock_gemini_ocr.called
    assert mock_upload.called
    # Check logs
    assert mock_log_json.call_count > 0
    # No dead letter or supabase error for success
    mock_log_dead.assert_not_called()
    mock_log_supabase.assert_not_called()

@patch("src.gcs_utils.file_exists_in_dest", return_value=True)
def test_worker_skips_if_in_dest(mock_exists):
    # list_new_files should skip files that exist in dest
    with patch("google.cloud.storage.Client") as mock_client:
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = "test.pdf"
        mock_bucket.list_blobs.return_value = [mock_blob]
        mock_client.bucket.return_value = mock_bucket
        files = list_new_files()
        assert files == []

@patch("src.worker.log_supabase_error")
@patch("src.worker.log_dead_letter")
@patch("src.worker.log_json")
@patch("src.worker.upload_to_gcs")
@patch("src.worker.download_from_gcs")
@patch("src.worker.gemini_ocr_page")
def test_worker_error_handling(
    mock_gemini_ocr,
    mock_download,
    mock_upload,
    mock_log_json,
    mock_log_dead,
    mock_log_supabase,
    sample_real_pdf
):
    # Patch download_from_gcs to copy the sample PDF to the temp dir
    def fake_download(file_name, dest_dir, trace_id=None):
        dest_path = os.path.join(dest_dir, os.path.basename(file_name))
        shutil.copy(sample_real_pdf, dest_path)
        return dest_path
    mock_download.side_effect = fake_download
    # Patch gemini_ocr_page to raise error
    mock_gemini_ocr.side_effect = Exception("Gemini error!")
    # Patch upload_to_gcs to just record call
    mock_upload.return_value = True
    # Run the worker on the sample file (should retry and then fail)
    process_file(os.path.basename(sample_real_pdf))
    # Should log dead letter and supabase error
    assert mock_log_dead.called
    assert mock_log_supabase.called
    # Should log persistent_error
    assert any(
        call_args[0][0] == "persistent_error"
        for call_args in mock_log_json.call_args_list
    )

def create_in_memory_pdf(num_pages=1):
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf

def test_per_page_retry_logic():
    call_count = {'count': 0}
    def flaky_ocr(*args, **kwargs):
        if call_count['count'] < 2:
            call_count['count'] += 1
            raise Exception("Temporary Gemini error!")
        return "# Success after retry"
    with patch("src.worker.gemini_ocr_page", side_effect=flaky_ocr):
        with patch("src.worker.download_from_gcs") as mock_download, \
             patch("src.worker.upload_to_gcs") as mock_upload:
            def fake_download(file_name, dest_dir, trace_id=None):
                dest_path = os.path.join(dest_dir, os.path.basename(SAMPLE_PDF))
                shutil.copy(SAMPLE_PDF, dest_path)
                return dest_path
            mock_download.side_effect = fake_download
            mock_upload.return_value = True
            process_file(os.path.basename(SAMPLE_PDF))
    assert call_count['count'] == 2

def test_file_level_concurrency():
    # Use all PDFs in testdata as the mock source bucket
    testdata_dir = os.path.join(os.path.dirname(__file__), "testdata")
    files = [os.path.basename(f) for f in glob.glob(os.path.join(testdata_dir, "*.pdf"))]
    processed = []
    concurrent_counts = []
    lock = threading.Lock()
    active = 0
    to_process = set(files)
    def slow_process_file(file_name):
        nonlocal active
        with lock:
            active += 1
            concurrent_counts.append(active)
        processed.append(file_name)
        time.sleep(0.5)
        with lock:
            active -= 1
    # Patch process_file in the correct namespace
    import src.worker as worker_mod
    with patch.object(worker_mod, "process_file", side_effect=slow_process_file):
        # Patch list_new_files to yield the next unprocessed files as the worker requests them
        def list_next_files():
            # Always return up to MAX_CONCURRENT_FILES unprocessed files
            batch = []
            for f in list(to_process):
                if len(batch) >= worker_mod.MAX_CONCURRENT_FILES:
                    break
                batch.append(f)
                to_process.remove(f)
            return batch
        with patch.object(worker_mod, "list_new_files", side_effect=list_next_files):
            with patch.object(worker_mod, "POLL_INTERVAL", 0.1):
                thread = threading.Thread(target=worker_mod.start_worker, daemon=True)
                thread.start()
                # Wait long enough for all files to be processed
                time.sleep(1 + 0.6 * len(files))
    assert set(processed) == set(files)
    assert all(c <= worker_mod.MAX_CONCURRENT_FILES for c in concurrent_counts)
    # Clean up any generated output files (not source PDFs)
    output_dirs = [os.path.join(os.path.dirname(__file__), d) for d in ["../logs", "../src/processed", "../src/staging"]]
    for d in output_dirs:
        if os.path.exists(d):
            for f in os.listdir(d):
                fpath = os.path.join(d, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
                elif os.path.isdir(fpath):
                    shutil.rmtree(fpath, ignore_errors=True)

def test_global_gemini_throttling():
    # Patch the global semaphore to 1 to force serial execution
    from src.worker import gemini_global_semaphore
    orig_value = gemini_global_semaphore._value
    gemini_global_semaphore._value = 1
    call_order = []
    def slow_ocr(*args, **kwargs):
        call_order.append(time.time())
        time.sleep(0.2)
        return "# OCR"
    with patch("src.worker.gemini_ocr_page", side_effect=slow_ocr):
        with patch("src.worker.download_from_gcs") as mock_download, \
             patch("src.worker.upload_to_gcs") as mock_upload:
            mock_download.side_effect = lambda file_name, dest_dir, trace_id=None: __file__
            mock_upload.return_value = True
            process_file("dummy.pdf")
    # Calls should be spaced out, not concurrent
    diffs = [call_order[i+1] - call_order[i] for i in range(len(call_order)-1)]
    assert all(d > 0.15 for d in diffs)
    gemini_global_semaphore._value = orig_value

def test_trace_id_in_logs():
    logs = []
    prints = []
    class DummyLogger:
        def info(self, msg): logs.append(msg)
        def error(self, msg): logs.append(msg)
    def fake_print(*args, **kwargs):
        prints.append(" ".join(str(a) for a in args))
    with patch("src.worker.logger", new=DummyLogger()):
        with patch("src.worker.gemini_ocr_page", return_value="# OCR"):
            with patch("src.worker.download_from_gcs") as mock_download, \
                 patch("src.worker.upload_to_gcs") as mock_upload, \
                 patch("builtins.print", side_effect=fake_print):
                def fake_download(file_name, dest_dir, trace_id=None):
                    dest_path = os.path.join(dest_dir, os.path.basename(SAMPLE_PDF))
                    shutil.copy(SAMPLE_PDF, dest_path)
                    return dest_path
                mock_download.side_effect = fake_download
                mock_upload.return_value = True
                process_file(os.path.basename(SAMPLE_PDF))
    assert any("[START][" in log for log in logs + prints)
    assert any("Processing file:" in log for log in logs + prints) 