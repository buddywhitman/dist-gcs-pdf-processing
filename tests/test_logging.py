import os
import tempfile
import json
from unittest.mock import patch
from src.worker import log_json, log_dead_letter, log_supabase_error

def test_log_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_json("event", "msg", extra={"foo": 1}, trace_id="abc", json_dir=tmpdir)
        files = os.listdir(tmpdir)
        assert files
        with open(os.path.join(tmpdir, files[0]), "r", encoding="utf-8") as f:
            lines = f.readlines()
            entry = json.loads(lines[0])
            assert entry["event_type"] == "event"
            assert entry["message"] == "msg"
            assert entry["extra"]["foo"] == 1
            assert entry["trace_id"] == "abc"

def test_log_dead_letter():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dead_letter("file.pdf", "err", trace_id="abc", extra={"bar": 2})
        # log_dead_letter always writes to DEAD_LETTER_DIR, so just check file exists
        # (could patch DEAD_LETTER_DIR for more isolation)
        # For now, just check the file is created
        assert os.path.exists(os.path.join("src", "logs", "dead_letter", "dead_letter.log"))

@patch("src.worker.requests.post")
def test_log_supabase_error(mock_post):
    mock_post.return_value.status_code = 201
    mock_post.return_value.raise_for_status = lambda: None
    log_supabase_error("errormsg", created_time="2024-01-01T00:00:00Z")
    assert mock_post.called 