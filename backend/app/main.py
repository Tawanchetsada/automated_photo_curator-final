from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import SELFIE_DIR
from app.database import Base, engine
from app.routers import auth, jobs, profile

# ── Create all tables on startup ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Automated Personal Photo Curator",
    description=(
        "API for uploading photo ZIPs, curating them with face recognition, "
        "and downloading the matched results."
    ),
    version="1.0.0",
)

# ── CORS (allow all origins for development) ──────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(jobs.router)

# Serve selfie images so the frontend can preview them
app.mount("/selfies", StaticFiles(directory=str(SELFIE_DIR)), name="selfies")


@app.get("/", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "service": "photo-curator-api"}
