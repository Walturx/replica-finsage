"""Embedder adapter for BAAI/bge-m3 (dense vectors) through sentence-transformers."""

from __future__ import annotations

import numpy as np

MODEL_NAME = "BAAI/bge-m3"


class BgeM3Embedder:
    def __init__(self, device: str = "cuda", fp16: bool = True, max_seq_length: int = 512, batch_size: int = 32):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(MODEL_NAME, device=device)
        if fp16:
            self._model.half()
        self._model.max_seq_length = max_seq_length
        self._batch_size = batch_size

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            texts, batch_size=self._batch_size, normalize_embeddings=True, convert_to_numpy=True
        )
        return vectors.astype(np.float32)
