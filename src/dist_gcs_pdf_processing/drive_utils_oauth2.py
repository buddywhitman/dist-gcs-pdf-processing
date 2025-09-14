"""
Google Drive utilities for file operations using OAuth2 authentication.
Replaces GCS functionality with Google Drive API.
"""
import os
import time
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import pickle
from .config import (
    DRIVE_SOURCE_FOLDER_ID,
    DRIVE_DEST_FOLDER_ID,
    STAGING_DIR,
    PROCESSED_DIR)
from .shared import DRIVE_LIMITER

logger = logging.getLogger("dcpr.worker")

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive']

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

class DriveService:
    """Singleton class to manage Google Drive API service."""
    _instance = None
    _service = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DriveService, cls).__new__(cls)
        return cls._instance

    def get_service(self):
        """Get authenticated Google Drive service using OAuth2."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('drive', 'v3', credentials=creds)
        return self._service

    def _get_credentials(self):
        """Get OAuth2 credentials."""
        creds = None

        # Check if we have stored credentials
        token_file = (
            os.path.join(os.path.dirname(__file__), '..', '..', 'token.pick
            le'))
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("Refreshing expired OAuth2 credentials...")
                creds.refresh(Request())
            else:
                print("Starting OAuth2 flow for Google Drive...")
                credentials_file = (
                    os.path.join(os.path.dirname(__file__), '..', '..', 'cr
                    edentials.json'))
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError("OAuth2 credentials file not found: {credentials_file}")

                flow = (
                    InstalledAppFlow.from_client_secrets_file(credentials_f
                    ile, SCOPES))
                creds = (
                    flow.run_local_server(port=0)  # Let it choose any avai
                    lable port)

            # Save the credentials for the next run
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

        return creds

def get_drive_service():
    """Get Google Drive service instance."""
    return DriveService().get_service()

def list_new_files(trace_id=None):
    """
    List new PDF files in the source folder that are not in the destination folder.

    Args:
        trace_id: Optional trace ID for logging

    Returns:
        List of file dictionaries with 'id' and 'name' keys
    """
    try:
        service = get_drive_service()
        new_files = []

        print("[DEBUG][DRIVE_UTILS] Source folder ID: {DRIVE_SOURCE_FOLDER_ID}")
        print("[DEBUG][DRIVE_UTILS] Destination folder ID: {DRIVE_DEST_FOLDER_ID}")

        # Query for PDF files in source folder
        source_query = (
            "parents in '{DRIVE_SOURCE_FOLDER_ID}' and name contains '.pd' 
            and trashed=false")
        print("[DEBUG][DRIVE_UTILS] Source query: {source_query}")

        source_results = service.files().list(
            q=source_query,
            fields="files(id, name, mimeType)"
        ).execute()
        source_files = source_results.get('files', [])
        print("[DEBUG][DRIVE_UTILS] Found {len(source_files)} files in source folder:")
        for file in source_files:
            print("[DEBUG][DRIVE_UTILS]   - {file['name']} (ID: {file['id']}, MIME: {file.get('mimeType', 'unknown')})")

        # Query for PDF files in destination folder
        dest_query = (
            "parents in '{DRIVE_DEST_FOLDER_ID}' and name contains '.pd' an
            d trashed=false")
        print("[DEBUG][DRIVE_UTILS] Destination query: {dest_query}")

        dest_results = service.files().list(
            q=dest_query,
            fields="files(id, name, mimeType)"
        ).execute()
        dest_files = dest_results.get('files', [])
        print("[DEBUG][DRIVE_UTILS] Found {len(dest_files)} files in destination folder:")
        for file in dest_files:
            print("[DEBUG][DRIVE_UTILS]   - {file['name']} (ID: {file['id']}, MIME: {file.get('mimeType', 'unknown')})")

        # Find files that are in source but not in destination
        dest_file_names = {file['name'] for file in dest_files}
        for file in source_files:
            if file['name'] not in dest_file_names:
                new_files.append(file)
                print("[DEBUG][DRIVE_UTILS] New file found: {file['name']}")

        print("[DEBUG][DRIVE_UTILS] No new files found to process")
        return new_files

    except Exception as e:
        print("[FATAL][DRIVE_UTILS] Exception in list_new_files: {e}")
        logger.error("Exception in list_new_files: {e}")
        raise

def download_from_drive(file_id, local_path, trace_id=None):
    """
    Download a file from Google Drive.

    Args:
        file_id: Google Drive file ID
        local_path: Local path to save the file
        trace_id: Optional trace ID for logging

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        service = get_drive_service()

        # Get file metadata
        file_metadata = service.files().get(fileId=file_id).execute()
        file_name = file_metadata.get('name', 'unknown')

        print("[DEBUG][DRIVE_UTILS] Downloading {file_name} to {local_path}")

        # Download file content
        request = service.files().get_media(fileId=file_id)
        file_handle = io.BytesIO()
        downloader = MediaIoBaseDownload(file_handle, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
            if trace_id:
                print("[DEBUG][DRIVE_UTILS] Download progress: {int(status.progress() * 100)}%")

        # Save to local file
        with open(local_path, 'wb') as f:
            f.write(file_handle.getvalue())

        print("[DEBUG][DRIVE_UTILS] Successfully downloaded {file_name}")
        return True

    except Exception as e:
        print("[ERROR][DRIVE_UTILS] Failed to download file {file_id}: {e}")
        logger.error("Failed to download file {file_id}: {e}")
        return False

def upload_to_drive(local_path, file_name, trace_id=None):
    """
    Upload a file to Google Drive destination folder with chunked upload for large files.

    Args:
        local_path: Local path of the file to upload
        file_name: Name for the file in Drive
        trace_id: Optional trace ID for logging

    Returns:
        str: Google Drive file ID if successful, None otherwise
    """
    try:
        service = get_drive_service()

        # Check if file already exists
        if file_exists_in_dest(file_name, trace_id):
            print("[DEBUG][DRIVE_UTILS] File {file_name} already exists in destination, skipping upload")
            return "exists"

        # Get file size
        file_size = os.path.getsize(local_path)
        print("[DEBUG][DRIVE_UTILS] Uploading {file_name} ({file_size:,} bytes) to Drive folder {DRIVE_DEST_FOLDER_ID}")

        # Create file metadata
        file_metadata = {
            'name': file_name,
            'parents': [DRIVE_DEST_FOLDER_ID]
        }

        # Use chunked upload for files larger than 5MB
        if file_size > 5 * 1024 * 1024:  # 5MB
            print("[DEBUG][DRIVE_UTILS] Using chunked upload for large file ({file_size:,} bytes)")
            media = MediaFileUpload(
                local_path,
                mimetype='application/pd',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )

            # Create resumable upload session
            request = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )

            # Execute with retry logic
            file_id = None
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    print("[DEBUG][DRIVE_UTILS] Upload attempt {attempt + 1}/{max_retries}")
                    response = None
                    while response is None:
                        status, response = request.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            print("[DEBUG][DRIVE_UTILS] Upload progress: {progress}%")

                    if response:
                        file_id = response.get('id')
                        print("[DEBUG][DRIVE_UTILS] Successfully uploaded {file_name} with ID: {file_id}")
                        break

                except Exception as e:
                    print("[WARNING][DRIVE_UTILS] Upload attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(2 ** attempt)  # Exponential backoff

        else:
            # Use simple upload for small files
            print("[DEBUG][DRIVE_UTILS] Using simple upload for small file ({file_size:,} bytes)")
            media = MediaFileUpload(local_path, mimetype='application/pd')
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            file_id = file.get('id')
            print("[DEBUG][DRIVE_UTILS] Successfully uploaded {file_name} with ID: {file_id}")

        return file_id

    except Exception as e:
        print("[ERROR][DRIVE_UTILS] Failed to upload file {file_name}: {e}")
        logger.error("Failed to upload file {file_name}: {e}")
        return None

def file_exists_in_dest(file_name, trace_id=None):
    """
    Check if a file exists in the destination folder.

    Args:
        file_name: Name of the file to check
        trace_id: Optional trace ID for logging

    Returns:
        bool: True if file exists, False otherwise
    """
    try:
        service = get_drive_service()

        query = (
            "parents in '{DRIVE_DEST_FOLDER_ID}' and name='{file_name}' and
             trashed=false")
        results = (
            service.files().list(q=query, fields="files(id, name)").execute
            ())
        files = results.get('files', [])

        exists = len(files) > 0
        print("[DEBUG][DRIVE_UTILS] File {file_name} exists in destination: {exists}")
        return exists

    except Exception as e:
        print("[ERROR][DRIVE_UTILS] Error checking if file exists: {e}")
        logger.error("Error checking if file exists: {e}")
        return False
