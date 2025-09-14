import os
from dist_gcs_pdf_processing.env import load_env_and_credentials

load_env_and_credentials()

# Google Cloud Storage configuration (legacy)
GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_SOURCE_PREFIX = os.getenv("GCS_SOURCE_PREFIX", "")
GCS_DEST_PREFIX = os.getenv("GCS_DEST_PREFIX", "")

# Google Drive configuration
DRIVE_SOURCE_FOLDER_ID = os.getenv("DRIVE_SOURCE_FOLDER_ID")
DRIVE_DEST_FOLDER_ID = os.getenv("DRIVE_DEST_FOLDER_ID")
GOOGLE_DRIVE_CREDENTIALS = os.getenv("GOOGLE_DRIVE_CREDENTIALS")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROMPT = os.getenv("GEMINI_PROMPT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
# Max number of documents to process in a batch
DOC_BATCH_SIZE = int(os.getenv("DOC_BATCH_SIZE", 10))
# Max parallel Gemini OCR for pages
PAGE_MAX_WORKERS = int(os.getenv("PAGE_MAX_WORKERS", 4))
# Max concurrent files being processed
MAX_CONCURRENT_FILES = int(os.getenv("MAX_CONCURRENT_FILES", 3))
# Max concurrent workers
MAX_CONCURRENT_WORKERS = int(os.getenv("MAX_CONCURRENT_WORKERS", 8))
# Global Gemini API concurrency limit
GEMINI_GLOBAL_CONCURRENCY = int(os.getenv("GEMINI_GLOBAL_CONCURRENCY", 10))
REDIS_URL = os.getenv("REDIS_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

STAGING_DIR = os.path.join(os.path.dirname(__file__), "staging")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "processed")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
