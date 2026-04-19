"""
indexer.py — Build a FAISS IndexFlatIP from a ZIP of photos.

Extracts the ZIP to a temp directory, embeds every face-containing image with
FaceEmbedder, adds the normalised vectors to a FAISS inner-product index, then
persists the index and a filename mapping so FaissSearcher can use them later.
"""

import json
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path

import faiss
import numpy as np

from app.ml.embedder import FaceEmbedder

logger = logging.getLogger(__name__)

ACCEPTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FaissIndexer:
    """Builds a FAISS index from photos inside a ZIP archive."""

    def __init__(self) -> None:
        self._embedder = FaceEmbedder()

    def build_index(
        self,
        zip_path: "str | Path",
        index_dir: "str | Path",
        progress_callback: "callable | None" = None,
    ) -> dict:
        """
        Extract *zip_path*, embed every image that contains a face, and write:

        * ``{index_dir}/vectors.index`` — FAISS IndexFlatIP (inner product)
        * ``{index_dir}/mapping.json``  — ordered list of filenames (same order
          as the FAISS index rows)

        Returns a dict ``{"indexed": int, "skipped": int, "total": int}``.
        """
        zip_path  = Path(zip_path)
        index_dir = Path(index_dir)
        index_dir.mkdir(parents=True, exist_ok=True)

        tmp_dir = tempfile.mkdtemp()
        try:
            logger.info("Extracting %s → %s", zip_path.name, tmp_dir)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)

            image_files = [
                f
                for f in Path(tmp_dir).rglob("*")
                if f.is_file() and f.suffix.lower() in ACCEPTED_EXTENSIONS
            ]
            logger.info("Found %d image(s) to process", len(image_files))

            dimension = 512
            index     = faiss.IndexFlatIP(dimension)
            mapping: list[str] = []
            skipped = 0

            for i, img_path in enumerate(image_files, start=1):
                embedding = self._embedder.embed(img_path)
                if embedding is None:
                    logger.debug("No face — skipping %s", img_path.name)
                    skipped += 1
                else:
                    vec = embedding.astype(np.float32).reshape(1, -1)
                    # FaceEmbedder already returns an L2-normalised vector;
                    # no need to call faiss.normalize_L2() again.
                    index.add(vec)
                    mapping.append(img_path.name)

                if progress_callback:
                    progress_callback(i, len(image_files))

            # ── Persist ───────────────────────────────────────────────────────
            faiss.write_index(index, str(index_dir / "vectors.index"))
            with (index_dir / "mapping.json").open("w", encoding="utf-8") as fp:
                json.dump(mapping, fp)

            stats = {
                "indexed": len(mapping),
                "skipped": skipped,
                "total":   len(image_files),
            }
            logger.info("Index built: %s", stats)
            return stats

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
