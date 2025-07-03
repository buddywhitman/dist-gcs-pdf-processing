import os
import time
import concurrent.futures
import logging
print("GOOGLE_APPLICATION_CREDENTIALS =", os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
print("File exists:", os.path.isfile(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")))
from google.cloud import storage
from google.api_core.exceptions import NotFound
from .config import GCS_BUCKET, GCS_SOURCE_PREFIX, GCS_DEST_PREFIX, STAGING_DIR, PROCESSED_DIR
from .shared import GCS_LIMITER
from dist_gcs_pdf_processing.env import load_env_and_credentials

load_env_and_credentials()

print(f"[DEBUG] GCS_BUCKET: {GCS_BUCKET}")
print(f"[DEBUG] GCS_SOURCE_PREFIX: {GCS_SOURCE_PREFIX}")
print(f"[DEBUG] GCS_DEST_PREFIX: {GCS_DEST_PREFIX}")

logger = logging.getLogger("dcpr.worker")

def gcs_path(*parts):
    return '/'.join(part.strip('/\\') for part in parts if part)

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def file_exists_in_dest(file_name, trace_id=None):
    print(f"[DEBUG] Checking if file exists in dest: {file_name}")
    GCS_LIMITER.acquire()
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        dest_blob_name = gcs_path(GCS_DEST_PREFIX, file_name)
        start = time.time()
        exists = bucket.blob(dest_blob_name).exists()
        elapsed = time.time() - start
        print(f"[DEBUG] Exists in dest? {file_name}: {exists} (checked in {elapsed:.2f}s)")
        if elapsed > 10:
            print(f"[WARNING] GCS existence check for {file_name} took {elapsed:.2f} seconds!")
        return exists
    except Exception as e:
        print(f"[FATAL][GCS_UTILS] Exception in file_exists_in_dest: {e}")
        return False

def list_new_files(trace_id=None):
    GCS_LIMITER.acquire()
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        blobs = list(bucket.list_blobs(prefix=GCS_SOURCE_PREFIX))
        dest_bucket = storage_client.bucket(GCS_BUCKET)
        dest_blobs = list(dest_bucket.list_blobs(prefix=GCS_DEST_PREFIX))
        dest_files = set(blob.name for blob in dest_blobs if blob.name.lower().endswith('.pdf'))
        new_files = []
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                dest_path = blob.name.replace(GCS_SOURCE_PREFIX, GCS_DEST_PREFIX, 1)
                if dest_path not in dest_files:
                    new_files.append(blob.name)
        if new_files:
            print(f"[INFO] New files to process: {new_files}")
            logger.info(f"New files to process: {new_files}")
        else:
            print("[INFO] No new files to process.")
            logger.info("No new files to process.")
        return new_files
    except Exception as e:
        print(f"[FATAL][GCS_UTILS] Exception in list_new_files: {e}")
        logger.error(f"[GCS_UTILS] Exception in list_new_files: {e}")
        raise

def download_from_gcs(file_name, dest_dir, trace_id=None):
    print(f"[DEBUG] Downloading {file_name} from GCS to {dest_dir}")
    GCS_LIMITER.acquire()
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET)
        source_blob_name = gcs_path(GCS_SOURCE_PREFIX, file_name)
        print(f"[DEBUG] Source blob name: {source_blob_name}")
        blob = bucket.blob(source_blob_name)
        local_path = os.path.join(dest_dir, os.path.basename(file_name))
        blob.download_to_filename(local_path)
        print(f"[DEBUG] Downloaded to {local_path}")
        return local_path
    except Exception as e:
        print(f"[FATAL][GCS_UTILS] Exception in download_from_gcs: {e}")
        raise

def upload_to_gcs(file_path, dest_name=None, trace_id=None, if_generation_match=None):
    GCS_LIMITER.acquire()
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    dest_blob_name = gcs_path(GCS_DEST_PREFIX, dest_name or os.path.basename(file_path))
    blob = bucket.blob(dest_blob_name)
    if if_generation_match is not None:
        blob.upload_from_filename(file_path, if_generation_match=if_generation_match)
    else:
        blob.upload_from_filename(file_path)
    return True

# Batch existence check for future optimization
# Usage: batch_file_exists_in_dest([file1, file2, ...])
def batch_file_exists_in_dest(file_names):
    print(f"[DEBUG] Batch checking existence for {len(file_names)} files in dest bucket...")
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET)
    dest_blobs = set()
    for blob in bucket.list_blobs(prefix=GCS_DEST_PREFIX):
        dest_blobs.add(os.path.basename(blob.name))
    results = {fn: (fn in dest_blobs) for fn in file_names}
    print(f"[DEBUG] Batch existence check results: {results}")
    return results 