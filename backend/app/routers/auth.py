import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, hash_password, verify_password
from app.config import ALLOWED_IMAGE_TYPES, SELFIE_DIR
from app.database import get_db
from app.models import User
from app.schemas import RegisterResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with an optional selfie",
)
async def register(
    username: str      = Form(...),
    email:    str      = Form(...),
    password: str      = Form(...),
    selfie:   UploadFile = File(None),
    db:       Session  = Depends(get_db),
) -> RegisterResponse:
    # Check uniqueness
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()  # get user.id without committing

    # Save selfie if provided
    if selfie and selfie.filename:
        if selfie.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selfie must be an image (jpg/png/webp)",
            )
        selfie_path = SELFIE_DIR / f"{user.id}.jpg"
        with selfie_path.open("wb") as f:
            shutil.copyfileobj(selfie.file, f)
        user.selfie_path = str(selfie_path)

    db.commit()
    db.refresh(user)

    return RegisterResponse(user_id=user.id, username=user.username, email=user.email)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT token",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db:        Session                   = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, token_type="bearer")
