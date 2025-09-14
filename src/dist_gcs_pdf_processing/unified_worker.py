"""
Unified PDF Processing Worker: Comprehensive worker with resume capability,
concurrent processing, distributed locking, and multi-storage backend support.

Features:
- Resume capability: Can resume from where it left off after crashes
- Concurrent processing: File-level and page-level concurrency with backpressure
- Multi-storage backends: GCS and Google Drive support via StorageInterface
- Distributed locking: Prevents duplicate processing across instances
- Comprehensive logging: JSON logs, dead letter queue, Supabase integration
- PDF validation: Validates PDF integrity before processing
- Rate limiting: Global Gemini API throttling and storage operation limits
- Graceful shutdown: Proper cleanup on termination signals
"""
import os
import sys
from dist_gcs_pdf_processing.env import load_env_and_credentials

load_env_and_credentials()
os.environ["G_MESSAGES_DEBUG"] = "none"
os.environ["G_DEBUG"] = "fatal-warnings"
os.environ["PYTHONWARNINGS"] = "ignore"

import time
import tempfile
import shutil
import logging
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
    wait,
    FIRST_COMPLETED)
from collections import namedtuple
from typing import List, Dict, Set, Optional
from .storage_interface import get_storage_backend
from .ocr import gemini_ocr_page
from .config import (
    POLL_INTERVAL,
    STAGING_DIR,
    PROCESSED_DIR,
    PAGE_MAX_WORKERS,
    MAX_CONCURRENT_FILES,
    MAX_CONCURRENT_WORKERS,
    GEMINI_GLOBAL_CONCURRENCY)
from pypdf import PdfReader, PdfWriter
import markdown2
from weasyprint import HTML
from logging.handlers import TimedRotatingFileHandler
import json
from datetime import datetime, timedelta
import uuid
import requests
import threading
import base64
import signal
import atexit
from .shared import GCS_LIMITER, GEMINI_LIMITER, RateLimiter
from queue import Queue, Empty
import concurrent.futures
import hashlib
import redis
from contextlib import contextmanager

# Windows compatibility for file locking
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    import msvcrt

# Set up a logs directory and file handler for local logging
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
JSON_LOGS_DIR = os.path.join(LOGS_DIR, "json")
DEAD_LETTER_DIR = os.path.join(LOGS_DIR, "dead_letter")
PROGRESS_DIR = os.path.join(LOGS_DIR, "progress")
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(JSON_LOGS_DIR, exist_ok=True)
os.makedirs(DEAD_LETTER_DIR, exist_ok=True)
os.makedirs(PROGRESS_DIR, exist_ok=True)

# Set up daily rotating log file
log_file_path = os.path.join(LOGS_DIR, "worker.log")
file_handler = (
    TimedRotatingFileHandler(log_file_path, when="midnight", backupCount=20
    0))
file_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s %(levelname)s %(message)s'))
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler])
logger = logging.getLogger("dcpr.worker")

# Configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
MAX_QUEUE = int(os.getenv("MAX_QUEUE", 100))
REDIS_URL = os.getenv("REDIS_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_ERROR_LOG_TABLE = "Activity_Error_Log"
WORKER_INSTANCE_ID = os.getenv("WORKER_INSTANCE_ID", str(uuid.uuid4())[:8])

# Global concurrency controls
gemini_global_semaphore = threading.Semaphore(GEMINI_GLOBAL_CONCURRENCY)
worker_semaphore = threading.Semaphore(MAX_CONCURRENT_WORKERS)
active_workers = 0
active_workers_lock = threading.Lock()

# Redis client for distributed locking
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()  # Test connection
        logger.info("Connected to Redis for distributed locking")
    except Exception as e:
        logger.warning("Failed to connect to Redis: {e}. Using file-based locking.")
        redis_client = None

PageResult = namedtuple("PageResult", ["page_number", "markdown"])

def log_json(event_type, message, extra=None, trace_id=None, json_dir=JSON_LOGS_DIR):
    """Log structured JSON events."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "message": message,
        "trace_id": trace_id or str(uuid.uuid4()),
        "worker_instance": WORKER_INSTANCE_ID,
        "extra": extra or {}
    }
    json_log_path = os.path.join(json_dir, "{datetime.utcnow().date()}.json")
    with open(json_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

def log_dead_letter(file_name, error, trace_id=None, extra=None):
    """Log failed files to dead letter queue."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "file_name": file_name,
        "error": error,
        "trace_id": trace_id or str(uuid.uuid4()),
        "worker_instance": WORKER_INSTANCE_ID,
        "extra": extra or {}
    }
    dead_letter_path = os.path.join(DEAD_LETTER_DIR, "dead_letter.log")
    with open(dead_letter_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

def log_supabase_error(error_message, created_time=None):
    """Log persistent errors to Supabase."""
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        return

    url = "{SUPABASE_URL}/rest/v1/{SUPABASE_ERROR_LOG_TABLE}"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": "Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    data = {
        "Activity Log/Error Message": error_message,
        "type": "error",
        "workflow name": "PDF Processing Worker",
        "Created time": created_time or datetime.utcnow().isoformat(),
        "CreatedAt": datetime.utcnow().isoformat(),
        "UpdatedAt": datetime.utcnow().isoformat(),
        "nc_order": None,
        "worker_instance": WORKER_INSTANCE_ID
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
    except Exception as e:
        log_dead_letter("supabase_error", "Failed to log to Supabase: {e}", extra={"original_error": error_message})

@contextmanager
def distributed_lock(lock_key: str, timeout: int = 300):
    """Distributed lock using Redis or file-based fallback."""
    lock_acquired = False
    lock_value = "{WORKER_INSTANCE_ID}_{int(time.time())}"

    if redis_client:
        # Redis-based distributed lock
        try:
            # Try to acquire lock with expiration
            if redis_client.set(lock_key, lock_value, nx=True, ex=timeout):
                lock_acquired = True
                logger.info("Acquired Redis lock: {lock_key}")
            else:
                logger.info("Could not acquire Redis lock: {lock_key}")
        except Exception as e:
            logger.warning("Redis lock failed: {e}. Falling back to file lock.")
            redis_client = None

    if not lock_acquired and not redis_client:
        # File-based lock fallback
        lock_file = os.path.join(
            LOGS_DIR, "lock_{hashlib.md5(lock_key.encode()).hexdigest()}.lock"
        )
        try:
            with open(lock_file, 'w') as f:
                if HAS_FCNTL:
                    # Unix/Linux file locking
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    # Windows file locking
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                f.write(lock_value)
                lock_acquired = True
                logger.info("Acquired file lock: {lock_key}")
        except (OSError, IOError):
            logger.info("Could not acquire file lock: {lock_key}")

    try:
        yield lock_acquired
    finally:
        if lock_acquired:
            if redis_client:
                try:
                    # Only release if we still own the lock
                    if redis_client.get(lock_key) == lock_value:
                        redis_client.delete(lock_key)
                        logger.info("Released Redis lock: {lock_key}")
                except Exception as e:
                    logger.warning("Failed to release Redis lock: {e}")
            else:
                try:
                    lock_file = os.path.join(
                        LOGS_DIR, f"lock_{hashlib.md5(lock_key.encode()).hexdigest()}.lock"
                    )
                    if os.path.exists(lock_file):
                        # Release Windows lock if needed
                        if not HAS_FCNTL:
                            try:
                                with open(lock_file, 'r+') as f:
                                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                            except Exception:
                                pass  # Ignore unlock errors
                        os.remove(lock_file)
                        logger.info("Released file lock: {lock_key}")
                except Exception as e:
                    logger.warning("Failed to release file lock: {e}")

def is_valid_pdf(file_path):
    """Validate PDF file integrity."""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False
            f.seek(-5, 2)
            trailer = f.read()
            if b'%%EOF' not in trailer:
                return False
        return True
    except Exception as e:
        logger.error("Exception while validating PDF: {e}")
        return False

def split_pdf_to_pages(pdf_path: str, pdf_dir: str) -> List[str]:
    """Split PDF into individual page files."""
    reader = PdfReader(pdf_path)
    page_files = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)
        page_path = os.path.join(pdf_dir, "page_{i+1:04d}.pd")
        with open(page_path, "wb") as f:
            writer.write(f)
        page_files.append(page_path)
    return page_files

def markdown_to_pdf(markdown: str, pdf_path: str, html_dir: str, page_num: int):
    """Convert markdown to PDF using WeasyPrint."""
    html = markdown2.markdown(markdown)
    html_path = os.path.join(html_dir, "page_{page_num:04d}.html")
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(html)
    HTML(string=html).write_pdf(pdf_path)

def get_pdf_page_count(pdf_path):
    """Get the number of pages in a PDF."""
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        logger.error("Could not read PDF: {e}")
        return 0

def get_progress_file_path(file_name: str) -> str:
    """Get progress file path for a specific file."""
    safe_filename = file_name.replace("/", "_").replace("\\", "_")
    return os.path.join(PROGRESS_DIR, "{safe_filename}_progress.json")

def load_file_progress(file_name: str) -> Dict:
    """Load progress for a specific file."""
    progress_path = get_progress_file_path(file_name)
    if os.path.exists(progress_path):
        try:
            with open(progress_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Failed to load progress for {file_name}: {e}")
    return {
        "status": "not_started",
        "total_pages": 0,
        "completed_pages": [],
        "failed_pages": [],
        "merged_pdf_path": None,
        "start_time": None,
        "last_update": None,
        "worker_instance": WORKER_INSTANCE_ID
    }

def save_file_progress(file_name: str, progress: Dict):
    """Save progress for a specific file."""
    progress_path = get_progress_file_path(file_name)
    try:
        progress["last_update"] = datetime.utcnow().isoformat()
        progress["worker_instance"] = WORKER_INSTANCE_ID
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        logger.warning("Failed to save progress for {file_name}: {e}")

def cleanup_file_progress(file_name: str):
    """Clean up progress file after successful completion."""
    progress_path = get_progress_file_path(file_name)
    try:
        if os.path.exists(progress_path):
            os.remove(progress_path)
            logger.info("Cleaned up progress file for {file_name}")
    except Exception as e:
        logger.warning("Failed to clean up progress file for {file_name}: {e}")

def ocr_page_with_retries(pdf_path, page_number, trace_id):
    """OCR a single page with per-page retries and global Gemini API throttling."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with gemini_global_semaphore:
                markdown = gemini_ocr_page(pdf_path, page_number)
            return markdown
        except Exception as e:
            logger.error("[{trace_id}] OCR failed for page {page_number} (attempt {attempt}/{MAX_RETRIES}): {e}")
            log_json("ocr_error", "OCR failed for page {page_number} (attempt {attempt}/{MAX_RETRIES}): {e}", trace_id=trace_id)
            if attempt == MAX_RETRIES:
                return None
            time.sleep(2)  # brief backoff

def process_file_with_resume(file_name, storage_backend):
    """Process file with resume capability and distributed locking."""
    trace_id = str(uuid.uuid4())
    lock_key = "pdf_processing:{file_name}"

    logger.info("[{trace_id}] Processing file: {file_name}")
    log_json("start_processing", "Processing file: {file_name}", trace_id=trace_id)

    # Try to acquire distributed lock
    with distributed_lock(lock_key, timeout=3600) as lock_acquired:
        if not lock_acquired:
            logger.info("[{trace_id}] File {file_name} is being processed by another worker")
            return False

        # Load existing progress
        progress = load_file_progress(file_name)
        logger.info("[{trace_id}] File progress: {progress['status']} - {len(progress['completed_pages'])}/{progress['total_pages']} pages completed")

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_dir = os.path.join(temp_dir, "pdfs")
                md_dir = os.path.join(temp_dir, "markdowns")
                html_dir = os.path.join(temp_dir, "htmls")
                os.makedirs(pdf_dir, exist_ok=True)
                os.makedirs(md_dir, exist_ok=True)
                os.makedirs(html_dir, exist_ok=True)

                # Download file if not already done
                if progress["status"] == "not_started":
                    logger.info("[{trace_id}] Downloading file to {temp_dir}")
                    local_pdf = (
                        os.path.join(temp_dir, os.path.basename(file_name)))
                    if not storage_backend.download_file(file_name, local_pdf, trace_id=trace_id):
                        logger.error("[{trace_id}] Failed to download {file_name}")
                        return False

                    # Validate PDF
                    if not is_valid_pdf(local_pdf):
                        logger.error("[{trace_id}] Invalid PDF file: {file_name}")
                        log_dead_letter(file_name, "Invalid PDF file", trace_id=trace_id)
                        return False

                    # Split PDF and update progress
                    logger.info("[{trace_id}] Splitting PDF into pages...")
                    page_files = split_pdf_to_pages(local_pdf, pdf_dir)
                    logger.info("[{trace_id}] Split into {len(page_files)} pages")

                    progress["status"] = "splitting_complete"
                    progress["total_pages"] = len(page_files)
                    progress["start_time"] = datetime.utcnow().isoformat()
                    save_file_progress(file_name, progress)
                else:
                    # Resume from existing progress
                    logger.info("[{trace_id}] Resuming from existing progress")
                    local_pdf = (
                        os.path.join(temp_dir, os.path.basename(file_name)))
                    if not storage_backend.download_file(file_name, local_pdf, trace_id=trace_id):
                        logger.error("[{trace_id}] Failed to download {file_name}")
                        return False

                    # Re-split PDF for processing
                    page_files = split_pdf_to_pages(local_pdf, pdf_dir)
                    logger.info("[{trace_id}] Re-split into {len(page_files)} pages for processing")

                # Determine which pages need processing
                pages_to_process = []
                results = []

                for i, page_file in enumerate(page_files):
                    page_number = i + 1
                    if page_number in progress["completed_pages"]:
                        # Load cached result
                        safe_filename = (
                            file_name.replace('/', '_').replace('\\', '_'))
                        cached_md_path = os.path.join(
                            PROGRESS_DIR, f"{safe_filename}_page_{page_number:04d}.md"
                        )
                        if os.path.exists(cached_md_path):
                            with open(cached_md_path, 'r', encoding='utf-8') as f:
                                cached_markdown = f.read()
                            results.append(PageResult(page_number, cached_markdown))
                            logger.info("[{trace_id}] Using cached result for page {page_number}")
                        else:
                            # Cached file missing, need to reprocess
                            pages_to_process.append((page_file, page_number))
                    else:
                        # Need to process this page
                        pages_to_process.append((page_file, page_number))

                logger.info("[{trace_id}] Need to process {len(pages_to_process)} pages (out of {len(page_files)})")

                if pages_to_process:
                    # Process remaining pages in parallel
                    logger.info("[{trace_id}] Processing {len(pages_to_process)} pages in parallel...")
                    with ThreadPoolExecutor(max_workers=PAGE_MAX_WORKERS) as executor:
                        futures = (
                            {executor.submit(ocr_page_with_retries, pf, pn,
                             trace_id): (pn, pf) for pf, pn in pages_to_pro
                            cess})
                        for future in as_completed(futures):
                            page_number, _ = futures[future]
                            markdown = future.result()
                            if markdown is not None:
                                results.append(PageResult(page_number, markdown))
                                # Save to cache
                                safe_filename = (
                                    file_name.replace('/', '_').replace('\\
                                    ', '_'))
                                cached_md_path = os.path.join(
                                    PROGRESS_DIR, f"{safe_filename}_page_{page_number:04d}.md"
                                )
                                with open(cached_md_path, 'w', encoding='utf-8') as f:
                                    f.write(markdown)

                                # Update progress
                                if page_number not in progress["completed_pages"]:
                                    progress["completed_pages"].append(page_number)
                                progress["completed_pages"].sort()
                                save_file_progress(file_name, progress)

                                logger.info("[{trace_id}] OCR for page {page_number} complete")
                            else:
                                logger.error("[{trace_id}] OCR permanently failed for page {page_number} after {MAX_RETRIES} attempts")
                                log_json("ocr_permanent_error", "OCR permanently failed for page {page_number}", trace_id=trace_id)

                                # Update progress
                                if page_number not in progress["failed_pages"]:
                                    progress["failed_pages"].append(page_number)
                                save_file_progress(file_name, progress)

                if not results:
                    logger.error("[{trace_id}] No pages were successfully processed")
                    return False

                logger.info("[{trace_id}] Successfully processed {len(results)} pages (total: {len(page_files)})")

                # Sort results by page number
                results.sort(key=lambda x: x.page_number)

                # Convert markdown to PDF
                single_pdf_paths = []
                for page_number, markdown in results:
                    pdf_path = os.path.join(
                        pdf_dir, f"ocr_page_{page_number:04d}.pdf"
                    )
                    try:
                        markdown_to_pdf(markdown, pdf_path, html_dir, page_number)
                        single_pdf_paths.append(pdf_path)
                        logger.info("[{trace_id}] Markdown to PDF for page {page_number} complete")
                    except Exception as e:
                        logger.error("[{trace_id}] Markdown to PDF failed for page {page_number}: {e}")

                # Merge PDFs
                merged_pdf_path = os.path.join(temp_dir, "merged.pd")
                writer = PdfWriter()
                for pdf in single_pdf_paths:
                    try:
                        reader = PdfReader(pdf)
                        writer.add_page(reader.pages[0])
                    except Exception as e:
                        logger.error("[{trace_id}] Merging page PDF failed for {pdf}: {e}")

                with open(merged_pdf_path, "wb") as f:
                    writer.write(f)

                logger.info("[{trace_id}] Checking merged PDF at {merged_pdf_path}")
                merged_pdf_size = os.path.getsize(merged_pdf_path)
                logger.info("[{trace_id}] Merged PDF size: {merged_pdf_size} bytes")

                original_page_count = get_pdf_page_count(local_pdf)
                output_page_count = get_pdf_page_count(merged_pdf_path)
                logger.info("[{trace_id}] Original PDF pages: {original_page_count}, Output PDF pages: {output_page_count}")

                if original_page_count != output_page_count:
                    logger.warning("[{trace_id}] Page count mismatch: {original_page_count} vs {output_page_count}")

                # Update progress
                progress["status"] = "merging_complete"
                progress["merged_pdf_path"] = merged_pdf_path
                save_file_progress(file_name, progress)

                logger.info("[{trace_id}] Uploading merged PDF as {os.path.basename(file_name)}")
                upload_result = (
                    storage_backend.upload_file(merged_pdf_path, os.path.ba
                    sename(file_name), trace_id=trace_id))

                if upload_result:
                    logger.info("[{trace_id}] Finished processing {file_name}")
                    log_json("success", "Finished processing {file_name}", trace_id=trace_id)

                    # Clean up progress and cache files
                    cleanup_file_progress(file_name)
                    safe_filename = (
                        file_name.replace('/', '_').replace('\\', '_'))
                    for page_number in range(1, len(page_files) + 1):
                        cached_md_path = os.path.join(
                            PROGRESS_DIR, f"{safe_filename}_page_{page_number:04d}.md"
                        )
                        if os.path.exists(cached_md_path):
                            os.remove(cached_md_path)

                    return True
                else:
                    logger.error("[{trace_id}] Upload failed for {file_name}")
                    progress["status"] = "upload_failed"
                    save_file_progress(file_name, progress)
                    return False

        except Exception as e:
            logger.error("[{trace_id}] Fatal error processing {file_name}: {e}")
            log_json("fatal_error", "Fatal error processing {file_name}: {e}", trace_id=trace_id)
            log_dead_letter(file_name, "Fatal error: {e}", trace_id=trace_id)
            log_supabase_error("Fatal error processing {file_name}: {e}")

            # Update progress
            progress["status"] = "error"
            progress["error"] = str(e)
            save_file_progress(file_name, progress)
            return False

def get_active_worker_count():
    """Get the number of active workers."""
    with active_workers_lock:
        return active_workers

def cleanup_old_files():
    """Clean up old log and temporary files."""
    now = datetime.utcnow()
    cutoff = now - timedelta(days=200)
    folders = (
        [LOGS_DIR, JSON_LOGS_DIR, DEAD_LETTER_DIR, PROGRESS_DIR, STAGING_DI
        R, PROCESSED_DIR])
    for folder in folders:
        if not os.path.exists(folder):
            continue
        for fname in os.listdir(folder):
            fpath = os.path.join(folder, fname)
            try:
                if os.path.isfile(fpath):
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        logger.info("Deleted old file: {fpath}")
                elif os.path.isdir(fpath):
                    mtime = datetime.utcfromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        shutil.rmtree(fpath, ignore_errors=True)
                        logger.info("Deleted old directory: {fpath}")
            except Exception as e:
                logger.error("Failed to delete {fpath}: {e}")

# Register cleanup for graceful shutdown
_temp_dirs = []
def _register_temp_dir(path):
    _temp_dirs.append(path)

def _cleanup_temp_dirs():
    for d in _temp_dirs:
        try:
            shutil.rmtree(d, ignore_errors=True)
            logger.info("Cleaned up temp dir: {d}")
        except Exception as e:
            logger.error("Failed to clean temp dir {d}: {e}")

atexit.register(_cleanup_temp_dirs)

def _signal_handler(signum, frame):
    logger.info("Received signal {signum}, cleaning up and exiting...")
    _cleanup_temp_dirs()
    exit(0)

for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, _signal_handler)

def start_worker(storage_backend):
    """Start the main worker loop with concurrent file processing."""
    in_progress = set()
    completed = set()
    pending = set()

    logger.info("Starting worker instance {WORKER_INSTANCE_ID}")
    logger.info("Max concurrent files: {MAX_CONCURRENT_FILES}")
    logger.info("Max concurrent workers: {PAGE_MAX_WORKERS}")
    logger.info("Gemini global concurrency: {GEMINI_GLOBAL_CONCURRENCY}")
    logger.info("Redis client: {'Connected' if redis_client else 'Not available'}")

    while True:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(storage_backend.list_new_files)
                try:
                    new_files = future.result(timeout=30)
                except concurrent.futures.TimeoutError:
                    logger.warning("Timeout in list_new_files. Skipping this poll.")
                    time.sleep(POLL_INTERVAL)
                    continue

            # Only fetch new files if we have room to process more
            if len(in_progress) < MAX_CONCURRENT_FILES:
                for f in new_files:
                    if f not in in_progress and f not in completed and f not in pending:
                        pending.add(f)
                        logger.info("Added to pending queue: {f}")

            # Start new files if we have capacity
            while len(in_progress) < MAX_CONCURRENT_FILES and pending:
                fname = pending.pop()
                in_progress.add(fname)

                def _cb(future, fname=fname):
                    in_progress.remove(fname)
                    completed.add(fname)
                    logger.info("Completed processing: {fname}")

                executor2 = getattr(start_worker, '_executor', None)
                if executor2 is None:
                    executor2 = (
                        concurrent.futures.ThreadPoolExecutor(max_workers=M
                        AX_CONCURRENT_FILES))
                    setattr(start_worker, '_executor', executor2)

                future2 = (
                    executor2.submit(process_file_with_resume, fname, stora
                    ge_backend))
                future2.add_done_callback(_cb)
                logger.info("Started processing: {fname}")

            # Log current status
            if in_progress or pending:
                logger.info("Status - In progress: {len(in_progress)}, Pending: {len(pending)}, Completed: {len(completed)}")

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            logger.error("Exception in main worker loop: {e}")
            time.sleep(POLL_INTERVAL)

def main():
    """Main entry point for the worker."""
    # Determine storage backend based on command used
    if len(sys.argv) > 0 and 'dist-drive-worker' in sys.argv[0]:
        storage_type = "drive"
    else:
        storage_type = os.getenv("STORAGE_BACKEND", "gcs")

    storage_backend = get_storage_backend(storage_type)

    print("=== Unified PDF Processing Worker ===")
    print(f"Worker Instance: {WORKER_INSTANCE_ID}")
    print(f"Storage Backend: {storage_type.upper()}")
    print(f"Poll interval: {POLL_INTERVAL} seconds")
    print(f"Max concurrent files: {MAX_CONCURRENT_FILES}")
    print(f"Max concurrent workers: {PAGE_MAX_WORKERS}")
    print(f"Gemini global concurrency: {GEMINI_GLOBAL_CONCURRENCY}")
    print("Resume capability: ENABLED")
    print(f"Distributed locking: {'Redis' if redis_client else 'File-based'}")
    print()

    cleanup_old_files()

    try:
        start_worker(storage_backend)
    except Exception as e:
        logger.error("Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
