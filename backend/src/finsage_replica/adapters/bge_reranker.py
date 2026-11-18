"""Reranker adapter for BAAI/bge-reranker-v2-m3 (cross-encoder).

The paper trains its own decoder reranker with DPO; that model and its data were not released,
so the replica uses this pretrained cross-encoder (declared limitation).
"""

from __future__ import annotations

MODEL_NAME = "BAAI/bge-reranker-v2-m3"


class BgeReranker:
    def __init__(self, device: str = "cuda", max_length: int = 512, batch_size: int = 16):
        import torch
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(MODEL_NAME, device=device, max_length=max_length,
                                   model_kwargs={"torch_dtype": torch.float16} if device == "cuda" else None)
        self._sigmoid = torch.nn.Sigmoid()
        self._batch_size = batch_size

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        scores = self._model.predict([[query, p] for p in passages], batch_size=self._batch_size,
                                     activation_fn=self._sigmoid, convert_to_numpy=True)
        return [float(s) for s in scores]
