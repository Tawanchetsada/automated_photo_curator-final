"""
utils/api_client.py — HTTP client wrapper for the Photo Curator FastAPI backend.

Reads BACKEND_URL from the environment (default: http://localhost:8000).
All public methods raise ``Exception`` with the API's ``detail`` message on
HTTP errors so callers can surface them directly via ``st.error()``.
JWT token is read from / written to ``st.session_state["token"]``.
"""

import os

import requests
import streamlit as st

# Base URL — set BACKEND_URL env var in Docker / production
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")


def _raise_for_status(resp: requests.Response) -> None:
    """Raise Exception with the API ``detail`` field if the response is not 2xx."""
    if not resp.ok:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise Exception(detail)


class ApiClient:
    """Thin HTTP client for the Photo Curator FastAPI backend."""

    def __init__(self) -> None:
        self.base_url = BACKEND_URL

    # ── Internal helpers ──────────────────────────────────────────────────────
    def _auth_headers(self) -> dict[str, str]:
        token: str = st.session_state.get("token", "")
        return {"Authorization": f"Bearer {token}"} if token else {}

    @staticmethod
    def _file_tuple(uploaded_file, mime: str | None = None):
        """Convert a Streamlit UploadedFile to a (name, bytes, mime) tuple."""
        return (
            uploaded_file.name,
            uploaded_file.getvalue(),
            mime or uploaded_file.type or "application/octet-stream",
        )

    # ── Auth ──────────────────────────────────────────────────────────────────
    def register(
        self,
        username: str,
        email: str,
        password: str,
        selfie_file,
    ) -> dict:
        """POST /auth/register — multipart form with selfie image."""
        resp = requests.post(
            f"{self.base_url}/auth/register",
            data={"username": username, "email": email, "password": password},
            files={"selfie": self._file_tuple(selfie_file)},
        )
        _raise_for_status(resp)
        return resp.json()

    def login(self, username: str, password: str) -> str:
        """POST /auth/login — OAuth2 form; returns the raw access_token string."""
        resp = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": username, "password": password},
        )
        _raise_for_status(resp)
        return resp.json()["access_token"]

    # ── Profile ───────────────────────────────────────────────────────────────
    def get_profile(self) -> dict:
        """GET /profile/me — requires token."""
        resp = requests.get(
            f"{self.base_url}/profile/me",
            headers=self._auth_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    def update_selfie(self, selfie_file) -> dict:
        """PUT /profile/selfie — upload a new selfie image."""
        resp = requests.put(
            f"{self.base_url}/profile/selfie",
            headers=self._auth_headers(),
            files={"selfie": self._file_tuple(selfie_file)},
        )
        _raise_for_status(resp)
        return resp.json()

    # ── Jobs ──────────────────────────────────────────────────────────────────
    def upload_zip(self, zip_file) -> dict:
        """POST /jobs/upload — upload a ZIP archive and create a curation job."""
        resp = requests.post(
            f"{self.base_url}/jobs/upload",
            headers=self._auth_headers(),
            files={"zip_file": self._file_tuple(zip_file, "application/zip")},
        )
        _raise_for_status(resp)
        return resp.json()

    def get_job_status(self, job_id: int) -> dict:
        """GET /jobs/{job_id}/status — poll job progress."""
        resp = requests.get(
            f"{self.base_url}/jobs/{job_id}/status",
            headers=self._auth_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    def get_history(self) -> list:
        """GET /jobs/history — list of all jobs for the current user."""
        resp = requests.get(
            f"{self.base_url}/jobs/history",
            headers=self._auth_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    def download_result(self, job_id: int) -> bytes:
        """GET /jobs/{job_id}/download — return raw ZIP bytes."""
        resp = requests.get(
            f"{self.base_url}/jobs/{job_id}/download",
            headers=self._auth_headers(),
        )
        _raise_for_status(resp)
        return resp.content

    def delete_job(self, job_id: int) -> None:
        """DELETE /jobs/{job_id} — remove a job record and its files."""
        resp = requests.delete(
            f"{self.base_url}/jobs/{job_id}",
            headers=self._auth_headers(),
        )
        _raise_for_status(resp)
