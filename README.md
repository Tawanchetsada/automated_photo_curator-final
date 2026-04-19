# Automated Personal Photo Curator

> AI-powered photo curation — upload an event ZIP, and get back only the photos **featuring your face**.

Built with **FastAPI** · **InsightFace (ArcFace)** · **FAISS** · **MLflow** · **Streamlit** · **Docker**

---

## Table of Contents

- [Architecture](#architecture)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
  - [Backend](#backend-dev)
  - [Frontend](#frontend-dev)
- [API Reference](#api-reference)
- [ML Pipeline](#ml-pipeline)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)

---

## Architecture

```
┌─────────────────┐       HTTP        ┌──────────────────────────┐
│  Streamlit      │ ────────────────► │  FastAPI Backend         │
│  Frontend       │  BACKEND_URL      │                          │
│  :8501          │                   │  /auth   /profile /jobs  │
└─────────────────┘                   │  /selfies (static)       │
                                      └────────────┬─────────────┘
                                                   │
                         ┌─────────────────────────┼──────────────────────┐
                         │                         │                      │
                   SQLite DB               ML Pipeline              MLflow
                   data/app.db      InsightFace + FAISS        mlflow_tracking/
```

### Data Flow

1. User registers with a **selfie** → stored at `data/selfies/{user_id}.jpg`
2. User uploads a **ZIP of event photos** → stored at `data/uploads/{job_id}.zip`
3. Background task runs the **ML pipeline**:
   - Detects & embeds every face in the ZIP with **ArcFace (buffalo_l)**
   - Builds a **FAISS IndexFlatIP** (cosine similarity via inner product)
   - Searches the index using the selfie embedding (threshold `0.40`)
   - Packs matched photos into `data/results/{job_id}_result.zip`
4. User downloads the **curated result ZIP**

---

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url>
cd automated_photo_curator-final

# 2. Copy and configure environment
cp .env.example .env
# Edit .env → set a strong SECRET_KEY

# 3. Build and start all services
docker compose up --build

# Backend  → http://localhost:8000
# Frontend → http://localhost:8501
# API docs → http://localhost:8000/docs
```

> **Note:** The first `docker compose build` will take a few minutes because it
> pre-downloads the InsightFace `buffalo_l` model (~300 MB) into the image layer.
> Subsequent builds use the Docker cache.

### Persistent Data

All persistent files live in host-mounted directories:

| Host path          | Container path         | Contents                        |
|--------------------|------------------------|---------------------------------|
| `./data/`          | `/app/data/`           | SQLite DB, selfies, ZIPs, results |
| `./mlflow_tracking/` | `/app/mlflow_tracking/` | MLflow SQLite + artifacts      |

---

## Local Development

### Backend Dev

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Run development server (auto-reload)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### Frontend Dev

```bash
cd frontend

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

# Point to local backend
set BACKEND_URL=http://localhost:8000   # Windows
# export BACKEND_URL=http://localhost:8000  # macOS / Linux

streamlit run app.py
```

Frontend: http://localhost:8501

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | — | Register with username, email, password, selfie |
| `POST` | `/auth/login` | — | Login → returns JWT |
| `GET`  | `/profile/me` | ✅ | Get current user profile |
| `PUT`  | `/profile/selfie` | ✅ | Update selfie image |
| `POST` | `/jobs/upload` | ✅ | Upload photo ZIP → create curation job |
| `GET`  | `/jobs/history` | ✅ | List all jobs for current user |
| `GET`  | `/jobs/{id}/status` | ✅ | Poll job status |
| `GET`  | `/jobs/{id}/download` | ✅ | Download curated result ZIP |
| `GET`  | `/selfies/{user_id}.jpg` | — | Serve selfie image (static) |

Full interactive docs available at `/docs` (Swagger UI) or `/redoc`.

---

## ML Pipeline

```
ZIP archive
    │
    ▼
Extract images (.jpg .jpeg .png .webp)
    │
    ▼ (per image)
FaceDetector.detect()          ← InsightFace RetinaFace
    │  returns 512-dim ArcFace embedding of largest face
    ▼
FaceEmbedder.embed()           ← L2-normalise
    │
    ▼
faiss.IndexFlatIP.add()        ← inner product ≡ cosine on unit vectors
    │
    ▼ (saved to disk)
vectors.index + mapping.json
    │
    ▼ (query with selfie)
FaissSearcher.search()
    │  threshold = 0.40  |  top_k = 500
    ▼
matched_filenames[]
    │
    ▼
Pack into result ZIP
```

### Tuning

Edit constants in `backend/app/routers/jobs.py`:

```python
_THRESHOLD = 0.40   # raise → stricter match, fewer results
_TOP_K     = 500    # max candidates to rank
```

### MLflow Tracking

Each job logs the following to `mlflow_tracking/mlflow.db`:

| Type | Name | Value |
|------|------|-------|
| param | `job_id` | job ID |
| param | `threshold` | 0.40 |
| param | `top_k` | 500 |
| metric | `indexed_count` | photos with a detected face |
| metric | `skipped_count` | photos without a face |
| metric | `matched_count` | photos matching the selfie |
| metric | `processing_time_seconds` | wall-clock time |

View the MLflow UI:
```bash
mlflow ui --backend-store-uri sqlite:///mlflow_tracking/mlflow.db
# → http://localhost:5000
```

---

## Project Structure

```
automated_photo_curator-final/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # FastAPI app, CORS, static files
│       ├── config.py        # paths, JWT settings, env vars
│       ├── database.py      # SQLAlchemy engine + get_db()
│       ├── models.py        # User, Job ORM models
│       ├── schemas.py       # Pydantic v2 response schemas
│       ├── auth.py          # JWT + bcrypt utilities
│       ├── routers/
│       │   ├── auth.py      # POST /auth/register|login
│       │   ├── profile.py   # GET|PUT /profile/*
│       │   └── jobs.py      # POST|GET /jobs/* + ML pipeline
│       └── ml/
│           ├── detector.py  # InsightFace singleton + face detect
│           ├── embedder.py  # L2-normalised ArcFace embedding
│           ├── indexer.py   # ZIP → FAISS index builder
│           └── searcher.py  # FAISS similarity search
│
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py               # Entry point, auth routing
│   ├── pages/
│   │   ├── 1_register.py   # Standalone register page
│   │   ├── 2_dashboard.py  # Upload + job tracking
│   │   └── 3_profile.py    # Profile info + selfie update
│   └── utils/
│       └── api_client.py   # HTTP client wrapper
│
└── data/                    # Created automatically at runtime
    ├── app.db
    ├── selfies/
    ├── uploads/
    ├── results/
    └── faiss_indexes/
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev-secret-key` | JWT signing key — **change in production** |
| `BACKEND_URL` | `http://localhost:8000` | Backend URL used by the Streamlit frontend |

Set these in `.env` (copy from `.env.example`) or pass directly to Docker Compose.
