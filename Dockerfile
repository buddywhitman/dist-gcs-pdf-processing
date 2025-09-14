# Multi-stage build for PDF processing worker
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install WeasyPrint dependencies
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install the package in editable mode
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash worker
RUN chown -R worker:worker /app
USER worker

# Create necessary directories
RUN mkdir -p /app/logs/{json,dead_letter,progress,cache}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default environment variables
ENV PYTHONPATH=/app
ENV POLL_INTERVAL=30
ENV MAX_CONCURRENT_FILES=3
ENV MAX_CONCURRENT_WORKERS=8
ENV GEMINI_GLOBAL_CONCURRENCY=10
ENV MAX_RETRIES=3
ENV WORKER_INSTANCE_ID=worker-1

# Expose port for health checks
EXPOSE 8000

# Default command
CMD ["python", "-m", "dist_gcs_pdf_processing.unified_worker"]