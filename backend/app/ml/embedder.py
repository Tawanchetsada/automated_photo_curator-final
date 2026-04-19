"""
embedder.py — L2-normalised ArcFace embedding extraction.

Reuses the InsightFace singleton from detector.py so the model is loaded only
once even when both FaceDetector and FaceEmbedder are instantiated.
"""

import logging
from pathlib import Path

import numpy as np

from app.ml.detector import FaceDetector

logger = logging.getLogger(__name__)


class FaceEmbedder:
    """Wraps FaceDetector and returns an L2-normalised 512-dim embedding."""

    def __init__(self) -> None:
        # Reuses the singleton InsightFace app via FaceDetector
        self._detector = FaceDetector()

    def embed(self, image_path: "str | Path") -> "np.ndarray | None":
        """
        Detect the largest face in *image_path* and return its L2-normalised
        512-dim ArcFace embedding, or ``None`` if no face is found.
        """
        raw = self._detector.detect(image_path)
        if raw is None:
            return None

        vec = raw.astype(np.float32)
        norm = float(np.linalg.norm(vec))
        if norm == 0.0:
            logger.warning("Zero-norm embedding for %s — skipping", image_path)
            return None

        return vec / norm  # L2-normalised, shape (512,)
