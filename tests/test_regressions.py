"""Regression tests for placeholders that lost their f-prefix in the
2025-09-14 lint pass (b46cc59), which made every file share one lock,
every split page share one path, and the Supabase header a literal string."""
import ast
import glob
import os
import re
from contextlib import contextmanager
from unittest.mock import patch

from pypdf import PdfReader, PdfWriter

import dist_gcs_pdf_processing.unified_worker as worker_mod
from dist_gcs_pdf_processing.unified_worker import (
    distributed_lock,
    split_pdf_to_pages,
)

SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "dist_gcs_pdf_processing")
PLACEHOLDER = re.compile(r"\{[a-zA-Z_][\w.\[\]()'\"+]*(:[^}]*)?\}")


def test_no_plain_string_contains_format_placeholder():
    offenders = []
    for path in glob.glob(os.path.join(SRC_DIR, "*.py")):
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        fstring_parts = {
            id(v) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for v in node.values
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in fstring_parts
                and PLACEHOLDER.search(node.value)
                and not node.value.lstrip().startswith(("{", "<"))
            ):
                offenders.append(f"{os.path.basename(path)}:{node.lineno}: {node.value[:60]!r}")
    assert not offenders, "string literals look like f-strings missing their f prefix:\n" + "\n".join(offenders)


def test_split_pdf_to_pages_writes_one_file_per_page(tmp_path):
    src = tmp_path / "in.pdf"
    writer = PdfWriter()
    for width in (72, 144, 216):  # distinct page sizes identify each page
        writer.add_blank_page(width=width, height=72)
    with open(src, "wb") as fh:
        writer.write(fh)

    pages = split_pdf_to_pages(str(src), str(tmp_path))

    assert len(set(pages)) == 3
    widths = [float(PdfReader(p).pages[0].mediabox.width) for p in pages]
    assert widths == [72, 144, 216]


def test_file_locks_for_different_keys_do_not_collide(monkeypatch, tmp_path):
    monkeypatch.setattr(worker_mod, "redis_client", None)
    monkeypatch.setattr(worker_mod, "LOGS_DIR", str(tmp_path))
    with distributed_lock("pdf_processing:a.pdf") as got_a:
        with distributed_lock("pdf_processing:b.pdf") as got_b:
            with distributed_lock("pdf_processing:a.pdf") as got_a_again:
                assert got_a and got_b
                assert not got_a_again


def test_process_file_with_resume_locks_per_file():
    seen = []

    @contextmanager
    def fake_lock(key, timeout=300):
        seen.append(key)
        yield False  # pretend another worker holds it; returns before any I/O

    with patch.object(worker_mod, "distributed_lock", fake_lock):
        worker_mod.process_file_with_resume("a.pdf", storage_backend=None)
        worker_mod.process_file_with_resume("b.pdf", storage_backend=None)

    assert seen == ["pdf_processing:a.pdf", "pdf_processing:b.pdf"]


class _BusyRedis:
    """Redis double whose key is always held by another worker."""

    def set(self, *args, **kwargs):
        return False


def test_redis_contention_does_not_fall_back_to_local_file_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(worker_mod, "redis_client", _BusyRedis())
    monkeypatch.setattr(worker_mod, "LOGS_DIR", str(tmp_path))
    with distributed_lock("pdf_processing:a.pdf") as got:
        assert not got
