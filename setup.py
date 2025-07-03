from setuptools import setup, find_packages
import os

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="dist-gcs-pdf-processing",
    version="0.1.0",
    author="Your Name",
    author_email="your@email.com",
    description="Distributed, scalable GCS PDF processing pipeline with Gemini OCR, Redis, and API endpoints.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/youruser/dist-gcs-pdf-processing",
    project_urls={
        "Source": "https://github.com/youruser/dist-gcs-pdf-processing",
        "Tracker": "https://github.com/youruser/dist-gcs-pdf-processing/issues",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "fastapi",
        "uvicorn",
        "google-cloud-storage",
        "requests",
        "python-dotenv",
        "pypdf",
        "markdown2",
        "weasyprint",
        "python-docx",
        "redis",
        "prometheus_client",
    ],
    include_package_data=True,
    python_requires=">=3.9",
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
) 