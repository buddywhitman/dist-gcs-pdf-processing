import os
import threading
from fastapi import FastAPI, Request, HTTPException

from dist_gcs_pdf_processing.env import load_env_and_credentials

from dist_gcs_pdf_processing.worker import (
import logging
import uvicorn


    start_worker,
    cleanup_old_files
)
load_env_and_credentials()

os.environ["G_MESSAGES_DEBUG"] = "none"
os.environ["G_DEBUG"] = "fatal-warnings"
os.environ["PYTHONWARNINGS"] = "ignore"

app = FastAPI()

# Print GCS bucket and prefix values once at startup
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_SOURCE_PREFIX = os.environ.get("GCS_SOURCE_PREFIX")
GCS_DEST_PREFIX = os.environ.get("GCS_DEST_PREFIX")
print(f"[INFO] GCS_BUCKET: {GCS_BUCKET}")
print(f"[INFO] GCS_SOURCE_PREFIX: {GCS_SOURCE_PREFIX}")
print(f"[INFO] GCS_DEST_PREFIX: {GCS_DEST_PREFIX}")

# Start the worker in a background thread on startup
@app.on_event("startup")
def startup_event():
    logging.getLogger("dcpr.worker").info(
        "FastAPI startup: worker thread will be started."
    )
    threading.Thread(target=start_worker, daemon=True).start()

@app.get("/")
def health():
    return {"status": "ok"}

@app.get("/health")
def health_alias():
    return {"status": "ok"}

@app.post("/gcs-event")
async def gcs_event(request: Request):
    body = await request.json()
    event_files = body.get("files", [])
    handle_gcs_event(event_files)
    return {"status": "processing started", "files": event_files}

@app.get("/status")
def status():
    return {
        "status": "running",
        "max_concurrent_files": MAX_CONCURRENT_FILES,
        "gcs_bucket": GCS_BUCKET,
        "gcs_source_prefix": GCS_SOURCE_PREFIX,
        "gcs_dest_prefix": GCS_DEST_PREFIX
    }

@app.get("/logs")
def logs():
    log_file = os.path.join(os.path.dirname(__file__), "logs", "worker.log")
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            lines = f.readlines()
            return {"logs": lines[-50:]}  # Last 50 lines
    return {"logs": []}

@app.get("/metrics")
def metrics():
    return {
        "status": "ok",
        "max_concurrent_files": MAX_CONCURRENT_FILES,
        "gcs_bucket": GCS_BUCKET
    }

@app.get("/config")
def config():
    return {
        "gcs_bucket": GCS_BUCKET,
        "gcs_source_prefix": GCS_SOURCE_PREFIX,
        "gcs_dest_prefix": GCS_DEST_PREFIX,
        "max_concurrent_files": MAX_CONCURRENT_FILES
    }

@app.post("/process-file")
async def process_file(request: Request):
    body = await request.json()
    file_path = body.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="file_path is required")

    # Process the file
    handle_gcs_event([file_path])
    return {"status": "processing started", "file": file_path}

def main():
    uvicorn.run("dist_gcs_pdf_processing.main:app", host="0.0.0.0", port=8000)
