"""
routers/jobs.py — Photo curation job endpoints.

POST /jobs/upload    – upload a ZIP and enqueue a background curation job
GET  /jobs/history   – list all jobs for the current user
GET  /jobs/{id}/status   – poll job status
GET  /jobs/{id}/download – download the curated result ZIP
"""

import logging
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import FAISS_INDEX_DIR, MLFLOW_TRACKING_URI, RESULT_DIR, UPLOAD_DIR
from app.database import SessionLocal, get_db
from app.models import Job, JobStatus, User
from app.schemas import JobCreateResponse, JobStatusResponse, JobSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# ── Pipeline constants ────────────────────────────────────────────────────────
_THRESHOLD = 0.40
_TOP_K     = 500


# ── Background task ───────────────────────────────────────────────────────────
def process_job(job_id: int, db: Session) -> None:
    """
    Full ML curation pipeline executed as a FastAPI BackgroundTask.

    Steps
    -----
    1. Mark job as *processing*.
    2. Build FAISS index from the uploaded ZIP.
    3. Embed the owner's selfie and search for matching photos.
    4. Pack matched photos into a result ZIP.
    5. Mark job as *done* and persist result_path.
    6. Track all metrics + params in MLflow.
    7. Always clean up temp directories and close the DB session.
    """
    # Deferred heavy imports so app startup remains fast
    import mlflow

    from app.ml.indexer import FaissIndexer
    from app.ml.searcher import FaissSearcher

    tmp_dirs: list[str] = []


    job: Job | None = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        logger.error("process_job: job %d not found", job_id)
        db.close()
        return

    try:
        # ── Step 1: mark processing ───────────────────────────────────────────
        job.status     = JobStatus.processing
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        start_time = time.perf_counter()
        logger.info("Job %d: started processing", job_id)

        # ── Step 2: build FAISS index ─────────────────────────────────────────
        logger.info("Job %d: building FAISS index from %s", job_id, job.zip_path)

        def on_progress(current: int, total: int) -> None:
            """Persist progress to DB every 10 images to limit write frequency."""
            if current % 10 == 0 or current == total:
                job.total_photos     = total
                job.processed_photos = current
                job.updated_at       = datetime.now(timezone.utc)
                db.commit()

        indexer     = FaissIndexer()
        index_stats = indexer.build_index(
            job.zip_path, job.faiss_index_path, progress_callback=on_progress
        )
        logger.info("Job %d: index stats = %s", job_id, index_stats)

        # Ensure final progress is committed even if total wasn't divisible by 10
        job.total_photos     = index_stats["total"]
        job.processed_photos = index_stats["indexed"] + index_stats["skipped"]
        job.matched_photos   = 0
        db.commit()

        # ── Step 3: get user selfie ───────────────────────────────────────────
        user: User | None = db.query(User).filter(User.id == job.user_id).first()
        if not user or not user.selfie_path:
            logger.error(
                "Job %d: user %d has no selfie — cannot search", job_id, job.user_id
            )
            job.status     = JobStatus.failed
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
            return

        # ── Step 4: similarity search ─────────────────────────────────────────
        logger.info("Job %d: searching index with selfie %s", job_id, user.selfie_path)
        searcher      = FaissSearcher()
        matched_files = searcher.search(
            user.selfie_path,
            job.faiss_index_path,
            threshold=_THRESHOLD,
            top_k=_TOP_K,
        )
        logger.info("Job %d: %d file(s) matched", job_id, len(matched_files))
        job.matched_photos = len(matched_files)
        db.commit()

        # ── Step 5: build result ZIP ──────────────────────────────────────────
        tmp_extract = tempfile.mkdtemp()
        tmp_dirs.append(tmp_extract)

        with zipfile.ZipFile(job.zip_path, "r") as zf:
            zf.extractall(tmp_extract)

        matched_set     = set(matched_files)
        result_zip_path = RESULT_DIR / f"{job_id}_result.zip"

        with zipfile.ZipFile(result_zip_path, "w", zipfile.ZIP_DEFLATED) as result_zip:
            for file_path in Path(tmp_extract).rglob("*"):
                if file_path.is_file() and file_path.name in matched_set:
                    result_zip.write(file_path, arcname=file_path.name)

        logger.info("Job %d: result ZIP written to %s", job_id, result_zip_path)

        processing_time = time.perf_counter() - start_time

        # ── Step 6: MLflow tracking (best-effort — never fails the job) ──────
        try:
            from app.config import MLFLOW_TRACKING_URI
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_experiment("photo_curator")

            with mlflow.start_run():
                mlflow.log_param("job_id",    job_id)
                mlflow.log_param("threshold", _THRESHOLD)
                mlflow.log_param("top_k",     _TOP_K)
                mlflow.log_metric("indexed_count",          index_stats["indexed"])
                mlflow.log_metric("skipped_count",          index_stats["skipped"])
                mlflow.log_metric("matched_count",          len(matched_files))
                mlflow.log_metric("processing_time_seconds", round(processing_time, 3))
        except Exception as exc:
            logger.warning("Job %d: MLflow tracking failed: %s — continuing without tracking", job_id, exc)

        # ── Step 7: mark done ─────────────────────────────────────────────────
        job.result_path = str(result_zip_path)
        job.status      = JobStatus.done
        job.updated_at  = datetime.now(timezone.utc)
        db.commit()
        logger.info("Job %d: completed in %.2fs", job_id, processing_time)

    except Exception:
        logger.exception("process_job: job %d failed", job_id)
        try:
            job.status     = JobStatus.failed
            job.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            logger.exception("process_job: could not update job %d to failed", job_id)

    finally:
        for tmp_dir in tmp_dirs:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _assert_job_belongs_to_user(job: "Job | None", user_id: int) -> Job:
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return job


