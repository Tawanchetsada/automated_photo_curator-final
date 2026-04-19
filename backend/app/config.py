import os
from pathlib import Path

# ── JWT ──────────────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

# ── Database ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = BASE_DIR / "data"
DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'app.db'}"

# ── File storage paths ────────────────────────────────────────────────────────
SELFIE_DIR       = DATA_DIR / "selfies"
UPLOAD_DIR       = DATA_DIR / "uploads"
RESULT_DIR       = DATA_DIR / "results"
FAISS_INDEX_DIR  = DATA_DIR / "faiss_indexes"

# ── MLflow ────────────────────────────────────────────────────────────────────
# In Docker: reads MLFLOW_TRACKING_URI=http://mlflow:5000 from docker-compose env.
# Local dev fallback: file-based store (no SQLite locking issues).
MLFLOW_TRACKING_URI: str = os.getenv(
    "MLFLOW_TRACKING_URI",
    f"file:///{BASE_DIR.parent}/mlflow_tracking",
)

# ── Validation ────────────────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Create directories on import
for _dir in (DATA_DIR, SELFIE_DIR, UPLOAD_DIR, RESULT_DIR, FAISS_INDEX_DIR):
    _dir.mkdir(parents=True, exist_ok=True)
