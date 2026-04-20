"""
detector.py — Face detection via InsightFace (RetinaFace + ArcFace buffalo_l).

The InsightFace app is loaded once (singleton) and reused across all calls.
Both FaceDetector and FaceEmbedder share the same singleton through
the module-level `_get_app()` helper so the model is not loaded twice.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Singleton ─────────────────────────────────────────────────────────────────
_insight_app = None


def _get_app():
    """Return the module-level InsightFace app, initialising it on first call."""
    global _insight_app
    if _insight_app is None:
        import insightface  # deferred so startup stays fast if ML not used

        logger.info("Loading InsightFace buffalo_l model — first call only …")
        _insight_app = insightface.app.FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"],
        )
        _insight_app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.3)
        logger.info("InsightFace model loaded successfully.")
    return _insight_app


# ── FaceDetector ──────────────────────────────────────────────────────────────
class FaceDetector:
    """Detects faces in an image and returns the largest face's embedding."""

    def __init__(self) -> None:
        self._app = _get_app()

    def detect(self, image_path: "str | Path") -> "np.ndarray | None":
        """
        Read *image_path*, run InsightFace detection+recognition pipeline,
        and return the raw 512-dim ArcFace embedding of the **largest** detected
        face, or ``None`` if no face is found or the image cannot be read.
        """
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                logger.warning("Could not read image (corrupt/unsupported): %s", image_path)
                return None

            h, w = img.shape[:2]
            logger.debug("Processing %s (%dx%d)", Path(image_path).name, w, h)

            # Upscale small images so InsightFace can detect faces reliably.
            # Thumbnails (e.g. 102x108) are too small for RetinaFace's minimum
            # face-size filter — upscaling to at least 300px on the short side
            # brings face pixel-area within the detectable range.
            MIN_DIM = 300
            if min(h, w) < MIN_DIM:
                scale = MIN_DIM / min(h, w)
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
                logger.debug(
                    "Upscaled %s from %dx%d → %dx%d",
                    Path(image_path).name, w, h, new_w, new_h,
                )

            faces = self._app.get(img)
            if not faces:
                logger.info("No face detected in %s (%dx%d)", Path(image_path).name, w, h)
                return None

            # Largest face by bounding-box area
            largest = max(
                faces,
                key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]),
            )

            if largest.embedding is None:
                logger.warning("Face found but embedding is None in %s", image_path)
                return None

            return largest.embedding  # np.ndarray, shape (512,)

        except Exception as exc:
            logger.error("Unexpected error processing %s: %s", Path(image_path).name, exc)
            return None