def _job_summary(job: Job) -> JobSummary:
    return JobSummary(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
        has_result=bool(job.result_path and Path(job.result_path).exists()),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.post(
    "/upload",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a ZIP of photos and enqueue a curation job",
)
async def upload_job(
    background_tasks: BackgroundTasks,
    zip_file:         UploadFile  = File(...),
    current_user:     User        = Depends(get_current_user),
    db:               Session     = Depends(get_db),
) -> JobCreateResponse:
    if not zip_file.filename or not zip_file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are accepted",
        )

    # Create job record
    job = Job(user_id=current_user.id, status=JobStatus.pending)
    db.add(job)
    db.flush()  # get job.id before commit

    # Save uploaded ZIP
    zip_dest = UPLOAD_DIR / f"{job.id}.zip"
    with zip_dest.open("wb") as f:
        f.write(await zip_file.read())

    job.zip_path = str(zip_dest)

    # Pre-create FAISS index directory
    faiss_dir = FAISS_INDEX_DIR / str(job.id)
    faiss_dir.mkdir(parents=True, exist_ok=True)
    job.faiss_index_path = str(faiss_dir)

    db.commit()
    db.refresh(job)

    # Enqueue background task with its own independent DB session
    bg_db = SessionLocal()
    background_tasks.add_task(process_job, job.id, bg_db)

    return JobCreateResponse(
        job_id=job.id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
    )


@router.get(
    "/history",
    response_model=list[JobSummary],
    summary="Return all jobs for the authenticated user",
)
def job_history(
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> list[JobSummary]:
    jobs = (
        db.query(Job)
        .filter(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return [_job_summary(j) for j in jobs]


@router.get(
    "/{job_id}/status",
    response_model=JobStatusResponse,
    summary="Get the current status of a job",
)
def job_status(
    job_id:       int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> JobStatusResponse:
    job = db.query(Job).filter(Job.id == job_id).first()
    _assert_job_belongs_to_user(job, current_user.id)
    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        updated_at=job.updated_at.isoformat(),
        total_photos=job.total_photos,
        processed_photos=job.processed_photos,
        matched_photos=job.matched_photos,
    )


@router.get(
    "/{job_id}/download",
    summary="Download the curated result ZIP for a completed job",
)
def download_result(
    job_id:       int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
) -> FileResponse:
    job = db.query(Job).filter(Job.id == job_id).first()
    _assert_job_belongs_to_user(job, current_user.id)

    if job.status != JobStatus.done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not complete (current status: {job.status.value})",
        )

    result_path = RESULT_DIR / f"{job_id}_result.zip"
    if not result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found",
        )

    return FileResponse(
        path=str(result_path),
        media_type="application/zip",
        filename=f"curated_{job_id}.zip",
    )
