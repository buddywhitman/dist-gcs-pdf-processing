# GCS PDF Processing Pipeline

## Overview
This service processes PDFs from a Google Cloud Storage (GCS) bucket, performs OCR using the Gemini API, and uploads clean, text-based PDFs to a destination GCS folder. It features robust error handling, logging, monitoring, and is designed for scalable, production use. Translates multilingual documents to english by default, and processes tables into relevant markdown syntax.

---

## Setup & Environment

1. **Clone the repository and navigate to the project root:**
   ```sh
   git clone <repo-url>
   cd nest-starters
   ```

2. **Install dependencies and the package:**
   ```sh
   pip install -r requirements.txt
   pip install .
   ```

3. **Environment Variables:**
   - Place your `.env` file in the `secrets/` directory at the project root.
   - Example `.env` variables:
     ```env
     GCS_BUCKET=your-bucket-name
     GCS_SOURCE_PREFIX=source-folder
     GCS_DEST_PREFIX=dest-folder
     GEMINI_API_KEY=your-gemini-api-key
     SUPABASE_URL=https://your-supabase-url
     SUPABASE_API_KEY=your-supabase-api-key
     MAX_RETRIES=3
     GEMINI_GLOBAL_CONCURRENCY=10
     MAX_CONCURRENT_FILES=3
     PAGE_MAX_WORKERS=5
     DOC_BATCH_SIZE=10
     MAX_QUEUE=100
     POLL_INTERVAL=30
     G_MESSAGES_DEBUG=none
     G_DEBUG=fatal-warnings
     ```

---

## Running as a pip-installed Package

After installing the package with `pip install .`, you can use the following console scripts from anywhere:

### Run the Worker (background processing)
```sh
dist-gcs-worker
```
- This will start the background worker that processes files from GCS.

### Run the FastAPI API Server
```sh
dist_gcs_pdf_processing
```
- This will start the FastAPI server (with the worker running in the background).
- You can override the port (default 8000):
  ```sh
  dist_gcs_pdf_processing 8080
  ```

### Run the API app directly (ASGI app, for advanced users)
```sh
uvicorn dist_gcs_pdf_processing.main:app --reload
```
- This runs the FastAPI app directly (no worker thread). The ASGI app is always `app` in `main.py`.

---

## Logging & Monitoring
- **Logs:**
  - Human-readable logs: `/logs/worker.log` (daily rotation)
  - JSON logs: `/logs/json/YYYY-MM-DD.json`
  - Dead letter logs: `/logs/dead_letter/dead_letter.log`
- **Supabase:**
  - Persistent errors are logged to the `Activity_Error_Log` table for monitoring.
- **Suppressing GTK/GLib output:**
  - Set in `.env` and at the top of `main.py` and `worker.py`.

---

## Error Handling
- Retries for transient errors (network, quota, etc.) with configurable limits.
- Per-page retries: Each page is retried up to `MAX_RETRIES` times before being skipped.
- Per-file retries: If a file fails (e.g., page count mismatch), the whole file is retried up to `MAX_RETRIES` times.
- All persistent errors are logged to file, JSON, dead letter, and Supabase.

---

## Scalability, Concurrency & Throttling
- **Rolling Concurrency Model:**
  - The worker always keeps up to `MAX_CONCURRENT_FILES` files in progress.
  - As soon as a file finishes, the next available file is picked up, until all are processed.
  - This ensures maximum throughput and efficient resource usage.
- **Per-Page Concurrency:**
  - Each file's pages are OCRed in parallel, up to `PAGE_MAX_WORKERS` at a time.
- **Global Gemini API Throttling:**
  - All Gemini API requests (across all files and pages) are globally throttled by `GEMINI_GLOBAL_CONCURRENCY`.
  - This ensures you never exceed your API quota or rate limits.
- **Backpressure:**
  - If too many files are queued (`MAX_QUEUE`), the worker will pause and log a warning.
- **Horizontal scaling:**
  - Run multiple stateless worker instances on different machines/VMs for even more throughput.

---

## Temp/Log Cleanup
- Files in logs, logs/json, logs/dead_letter, staging, and processed older than 200 days are deleted before the worker starts.

---

## Tests
- Unit and integration tests are located in `/tests`.
- Tests cover:
  - PDF splitting/merging
  - Per-page and per-file retry logic
  - File-level rolling concurrency (ensuring the concurrency window is always full)
  - Global Gemini API throttling
  - Trace ID propagation in logs
- To run tests:
  ```sh
  pytest
  ```

---

## CI/CD
- GitHub Actions workflow runs linting and tests on every push.
- Example workflow file: `.github/workflows/ci.yml`.

---

## Additional Notes
- All print/log statements are also written to log files.
- Trace/request IDs are used for end-to-end traceability.
- For any persistent errors, check Supabase and the dead letter log for details.

# Project Structure

```
project-root/
├── src/                # All main code (import as src.module)
├── tests/              # All tests (import as from src.module import ...)
├── logs/               # Log output
├── secrets/            # Secrets and credentials
│   └── your-service-account.json
│   └── .env
├── requirements.txt    # Python dependencies
├── setup.py            # For pip install -e .
├── Dockerfile
├── README.md
```

## Local Development

1. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   pip install .
   ```

2. **Run the worker:**
   ```sh
   dist-gcs-worker
   # or, for the API server:
   dist_gcs_pdf_processing
   ```

3. **Run tests:**
   ```sh
   pytest --import-mode=importlib tests/
   # or, if you have trouble with imports:
   PYTHONPATH=. pytest tests/
   ```

## Docker Usage

1. **Build the Docker image:**
   ```sh
   docker build -t nest-starters .
   ```

2. **Run the container (worker only):**
   ```sh
   docker run --rm -it -v $PWD/logs:/app/logs nest-starters dist-gcs-worker
   ```

3. **Run the container (API server):**
   ```sh
   docker run --rm -it -v $PWD/logs:/app/logs -p 8000:8000 nest-starters dist_gcs_pdf_processing
   ```

- The Dockerfile can be overridden to run either the worker or the API server.
- The `.dockerignore` file ensures your build context is clean and fast.
- You can override the CMD to run tests or other scripts as needed:
   ```sh
   docker run --rm -it nest-starters python -m pytest --import-mode=importlib tests/
   ```

## Continuous Integration (CI)

- Use GitHub Actions or similar CI to run:
  ```yaml
  - name: Install deps
    run: |
      pip install -r requirements.txt
      pip install .
  - name: Run tests
  ```

## Secrets and Environment Variables

- Place your GCP credentials JSON file in a `secrets/` directory at the project root (not tracked by git).
- In your `.env` file (in the `secrets/` directory), set:
  ```
  GOOGLE_APPLICATION_CREDENTIALS=secrets/your-service-account.json
  ```
- The worker will automatically load `.env` from `secrets/`.
- For Docker/CI, mount the `secrets/` directory and ensure the `.env` file and credentials are present.
- **Never commit secrets or credentials to version control!**

---

## Installation

You can install the package from a GitHub Release:

```sh
pip install https://github.com/youruser/dist-gcs-pdf-processing/releases/download/v0.1.0/dist_gcs_pdf_processing-0.1.0-py3-none-any.whl
```

---

## CLI Usage

After installation, you can run:

```sh
dist-gcs-worker  # Start the background worker

dist-gcs-api     # Start the FastAPI API server (with all endpoints)
```

Or, for advanced usage:

```sh
python -m dist_gcs_pdf_processing.worker
python -m dist_gcs_pdf_processing.main
```
