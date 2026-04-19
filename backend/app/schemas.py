from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────
class RegisterResponse(BaseModel):
    user_id:  int
    username: str
    email:    str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── Profile ───────────────────────────────────────────────────────────────────
class ProfileResponse(BaseModel):
    user_id:    int
    username:   str
    email:      str
    has_selfie: bool
    created_at: str

    model_config = {"from_attributes": True}


# ── Jobs ──────────────────────────────────────────────────────────────────────
class JobCreateResponse(BaseModel):
    job_id:     int
    status:     str
    created_at: str


class JobSummary(BaseModel):
    job_id:     int
    status:     str
    created_at: str
    updated_at: str
    has_result: bool

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    job_id:           int
    status:           str
    updated_at:       str
    total_photos:     Optional[int] = None
    processed_photos: Optional[int] = None
    matched_photos:   Optional[int] = None

    model_config = {"from_attributes": True}
