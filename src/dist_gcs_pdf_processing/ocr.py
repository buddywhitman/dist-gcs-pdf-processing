import os
import requests
import base64
from dist_gcs_pdf_processing.env import load_env_and_credentials

load_env_and_credentials()

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "processed")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROMPT = os.getenv("GEMINI_PROMPT")

# Placeholder Gemini API endpoint (replace with actual endpoint)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

def process_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    prompt_text = (
        "Extract text from a PDF page and convert it to Markdown format, preserving original formatting. "
        "Convert tables into Markdown tables with correct alignment and formatting. "
        "Translate Hindi to English with literal translation keeping only english equivalent. "
        "Create a well-formatted Markdown output that accurately represents the original PDF content. "
        "Must not include no note or comment and only include text extracted from PDF"
    )
    body = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {"inline_data": {
                    "mime_type": "application/pdf",
                    "data": pdf_b64
                }}
            ]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048
        }
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body)
    response.raise_for_status()
    # Save the processed file
    processed_path = os.path.join(PROCESSED_DIR, os.path.basename(pdf_path))
    with open(processed_path, "wb") as out:
        out.write(response.content)
    return processed_path

def gemini_ocr_page(pdf_path, page_number):
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    prompt_text = (
        "Extract text from a PDF page and convert it to Markdown format, preserving original formatting. "
        "Convert tables into Markdown tables with correct alignment and formatting. "
        "Translate Hindi to English with literal translation keeping only english equivalent. "
        "Create a well-formatted Markdown output that accurately represents the original PDF content. "
        "Must not include no note or comment and only include text extracted from PDF"
    )
    body = {
        "contents": [{
            "parts": [
                {"text": prompt_text},
                {"inline_data": {
                    "mime_type": "application/pdf",
                    "data": pdf_b64
                }}
            ]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 2048
        }
    }
    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}
    response = requests.post(GEMINI_API_URL, headers=headers, params=params, json=body)
    response.raise_for_status()
    # Parse the markdown from the response
    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return response.text 