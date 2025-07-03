import os
from unittest.mock import patch, MagicMock
from dist_gcs_pdf_processing.gcs_utils import *

def test_gcs_path():
    assert gcs_path("a", "b/c") == "a/b/c"
    assert gcs_path("/a/", "/b/", "c/") == "a/b/c"
    assert gcs_path() == ""

@patch("google.cloud.storage.Client")
def test_file_exists_in_dest(mock_client):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.exists.return_value = True
    mock_bucket.blob.return_value = mock_blob
    mock_client.return_value.bucket.return_value = mock_bucket
    assert file_exists_in_dest("file.pdf")
    mock_blob.exists.return_value = False
    assert not file_exists_in_dest("file.pdf")

@patch("dist_gcs_pdf_processing.gcs_utils.file_exists_in_dest", return_value=False)
@patch("google.cloud.storage.Client")
def test_list_new_files(mock_client, mock_exists):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_blob.name = "file.pdf"
    mock_bucket.list_blobs.return_value = [mock_blob]
    mock_client.return_value.bucket.return_value = mock_bucket
    files = list_new_files()
    assert files == ["file.pdf"]

@patch("google.cloud.storage.Client")
def test_download_from_gcs(mock_client, tmp_path):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client.return_value.bucket.return_value = mock_bucket
    dest_dir = tmp_path
    file_name = "file.pdf"
    mock_blob.download_to_filename.side_effect = lambda path: open(path, "wb").write(b"pdf")
    out_path = download_from_gcs(file_name, dest_dir)
    assert os.path.exists(out_path)

@patch("google.cloud.storage.Client")
def test_upload_to_gcs(mock_client, tmp_path):
    mock_bucket = MagicMock()
    mock_blob = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client.return_value.bucket.return_value = mock_bucket
    file_path = tmp_path / "file.pdf"
    file_path.write_bytes(b"pdf")
    assert upload_to_gcs(str(file_path)) 