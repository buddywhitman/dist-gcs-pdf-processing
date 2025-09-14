from dist_gcs_pdf_processing.env import load_env_and_credentials
load_env_and_credentials()

import os
from dotenv import load_dotenv
os.environ["G_MESSAGES_DEBUG"] = "none"
os.environ["G_DEBUG"] = "fatal-warnings"
os.environ["PYTHONWARNINGS"] = "ignore"
from fastapi import FastAPI, Request, HTTPException
from dist_gcs_pdf_processing.worker import start_worker, handle_gcs_event, MAX_CONCURRENT_FILES
import threading
import json

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
    import logging
    logging.getLogger("dcpr.worker").info("FastAPI startup: worker thread will be started.")
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
    # Dummy values; wire up to real worker state if available
    return {
        "active_workers": 0,  # Could be wired to worker.get_active_worker_count()
        "queue_length": 0,    # Could be wired to a global queue if implemented
        "max_concurrent_files": MAX_CONCURRENT_FILES,
        "status": "running"
    }

@app.get("/logs")
def logs():
    log_path = os.path.join(os.path.dirname(__file__), "logs", "worker.log")
    if not os.path.exists(log_path):
        return {"logs": "No logs found."}
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[-50:]  # Tail last 50 lines
    return {"logs": "".join(lines)}

@app.get("/metrics")
def metrics():
    # Dummy metrics; wire up to real counters if available
    return {
        "files_processed": 0,
        "errors": 0,
        "active_workers": 0
    }

@app.post("/process-file")
async def process_file_endpoint(request: Request):
    body = await request.json()
    file_name = body.get("file")
    if not file_name:
        raise HTTPException(status_code=400, detail="Missing 'file' in request body.")
    # Start processing the file in a background thread
    threading.Thread(target=handle_gcs_event, args=([file_name],), daemon=True).start()
    return {"status": "processing started", "file": file_name}

@app.get("/config")
def config():
    # Return a subset of environment/config variables
    keys = [
        "GCS_BUCKET", "GCS_SOURCE_PREFIX", "GCS_DEST_PREFIX", "GEMINI_API_KEY",
        "MAX_RETRIES", "GEMINI_GLOBAL_CONCURRENCY", "MAX_CONCURRENT_FILES",
        "PAGE_MAX_WORKERS", "DOC_BATCH_SIZE", "MAX_QUEUE", "POLL_INTERVAL"
    ]
    config = {k: os.getenv(k) for k in keys}
    return config

def main():
    import uvicorn
    uvicorn.run("dist_gcs_pdf_processing.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main() 