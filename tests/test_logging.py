import os
import tempfile
import json
from unittest.mock import patch

from dist_gcs_pdf_processing.unified_worker import (

    log_json, log_dead_letter, log_supabase_error
)

def test_log_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_json("event", "msg", extra={"foo": 1}, trace_id="abc", json_dir=tmpdir)
        files = os.listdir(tmpdir)
        assert len(files) == 1
        with open(os.path.join(tmpdir, files[0]), 'r') as f:
            data = json.load(f)
        assert data['event_type'] == "event"
        assert data['message'] == "msg"
        assert data['extra']['foo'] == 1
        assert data['trace_id'] == "abc"

def test_log_dead_letter():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dead_letter("error", "test error", extra={"error": "test"}, dead_letter_dir=tmpdir)
        files = os.listdir(tmpdir)
        assert len(files) == 1
        with open(os.path.join(tmpdir, files[0]), 'r') as f:
            data = json.load(f)
        assert data['file_name'] == "error"
        assert data['error'] == "test error"

@patch('requests.post')
@patch.dict(os.environ, {'SUPABASE_URL': 'http://test.com', 'SUPABASE_API_KEY': 'test_key'})
def test_log_supabase_error(mock_post):
    mock_post.return_value.status_code = 200
    log_supabase_error("test error")
    mock_post.assert_called_once()
