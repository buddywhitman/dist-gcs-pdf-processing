import sys
import uvicorn

# dist_gcs_pdf_processing package

def main():
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except Exception:
            print(f"[WARN] Invalid port argument: {sys.argv[1]}")
    uvicorn.run("dist_gcs_pdf_processing.main:app", host="0.0.0.0",
                port=port, reload=True)
