import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import ALLOWED_IMAGE_TYPES, SELFIE_DIR
from app.database import get_db
from app.models import User
from app.schemas import ProfileResponse

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_profile_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        has_selfie=bool(user.selfie_path),
        created_at=user.created_at.isoformat(),
    )


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Get the authenticated user's profile",
)
def get_profile(current_user: User = Depends(get_current_user)) -> ProfileResponse:
    return _build_profile_response(current_user)


@router.put(
    "/selfie",
    response_model=ProfileResponse,
    summary="Update the authenticated user's selfie",
)
async def update_selfie(
    selfie:       UploadFile = File(...),
    current_user: User       = Depends(get_current_user),
    db:           Session    = Depends(get_db),
) -> ProfileResponse:
    if not selfie.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    if selfie.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selfie must be an image (jpg/png/webp)",
        )

    selfie_path = SELFIE_DIR / f"{current_user.id}.jpg"
    with selfie_path.open("wb") as f:
        shutil.copyfileobj(selfie.file, f)

    current_user.selfie_path = str(selfie_path)
    db.commit()
    db.refresh(current_user)

    return _build_profile_response(current_user)
