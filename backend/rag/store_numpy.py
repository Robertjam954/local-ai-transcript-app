"""Dependency-light vector store fallback backed by NumPy.

Used when ChromaDB is not installed (e.g. tight disk). Provides the same
interface as HybridStore - dense cosine search + an inline BM25 keyword score,
fused with reciprocal rank fusion - but persists to a simple .npz + .json pair
and needs only NumPy (already a core dependency) plus the `openai` client for
Ollama/LM Studio embeddings. No extra installs required.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter

import numpy as np
from openai import OpenAI

from .config import RagConfig
from .store import Retrieved


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class NumpyStore:
    """Persistent NumPy-backed hybrid store. Same surface as HybridStore."""

    def __init__(self, config: RagConfig):
        self.config = config
        self._embed_client: OpenAI | None = None
        self._vecs: np.ndarray | None = None  # (N, D) float32, L2-normalized
        self._ids: list[str] = []
        self._docs: list[str] = []
        self._metas: list[dict] = []
        config.vector_dir.mkdir(parents=True, exist_ok=True)
        self._npz = config.vector_dir / "numpy_store.npz"
        self._meta = config.vector_dir / "numpy_store.json"
        self._load()

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        if self._meta.exists():
            payload = json.loads(self._meta.read_text())
            self._ids = payload.get("ids", [])
            self._docs = payload.get("docs", [])
            self._metas = payload.get("metas", [])
        if self._npz.exists():
            self._vecs = np.load(self._npz)["vecs"].astype("float32")

    def _persist(self) -> None:
        self._meta.write_text(
            json.dumps({"ids": self._ids, "docs": self._docs, "metas": self._metas})
        )
        vecs = self._vecs if self._vecs is not None else np.zeros((0, 1), "float32")
        np.savez_compressed(self._npz, vecs=vecs)

    # -- embeddings --------------------------------------------------------

    def _embedder(self) -> OpenAI:
        if self._embed_client is None:
            self._embed_client = OpenAI(
                base_url=self.config.openai_base_url, api_key="local"
            )
        return self._embed_client

    def _embed(self, texts: list[str]) -> np.ndarray:
        resp = self._embedder().embeddings.create(
            model=self.config.embed_model, input=texts
        )
        arr = np.array([d.embedding for d in resp.data], dtype="float32")
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return arr / norms

    # -- writes ------------------------------------------------------------

    def add(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        new = self._embed(texts)
        self._vecs = new if self._vecs is None else np.vstack([self._vecs, new])
        self._ids.extend(ids)
        self._docs.extend(texts)
        self._metas.extend(metadatas)
        self._persist()

    def delete_source(self, source: str) -> None:
        keep = [i for i, m in enumerate(self._metas) if m.get("source") != source]
        if len(keep) == len(self._ids):
            return
        self._ids = [self._ids[i] for i in keep]
        self._docs = [self._docs[i] for i in keep]
        self._metas = [self._metas[i] for i in keep]
        self._vecs = self._vecs[keep] if self._vecs is not None and keep else None
        self._persist()

    def count(self) -> int:
        return len(self._ids)

    # -- retrieval ---------------------------------------------------------

    def _bm25_scores(self, query: str) -> np.ndarray:
        """Minimal BM25 over the corpus (no external dependency)."""
        n = len(self._docs)
        if n == 0:
            return np.zeros(0)
        k1, b = 1.5, 0.75
        doc_tokens = [_tokenize(d) for d in self._docs]
        doc_len = np.array([len(t) for t in doc_tokens], dtype="float32")
        avgdl = doc_len.mean() if doc_len.mean() > 0 else 1.0
        q_terms = set(_tokenize(query))
        df = {
            t: sum(1 for toks in doc_tokens if t in toks) for t in q_terms
        }
        scores = np.zeros(n, dtype="float32")
        for i, toks in enumerate(doc_tokens):
            counts = Counter(toks)
            s = 0.0
            for t in q_terms:
                if df.get(t, 0) == 0:
                    continue
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                tf = counts.get(t, 0)
                s += idf * (tf * (k1 + 1)) / (
                    tf + k1 * (1 - b + b * doc_len[i] / avgdl)
                )
            scores[i] = s
        return scores

    def search(self, query: str) -> list[Retrieved]:
        n = len(self._ids)
        if n == 0 or self._vecs is None:
            return []
        fetch_k = min(self.config.fetch_k, n)

        qv = self._embed([query])[0]
        sims = self._vecs @ qv
        vec_rank = list(np.argsort(-sims)[:fetch_k])

        bm = self._bm25_scores(query)
        kw_rank = list(np.argsort(-bm)[:fetch_k]) if bm.any() else []

        # Reciprocal rank fusion over the two ranked index lists.
        k = 60
        fused: dict[int, float] = {}
        for ranked in (vec_rank, kw_rank):
            for rank, idx in enumerate(ranked):
                idx = int(idx)
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)

        order = sorted(fused, key=lambda i: fused[i], reverse=True)[: self.config.top_k]
        return [
            Retrieved(
                id=self._ids[i],
                text=self._docs[i],
                source=str(self._metas[i].get("source", "unknown")),
                score=float(fused[i]),
                metadata=self._metas[i],
            )
            for i in order
        ]
