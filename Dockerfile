FROM python:3.11-slim

WORKDIR /app

# Install GTK and WeasyPrint dependencies
RUN apt-get update && apt-get install -y \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libxml2 \
    libgdk-pixbuf2.0-dev \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Add GTK bin to PATH (for good measure, though system install usually suffices)
ENV PATH="/usr/bin:/usr/local/bin:$PATH"

COPY requirements.txt setup.py ./
COPY src/ ./src/
COPY logs/ ./logs/
COPY tests/ ./tests/

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -e .

# Install uvicorn for FastAPI API server
RUN pip install uvicorn

# Copy secrets directory (for local dev; recommend mounting in prod)
COPY secrets/ ./secrets/

# Entrypoint selection: worker or API
# Use SERVICE_MODE=api to run the FastAPI app, or default to worker
ENV SERVICE_MODE=worker

CMD ["/bin/sh", "-c", "if [ \"$SERVICE_MODE\" = 'api' ]; then uvicorn src.main:app --host 0.0.0.0 --port 8000; else python src/worker.py; fi"] 