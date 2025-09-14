# PDF Processing Pipeline

A comprehensive, scalable PDF processing system with support for Google Cloud Storage (GCS) and Google Drive backends, featuring resume capability, distributed locking, and production-ready deployment options.

## 🚀 Features

- **🔄 Resume Capability**: Can resume from where it left off after crashes or interruptions
- **⚡ Concurrent Processing**: File-level and page-level concurrency with intelligent backpressure
- **🗄️ Multi-Storage Backends**: Support for both GCS and Google Drive via pluggable storage interface
- **🔒 Distributed Locking**: Prevents duplicate processing across multiple instances
- **📊 Comprehensive Logging**: JSON logs, dead letter queue, and Supabase integration
- **✅ PDF Validation**: Validates PDF integrity before processing
- **🚦 Rate Limiting**: Global Gemini API throttling and storage operation limits
- **🛡️ Graceful Shutdown**: Proper cleanup on termination signals
- **🏥 Health Monitoring**: Built-in health checks and monitoring endpoints
- **📈 Auto-scaling**: Kubernetes HPA for dynamic scaling
- **🐳 Container Ready**: Docker and Kubernetes deployment configurations

## 🏗️ Architecture

The system consists of:

1. **Unified Worker**: Single worker supporting both GCS and Google Drive backends
2. **Storage Interface**: Pluggable storage abstraction layer
3. **OCR Engine**: Gemini API integration with intelligent rate limiting
4. **Resume System**: Persistent progress tracking and resume capability
5. **Distributed Locking**: Redis-based or file-based locking to prevent duplicates
6. **Comprehensive Logging**: Multi-output logging system with structured JSON logs
7. **Health Monitoring**: Built-in health checks and metrics endpoints

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Storage bucket OR Google Drive folders
- Gemini API key
- Service account credentials (GCS) OR OAuth2 credentials (Drive)
- Redis instance (for distributed locking)

### Installation

```bash
# Install from PyPI
pip install dist-gcs-pdf-processing==2.0.0

# Or install from source
git clone <repository-url>
cd gcs-pdf-processing
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Configuration

Create a `.env` file with your settings:

```env
# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Google Cloud Storage (for GCS backend)
GOOGLE_APPLICATION_CREDENTIALS=secrets/gcs-service-account.json
GCS_BUCKET_NAME=your-bucket-name
GCS_SOURCE_PREFIX=source/
GCS_DEST_PREFIX=processed/

# Google Drive (for Drive backend)
GOOGLE_DRIVE_CREDENTIALS=secrets/drive-oauth2-credentials.json
DRIVE_SOURCE_FOLDER_ID=your_source_folder_id
DRIVE_DEST_FOLDER_ID=your_dest_folder_id

# Redis (for distributed locking)
REDIS_URL=redis://localhost:6379/0

# Supabase (optional, for persistent error logging)
SUPABASE_URL=your_supabase_url
SUPABASE_API_KEY=your_supabase_api_key

# Worker Configuration
POLL_INTERVAL=30
MAX_CONCURRENT_FILES=3
MAX_CONCURRENT_WORKERS=8
GEMINI_GLOBAL_CONCURRENCY=10
MAX_RETRIES=3
```

## 🎯 Usage

### Local Development

```bash
# Run GCS worker
dist-gcs-worker

# Run Drive worker  
dist-drive-worker

# Run API server
dist-gcs-api
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Scale workers
docker-compose up -d --scale pdf-worker-gcs=3 --scale pdf-worker-drive=2
```

### Kubernetes Deployment

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/hpa.yaml
```

## 📁 Project Structure

```
├── src/dist_gcs_pdf_processing/
│   ├── unified_worker.py      # 🎯 Main unified worker
│   ├── storage_interface.py   # 🗄️ Storage abstraction layer
│   ├── gcs_utils.py          # ☁️ GCS operations
│   ├── drive_utils_oauth2.py # 📁 Drive operations
│   ├── ocr.py                # 🔍 OCR processing
│   ├── config.py             # ⚙️ Configuration
│   ├── env.py                # 🌍 Environment setup
│   └── shared.py             # 🔧 Shared utilities
├── k8s/                      # ☸️ Kubernetes manifests
├── docker-compose.yml        # 🐳 Docker Compose config
├── Dockerfile               # 🐳 Docker configuration
└── tests/                   # 🧪 Test suite
```

## 🔧 Configuration Options

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `STORAGE_BACKEND` | Storage backend (gcs/drive) | gcs | Determines which storage to use |
| `POLL_INTERVAL` | Polling interval in seconds | 30 | How often to check for new files |
| `MAX_CONCURRENT_FILES` | Max concurrent files | 3 | Files processed simultaneously |
| `MAX_CONCURRENT_WORKERS` | Max concurrent workers | 8 | Pages processed simultaneously |
| `GEMINI_GLOBAL_CONCURRENCY` | Global Gemini API concurrency | 10 | Global API rate limiting |
| `MAX_RETRIES` | Max retries per page | 3 | Retry failed pages |
| `REDIS_URL` | Redis connection URL | None | For distributed locking |
| `WORKER_INSTANCE_ID` | Unique worker instance ID | Auto-generated | For logging and locking |

## 📊 Monitoring & Logging

### Health Checks

- **Worker Health**: Checks for log file existence
- **API Health**: HTTP endpoint at `/health`
- **Redis Health**: Redis ping command

### Logging

- **Structured Logs**: JSON format in `logs/json/`
- **Dead Letter Queue**: Failed files in `logs/dead_letter/`
- **Progress Tracking**: Resume state in `logs/progress/`
- **Supabase Integration**: Persistent error logging

### Metrics

