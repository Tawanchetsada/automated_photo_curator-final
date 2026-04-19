"""
tests/test_jobs.py — Integration tests for /jobs/* endpoints.

process_job is mocked throughout so no ML models are loaded and no
BackgroundTask fails during ASGI request handling.
"""

import io
import zipfile
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_login


# ── /jobs/upload ──────────────────────────────────────────────────────────────
async def test_upload_requires_auth(client: AsyncClient) -> None:
    """POST /jobs/upload without a token → 401."""
    zip_bytes = io.BytesIO(b"PK")  # minimal fake content
    resp = await client.post(
        "/jobs/upload",
        files={"zip_file": ("photos.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 401


async def test_upload_non_zip_rejected(client: AsyncClient) -> None:
    """Uploading a non-ZIP file → 400."""
    token = await register_and_login(client)
    resp = await client.post(
        "/jobs/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"zip_file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_zip_creates_job(client: AsyncClient) -> None:
    """Upload a valid ZIP → 202 with job_id and status='pending'."""
    token = await register_and_login(client)

    # Build a valid in-memory ZIP
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("photo1.jpg", b"fakejpeg1")
    buf.seek(0)

    # Mock process_job so the background task is a no-op
    with patch("app.routers.jobs.process_job"):
        resp = await client.post(
            "/jobs/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"zip_file": ("photos.zip", buf, "application/zip")},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert "job_id" in body
    assert body["status"] == "pending"
    assert "created_at" in body


# ── /jobs/history ─────────────────────────────────────────────────────────────
async def test_job_history_empty(client: AsyncClient) -> None:
    """GET /jobs/history for a new user → 200 with empty list."""
    token = await register_and_login(client)
    resp = await client.get(
        "/jobs/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


# ── /jobs/{job_id}/status ─────────────────────────────────────────────────────
async def test_job_status_not_found(client: AsyncClient) -> None:
    """GET /jobs/999/status for a non-existent job → 404."""
    token = await register_and_login(client)
    resp = await client.get(
        "/jobs/999/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
