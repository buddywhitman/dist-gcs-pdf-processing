from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time

from .gcs_utils import (
    download_from_gcs,
    upload_to_gcs,
    list_new_files as gcs_list_new_files,
    file_exists_in_dest as gcs_file_exists
)
from .drive_utils_oauth2 import (
    download_from_drive,
    upload_to_drive,
    list_new_files as drive_list_new_files,
    file_exists_in_dest as drive_file_exists
)

"""
Abstract storage interface for pluggable storage backends.
Allows switching between GCS and Google Drive without changing worker logic.
"""
class StorageInterface(ABC):
    """Abstract interface for storage operations."""

    @abstractmethod
    def list_new_files(self) -> List[str]:
        """List new files to process. Returns list of file names."""
        pass

    @abstractmethod
    def download_file(self, file_name: str, local_path: str, trace_id: Optional[str] = None) -> bool:
        """Download a file to local path. Returns True if successful."""
        pass

    @abstractmethod
    def upload_file(self, local_path: str, file_name: str, trace_id: Optional[str] = None, if_generation_match: int = 0) -> bool:
        """Upload a file from local path. Returns True if successful."""
        pass

    @abstractmethod
    def file_exists(self, file_name: str, trace_id: Optional[str] = None) -> bool:
        """Check if file exists in destination. Returns True if exists."""
        pass

class GCSStorage(StorageInterface):
    """GCS storage implementation."""

    def __init__(self):
        self._list_new_files = gcs_list_new_files
        self._download_file = download_from_gcs
        self._upload_file = upload_to_gcs
        self._file_exists = file_exists_in_dest

    def list_new_files(self) -> List[str]:
        return self._list_new_files()

    def download_file(self, file_name: str, local_path: str, trace_id: Optional[str] = None) -> bool:
        return self._download_file(file_name, local_path, trace_id)

    def upload_file(self, local_path: str, file_name: str, trace_id: Optional[str] = None, if_generation_match: int = 0) -> bool:
        return self._upload_file(local_path, file_name, trace_id, if_generation_match)

    def file_exists(self, file_name: str, trace_id: Optional[str] = None) -> bool:
        return self._file_exists(file_name, trace_id)

class DriveStorage(StorageInterface):
    """Google Drive storage implementation."""

    def __init__(self):
        self._list_new_files = drive_list_new_files
        self._download_file = download_from_drive
        self._upload_file = upload_to_drive
        self._file_exists = file_exists_in_dest
        self._file_cache = {}  # Cache file info by name
        self._last_list_time = 0
        self._cache_ttl = 30  # Cache for 30 seconds

    def list_new_files(self) -> List[str]:
        current_time = time.time()

        # Use cache if it's fresh enough
        if (current_time - self._last_list_time < self._cache_ttl and
                self._file_cache):
            return list(self._file_cache.keys())

        # Fetch fresh data
        files = self._list_new_files()
        self._file_cache = {f['name']: f for f in files}
        self._last_list_time = current_time
        return list(self._file_cache.keys())

    def download_file(self, file_name: str, local_path: str, trace_id: Optional[str] = None) -> bool:
        # Get file info from cache
        if file_name not in self._file_cache:
            # Refresh cache if file not found
            self.list_new_files()

        file_info = self._file_cache.get(file_name)
        if not file_info:
            return False
        return self._download_file(file_info['id'], local_path, trace_id)

    def upload_file(self, local_path: str, file_name: str, trace_id: Optional[str] = None, if_generation_match: int = 0) -> bool:
        return self._upload_file(local_path, file_name, trace_id)

    def file_exists(self, file_name: str, trace_id: Optional[str] = None) -> bool:
        return self._file_exists(file_name, trace_id)

def get_storage_backend(backend_type: str = None) -> StorageInterface:
    """Get storage backend based on type or environment."""
    if backend_type is None:
        backend_type = os.getenv("STORAGE_BACKEND", "gcs")

    if backend_type.lower() == "drive":
        return DriveStorage()
    else:
        return GCSStorage()
