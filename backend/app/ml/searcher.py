"""
searcher.py — Query a FAISS index with a selfie embedding.

Loads the pre-built vectors.index and mapping.json produced by FaissIndexer,
embeds the query selfie with FaceEmbedder, and returns all photo filenames
whose inner-product similarity to the selfie meets or exceeds *threshold*.
"""

import json
import logging
from pathlib import Path

import faiss
import numpy as np

from app.ml.embedder import FaceEmbedder

logger = logging.getLogger(__name__)


class FaissSearcher:
    """Searches a FAISS index for photos matching a query selfie."""

    def __init__(self) -> None:
        self._embedder = FaceEmbedder()

    def search(
        self,
        selfie_path: "str | Path",
        index_dir: "str | Path",
        threshold: float = 0.40,
        top_k: int = 500,
    ) -> list[str]:
        """
        Embed *selfie_path*, query the FAISS index in *index_dir*, and return
        the filenames of all photos whose similarity score >= *threshold*.

        Returns an empty list if no face is detected in the selfie or if the
        index is empty.
        """
        index_dir = Path(index_dir)

        index = faiss.read_index(str(index_dir / "vectors.index"))
        with (index_dir / "mapping.json").open(encoding="utf-8") as fp:
            mapping: list[str] = json.load(fp)

        if index.ntotal == 0:
            logger.warning("FAISS index is empty — no photos to search")
            return []

        embedding = self._embedder.embed(selfie_path)
        if embedding is None:
            logger.warning("No face detected in selfie: %s", selfie_path)
            return []

        query = embedding.astype(np.float32).reshape(1, -1)
        # FaceEmbedder already returns an L2-normalised vector;
        # no need to call faiss.normalize_L2() again.

        k = min(top_k, index.ntotal)
        scores, indices = index.search(query, k)

        matched = [
            mapping[idx]
            for score, idx in zip(scores[0], indices[0])
            if idx != -1 and float(score) >= threshold
        ]

        logger.info(
            "Search complete — matched %d / %d indexed (threshold=%.2f)",
            len(matched),
            index.ntotal,
            threshold,
        )
        return matched
