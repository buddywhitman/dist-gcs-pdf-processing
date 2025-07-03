import os
from dist_gcs_pdf_processing.env import load_env_and_credentials

load_env_and_credentials()

GCS_BUCKET = os.getenv("GCS_BUCKET")
GCS_SOURCE_PREFIX = os.getenv("GCS_SOURCE_PREFIX", "")
GCS_DEST_PREFIX = os.getenv("GCS_DEST_PREFIX", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROMPT = os.getenv("GEMINI_PROMPT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
DOC_BATCH_SIZE = int(os.getenv("DOC_BATCH_SIZE", 10))  # Max number of documents to process in a batch
PAGE_MAX_WORKERS = int(os.getenv("PAGE_MAX_WORKERS", 4))  # Max parallel Gemini OCR for pages
REDIS_URL = os.getenv("REDIS_URL")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 30))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

STAGING_DIR = os.path.join(os.path.dirname(__file__), "staging")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "processed")

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True) 