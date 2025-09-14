# Contributing to PDF Processing Pipeline

Thank you for your interest in contributing to the PDF Processing Pipeline! This document provides guidelines and instructions for developers who want to contribute to the project.

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker (for testing)
- Redis (for distributed locking)
- Google Cloud credentials (for testing)

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/yourusername/dist-gcs-pdf-processing.git
   cd dist-gcs-pdf-processing
   ```

2. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

4. **Install Development Dependencies**:
   ```bash
   pip install pytest pytest-cov flake8 black isort mypy
   ```

5. **Set up Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

## 🏗️ Project Architecture

### Core Components

- **`unified_worker.py`**: Main worker logic with resume capability
- **`storage_interface.py`**: Abstract storage interface for GCS/Drive
- **`gcs_utils.py`**: Google Cloud Storage operations
- **`drive_utils_oauth2.py`**: Google Drive operations
- **`ocr.py`**: Gemini API integration
- **`config.py`**: Configuration management
- **`env.py`**: Environment variable handling
- **`shared.py`**: Shared utilities and rate limiting

### Key Design Patterns

- **Storage Interface**: Pluggable storage backends
- **Resume System**: Persistent progress tracking
- **Distributed Locking**: Redis-based with file fallback
- **Rate Limiting**: Global and per-service throttling
- **Error Handling**: Comprehensive logging and retry logic

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/dist_gcs_pdf_processing --cov-report=html

# Run specific test file
pytest tests/test_worker.py

# Run integration tests
pytest tests/test_integration.py -v

# Run with verbose output
pytest -v -s
```

### Test Structure

```
tests/
├── test_worker.py          # Worker functionality tests
├── test_integration.py     # End-to-end integration tests
├── test_gcs_utils.py       # GCS operations tests
├── test_ocr.py            # OCR processing tests
├── test_logging.py        # Logging system tests
├── test_utils.py          # Utility function tests
└── testdata/              # Test PDF files
```

### Writing Tests

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **Mock External Services**: Use mocks for APIs and storage
4. **Test Data**: Use small, representative test files

Example test:
```python
import pytest
from unittest.mock import Mock, patch
from dist_gcs_pdf_processing.unified_worker import process_file

def test_process_file_success():
    with patch('dist_gcs_pdf_processing.unified_worker.download_file') as mock_download:
        mock_download.return_value = "test.pdf"
        result = process_file("test.pdf")
        assert result is not None
```

## 🔧 Code Quality

### Code Style

We use the following tools for code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type check
mypy src/
```

### Code Standards

1. **Type Hints**: Use type hints for all function parameters and return values
2. **Docstrings**: Document all public functions and classes
3. **Error Handling**: Use specific exception types
4. **Logging**: Use structured logging with appropriate levels
5. **Naming**: Use descriptive variable and function names

Example:
```python
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

def process_pdf_file(
    file_path: str, 
    output_path: Optional[str] = None
) -> bool:
    """
    Process a PDF file through OCR pipeline.
    
    Args:
        file_path: Path to input PDF file
        output_path: Optional output path for processed file
        
    Returns:
        True if processing successful, False otherwise
        
    Raises:
        FileNotFoundError: If input file doesn't exist
        ProcessingError: If OCR processing fails
    """
    try:
        # Implementation here
        logger.info(f"Processing file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return False
```

## 🚀 Development Workflow

### Branch Strategy

1. **Main Branch**: `main` - Production-ready code
2. **Feature Branches**: `feature/description` - New features
3. **Bug Fix Branches**: `bugfix/description` - Bug fixes
4. **Hotfix Branches**: `hotfix/description` - Critical fixes

### Commit Guidelines

Use conventional commits:

```
feat: add resume capability for failed pages
fix: resolve Redis connection timeout issue
docs: update API documentation
test: add integration tests for Drive backend
refactor: extract common logging utilities
```

### Pull Request Process

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes**:
   - Write code following style guidelines
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Changes**:
   ```bash
   pytest
   flake8 src/ tests/
   mypy src/
   ```

4. **Commit Changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **Push and Create PR**:
   ```bash
   git push origin feature/new-feature
   # Create PR on GitHub
   ```

### PR Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] New functionality has tests
- [ ] Documentation updated
- [ ] No sensitive data in commits
- [ ] PR description explains changes

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Environment**: OS, Python version, package version
2. **Steps to Reproduce**: Clear, minimal steps
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Logs**: Relevant log output
6. **Screenshots**: If applicable

## 💡 Feature Requests

When requesting features, please include:

1. **Use Case**: Why is this feature needed?
2. **Proposed Solution**: How should it work?
3. **Alternatives**: Other approaches considered
4. **Implementation**: Technical details if known

## 🔧 Development Tools

### IDE Setup

**VS Code**:
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.sortImports.args": ["--profile", "black"]
}
```

**PyCharm**:
- Configure Python interpreter to use venv
- Enable Black formatter
- Configure flake8 inspection
- Set up pytest runner

### Debugging

```bash
# Run with debug logging
LOG_LEVEL=DEBUG dist-gcs-worker

# Run specific test with debug
pytest tests/test_worker.py -v -s --log-cli-level=DEBUG

# Debug with pdb
python -m pdb -m dist_gcs_pdf_processing.unified_worker
```

### Performance Profiling

```bash
# Profile memory usage
python -m memory_profiler src/dist_gcs_pdf_processing/unified_worker.py

# Profile CPU usage
python -m cProfile -o profile.stats src/dist_gcs_pdf_processing/unified_worker.py
```

## 📚 Documentation

### Code Documentation

- Use docstrings for all public functions
- Include type hints
- Document complex algorithms
- Add inline comments for non-obvious code

### API Documentation

- Update README.md for user-facing changes
- Document new configuration options
- Update deployment guides for infrastructure changes

### Internal Documentation

- Document design decisions in code comments
- Update architecture diagrams
- Document testing strategies

## 🚀 Release Process

### Version Bumping

1. **Patch**: Bug fixes (1.0.0 → 1.0.1)
2. **Minor**: New features (1.0.0 → 1.1.0)
3. **Major**: Breaking changes (1.0.0 → 2.0.0)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Version bumped in pyproject.toml
- [ ] CHANGELOG.md updated
- [ ] Release notes prepared
- [ ] PyPI upload tested

## 🤝 Community Guidelines

### Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the golden rule

### Getting Help

- Check existing issues and discussions
- Ask questions in GitHub Discussions
- Join our community chat (if available)
- Read the documentation thoroughly

## 📞 Contact

- **Maintainer**: [Your Name](mailto:your.email@example.com)
- **Issues**: [GitHub Issues](https://github.com/youruser/dist-gcs-pdf-processing/issues)
- **Discussions**: [GitHub Discussions](https://github.com/youruser/dist-gcs-pdf-processing/discussions)

Thank you for contributing to the PDF Processing Pipeline! 🎉