- **Prometheus Metrics**: Available at `/metrics` endpoint
- **Resource Usage**: CPU, memory, network
- **Processing Metrics**: Files processed, pages processed, errors

## 🚀 Deployment Options

### 1. Docker Compose (Recommended for Development)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale pdf-worker-gcs=3 --scale pdf-worker-drive=2

# Stop services
docker-compose down
```

### 2. Kubernetes (Recommended for Production)

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n pdf-processing

# View logs
kubectl logs -f deployment/pdf-worker-gcs -n pdf-processing

# Scale manually
kubectl scale deployment pdf-worker-gcs --replicas=5 -n pdf-processing
```

### 3. Individual Containers

```bash
# Run GCS worker
docker run -d \
  --name pdf-worker-gcs \
  --env-file .env \
  -v ./secrets:/app/secrets:ro \
  -v ./logs:/app/logs \
  pdf-worker:latest \
  dist-gcs-worker

# Run Drive worker
docker run -d \
  --name pdf-worker-drive \
  --env-file .env \
  -v ./secrets:/app/secrets:ro \
  -v ./logs:/app/logs \
  pdf-worker:latest \
  dist-drive-worker

# Run API server
docker run -d \
  --name pdf-api \
  --env-file .env \
  -p 8000:8000 \
  -v ./secrets:/app/secrets:ro \
  -v ./logs:/app/logs \
  pdf-worker:latest \
  dist-gcs-api
```

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis status
   kubectl get pods -l app=redis -n pdf-processing
   ```

2. **Authentication Errors**
   ```bash
   # Check secrets
   kubectl get secret pdf-worker-secrets -n pdf-processing -o yaml
   ```

3. **Duplicate Processing**
   ```bash
   # Check Redis locks
   redis-cli keys "pdf_processing:*"
   ```

### Debug Commands

```bash
# Check worker status
kubectl describe pod <pod-name> -n pdf-processing

# View logs
kubectl logs -f <pod-name> -n pdf-processing

# Execute shell in pod
kubectl exec -it <pod-name> -n pdf-processing -- /bin/bash
```

## 📈 Scaling Strategies

### Horizontal Scaling

1. **Kubernetes HPA**: Automatic scaling based on CPU/memory
2. **Manual Scaling**: `kubectl scale deployment`
3. **Docker Compose**: `docker-compose up --scale`

### Vertical Scaling

1. **Resource Limits**: Adjust CPU/memory limits
2. **Concurrency**: Increase `MAX_CONCURRENT_FILES`
3. **Workers**: Increase `MAX_CONCURRENT_WORKERS`

## 🛡️ Security Considerations

1. **Secrets Management**: Use Kubernetes secrets or external secret management
2. **Network Policies**: Implement network segmentation
3. **RBAC**: Configure proper role-based access control
4. **Image Security**: Scan images for vulnerabilities
5. **Resource Limits**: Prevent resource exhaustion attacks

## 🔧 Setup Guides

### Google Cloud Storage Setup

1. **Create a GCS Bucket**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to Cloud Storage
   - Create a new bucket
   - Note the bucket name

2. **Create Service Account**:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Provide name and description
   - Grant "Storage Admin" role
   - Create and download JSON key as `secrets/gcs-service-account.json`

3. **Configure Environment**:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=secrets/gcs-service-account.json
   GCS_BUCKET_NAME=your-bucket-name
   GCS_SOURCE_PREFIX=source/
   GCS_DEST_PREFIX=processed/
   ```

### Google Drive Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Google Drive API

2. **Create OAuth2 Credentials**:
   - Go to "Credentials" in the Google Cloud Console
   - Click "Create Credentials" → "OAuth 2.0 Client IDs"
   - Choose "Desktop application"
   - Download the JSON file as `secrets/drive-oauth2-credentials.json`

3. **Set up OAuth2 Flow**:
   ```bash
   # Run the OAuth2 setup (one-time)
   python -c "
   from dist_gcs_pdf_processing.drive_utils_oauth2 import setup_oauth2_credentials
   setup_oauth2_credentials()
   "
   ```

4. **Create Drive Folders**:
   - Create source and destination folders in Google Drive
   - Copy folder IDs from URLs
   - Configure environment:
   ```env
   GOOGLE_DRIVE_CREDENTIALS=secrets/drive-oauth2-credentials.json
   DRIVE_SOURCE_FOLDER_ID=your_source_folder_id
   DRIVE_DEST_FOLDER_ID=your_dest_folder_id
   ```

### Redis Setup

#### Local Redis
```bash
# Install Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

#### Docker Redis
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

#### Kubernetes Redis
```bash
kubectl apply -f k8s/redis-deployment.yaml
```

## 📚 API Reference

### Health Endpoints

- `GET /` - Basic health check
- `GET /health` - Detailed health status
- `GET /status` - Worker status and metrics
- `GET /metrics` - Prometheus metrics

### Processing Endpoints

- `POST /process-file` - Process a specific file
- `POST /drive-event` - Process files from Drive webhook
- `GET /logs` - Recent processing logs

### Configuration Endpoints

- `GET /config` - Current configuration
- `POST /config` - Update configuration (restart required)

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_worker.py

# Run with coverage
pytest --cov=src/dist_gcs_pdf_processing tests/

# Run integration tests
pytest tests/test_integration.py -v
```

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/buddywhitman/dist-gcs-pdf-processing/issues)
- **Discussions**: [GitHub Discussions](https://github.com/buddywhitman/dist-gcs-pdf-processing/discussions)
- **Documentation**: [Wiki](https://github.com/buddywhitman/dist-gcs-pdf-processing/wiki)

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and contribution instructions.