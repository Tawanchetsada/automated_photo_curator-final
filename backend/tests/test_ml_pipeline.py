"""
tests/test_ml_pipeline.py — Unit tests for the ML pipeline classes.

No real models are loaded: InsightFace's _get_app() is mocked everywhere
so tests run without GPU, without internet, and without the heavy
insightface/onnxruntime packages being initialised.
"""

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import faiss
import numpy as np
import pytest

from app.ml.embedder import FaceEmbedder
from app.ml.indexer import FaissIndexer
from app.ml.searcher import FaissSearcher


# ── FaceEmbedder ──────────────────────────────────────────────────────────────
def test_embedder_returns_none_for_missing_file() -> None:
    """
    When FaceDetector.detect() returns None (no face / bad image),
    FaceEmbedder.embed() must propagate None without raising.
    """
    # Patch _get_app so no real InsightFace model is loaded,
    # then patch FaceDetector so detect() returns None.
    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.embedder.FaceDetector") as MockDetector:
            MockDetector.return_value.detect.return_value = None
            embedder = FaceEmbedder()
            result = embedder.embed("nonexistent.jpg")

    assert result is None


def test_embedder_normalises_vector() -> None:
    """embed() must return an L2-normalised (unit-norm) vector."""
    raw = np.random.rand(512).astype(np.float32)

    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.embedder.FaceDetector") as MockDetector:
            MockDetector.return_value.detect.return_value = raw
            embedder = FaceEmbedder()
            result = embedder.embed("photo.jpg")

    assert result is not None
    assert abs(float(np.linalg.norm(result)) - 1.0) < 1e-5


# ── FaissIndexer ──────────────────────────────────────────────────────────────
def test_indexer_skips_no_face_images(tmp_path: Path) -> None:
    """
    When embed() returns None for every image (no faces detected),
    build_index() must report indexed=0 and skipped=total.
    """
    # Build an in-memory ZIP with 2 fake JPEG files
    zip_path = tmp_path / "photos.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("photo1.jpg", b"fakejpeg1")
        zf.writestr("photo2.jpg", b"fakejpeg2")

    index_dir = tmp_path / "index"

    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.indexer.FaceEmbedder") as MockEmbedder:
            MockEmbedder.return_value.embed.return_value = None  # no face in any image
            indexer = FaissIndexer()
            stats = indexer.build_index(zip_path, index_dir)

    assert stats["indexed"] == 0
    assert stats["skipped"] == 2
    assert stats["total"]   == 2

    # Index and mapping files must still be written (empty but valid)
    assert (index_dir / "vectors.index").exists()
    assert (index_dir / "mapping.json").exists()


def test_indexer_adds_faces_to_index(tmp_path: Path) -> None:
    """
    When embed() returns a valid unit vector, build_index() must
    add it to the FAISS index (indexed == number of images with a face).
    """
    zip_path = tmp_path / "photos.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("face.jpg", b"fakejpeg")
        zf.writestr("noface.jpg", b"fakejpeg2")

    fake_embedding = np.ones(512, dtype=np.float32) / np.sqrt(512)

    # Return embedding for the first call, None for the second
    side_effects = [fake_embedding, None]

    index_dir = tmp_path / "index"

    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.indexer.FaceEmbedder") as MockEmbedder:
            MockEmbedder.return_value.embed.side_effect = side_effects
            indexer = FaissIndexer()
            stats = indexer.build_index(zip_path, index_dir)

    assert stats["indexed"] == 1
    assert stats["skipped"] == 1
    assert stats["total"]   == 2


# ── FaissSearcher ─────────────────────────────────────────────────────────────
def test_searcher_returns_empty_for_empty_index(tmp_path: Path) -> None:
    """
    Searching an empty FAISS index must return [] immediately
    (before any embedding or search is performed).
    """
    # Write an empty but valid FAISS index + empty mapping
    empty_index = faiss.IndexFlatIP(512)
    faiss.write_index(empty_index, str(tmp_path / "vectors.index"))
    (tmp_path / "mapping.json").write_text(json.dumps([]))

    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.searcher.FaceEmbedder") as MockEmbedder:
            MockEmbedder.return_value.embed.return_value = np.zeros(512, dtype=np.float32)
            searcher = FaissSearcher()
            result = searcher.search("selfie.jpg", tmp_path)

    assert result == []


def test_searcher_returns_empty_when_no_selfie_face(tmp_path: Path) -> None:
    """
    If embed() returns None for the selfie (no face detected),
    search() must return [].
    """
    # Build a non-empty index with one vector so we can reach the embed check
    vec = np.ones(512, dtype=np.float32) / np.sqrt(512)
    index = faiss.IndexFlatIP(512)
    index.add(vec.reshape(1, -1))
    faiss.write_index(index, str(tmp_path / "vectors.index"))
    (tmp_path / "mapping.json").write_text(json.dumps(["photo.jpg"]))

    with patch("app.ml.detector._get_app", return_value=MagicMock()):
        with patch("app.ml.searcher.FaceEmbedder") as MockEmbedder:
            MockEmbedder.return_value.embed.return_value = None  # no face in selfie
            searcher = FaissSearcher()
            result = searcher.search("selfie.jpg", tmp_path)

    assert result == []
