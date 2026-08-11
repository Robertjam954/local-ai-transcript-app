"""Hybrid retrieval store: ChromaDB (dense vectors) + BM25 (sparse), fused with
reciprocal rank fusion and optionally reranked with a CrossEncoder.

Adapted from ObsidianRAG's retrieval design, kept dependency-light: embeddings
are computed by Ollama through its OpenAI-compatible API (reusing the `openai`
client the app already depends on), so ChromaDB stores precomputed vectors and
never downloads an embedding model of its own.

Heavy imports (chromadb, rank_bm25, sentence_transformers) are performed lazily
inside methods so this module is importable even when the `rag` extra is not
installed. Call `check_dependencies()` to get an actionable status first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from openai import OpenAI

from .config import RagConfig


@dataclass
class Retrieved:
    """A single retrieved chunk with its provenance and fused score."""

    id: str
    text: str
    source: str
    score: float
    metadata: dict = field(default_factory=dict)


def check_dependencies() -> tuple[bool, str]:
    """Return (ok, reason). `reason` explains what to install when not ok."""
    missing: list[str] = []
    try:
        import chromadb  # noqa: F401
    except ImportError:
        missing.append("chromadb")
    try:
        import rank_bm25  # noqa: F401
    except ImportError:
        missing.append("rank-bm25")
    if missing:
        pkgs = " ".join(missing)
        return False, f"Missing RAG dependencies: {pkgs}. Install with: uv sync --extra rag"
    return True, "ok"


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class HybridStore:
    """Persistent hybrid vector + keyword store over transcript chunks."""

    def __init__(self, config: RagConfig):
        self.config = config
        self._client = None
        self._collection = None
        self._embed_client: OpenAI | None = None
        self._reranker = None
        # In-memory BM25 index, rebuilt from the collection when it goes stale.
        self._bm25 = None
        self._bm25_ids: list[str] = []
        self._bm25_docs: list[str] = []
        self._bm25_dirty = True

    # -- lazy resources ----------------------------------------------------

    def _collection_handle(self):
        if self._collection is None:
            import chromadb

            self.config.vector_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.config.vector_dir))
            self._collection = self._client.get_or_create_collection(
                name=self.config.collection,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _embedder(self) -> OpenAI:
        if self._embed_client is None:
            # api_key is required by the client but ignored by Ollama.
            self._embed_client = OpenAI(
                base_url=self.config.openai_base_url, api_key="ollama"
            )
        return self._embed_client

    def _embed(self, texts: list[str]) -> list[list[float]]:
        resp = self._embedder().embeddings.create(
            model=self.config.embed_model, input=texts
        )
        return [item.embedding for item in resp.data]

    # -- writes ------------------------------------------------------------

    def add(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        """Upsert chunks. Embeddings are computed via Ollama."""
        if not ids:
            return
        collection = self._collection_handle()
        embeddings = self._embed(texts)
        collection.upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
        )
        self._bm25_dirty = True

    def delete_source(self, source: str) -> None:
        """Remove all chunks belonging to a source before re-indexing it."""
        collection = self._collection_handle()
        collection.delete(where={"source": source})
        self._bm25_dirty = True

    def count(self) -> int:
        return self._collection_handle().count()

    def list_sources(self) -> list[str]:
        """Distinct source names across all stored chunks, in first-seen order."""
        got = self._collection_handle().get(include=["metadatas"])
        seen: list[str] = []
        for meta in got.get("metadatas") or []:
            source = (meta or {}).get("source")
            if source and source not in seen:
                seen.append(source)
        return seen

    def get_by_source(self, source: str) -> str:
        """Full text of one source, chunks concatenated in chunk order.

        Returns "" when the source is unknown.
        """
        got = self._collection_handle().get(
            where={"source": source}, include=["documents", "metadatas"]
        )
        docs = got.get("documents") or []
        metas = got.get("metadatas") or []
        pairs = sorted(
            zip(metas, docs), key=lambda pair: (pair[0] or {}).get("chunk", 0)
        )
        return "\n".join(doc for _, doc in pairs).strip()

    # -- retrieval ---------------------------------------------------------

    def _ensure_bm25(self) -> None:
        if not self._bm25_dirty and self._bm25 is not None:
            return
        from rank_bm25 import BM25Okapi

        collection = self._collection_handle()
        data = collection.get(include=["documents"])
        self._bm25_ids = data.get("ids", []) or []
        self._bm25_docs = data.get("documents", []) or []
        if self._bm25_docs:
            self._bm25 = BM25Okapi([_tokenize(d) for d in self._bm25_docs])
        else:
            self._bm25 = None
        self._bm25_dirty = False

    def _vector_hits(self, query: str) -> list[tuple[str, str, dict]]:
        collection = self._collection_handle()
        qvec = self._embed([query])[0]
        res = collection.query(
            query_embeddings=[qvec],
            n_results=self.config.fetch_k,
            include=["documents", "metadatas"],
        )
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        return list(zip(ids, docs, metas, strict=False))

    def _bm25_hits(self, query: str) -> list[tuple[str, str, dict]]:
        self._ensure_bm25()
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[: self.config.fetch_k]
        collection = self._collection_handle()
        ids = [self._bm25_ids[i] for i in ranked]
        if not ids:
            return []
        got = collection.get(ids=ids, include=["documents", "metadatas"])
        gid = got.get("ids", []) or []
        gdocs = got.get("documents", []) or []
        gmetas = got.get("metadatas", []) or []
        return list(zip(gid, gdocs, gmetas, strict=False))

    def search(self, query: str) -> list[Retrieved]:
        """Hybrid search: dense + sparse, fused with reciprocal rank fusion,
        optionally reranked with a CrossEncoder. Returns top_k results."""
        vector = self._vector_hits(query)
        keyword = self._bm25_hits(query)

        # Reciprocal rank fusion over the two ranked lists.
        k = 60
        fused: dict[str, float] = {}
        payload: dict[str, tuple[str, dict]] = {}
        for ranked in (vector, keyword):
            for rank, (cid, doc, meta) in enumerate(ranked):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (k + rank + 1)
                payload.setdefault(cid, (doc, meta or {}))

        order = sorted(fused, key=lambda c: fused[c], reverse=True)
        candidates = [
            Retrieved(
                id=cid,
                text=payload[cid][0],
                source=str(payload[cid][1].get("source", "unknown")),
                score=fused[cid],
                metadata=payload[cid][1],
            )
            for cid in order
        ]

        if self.config.rerank and candidates:
            candidates = self._rerank(query, candidates)
        return candidates[: self.config.top_k]

    def _rerank(self, query: str, candidates: list[Retrieved]) -> list[Retrieved]:
        try:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(self.config.rerank_model)
            pairs = [(query, c.text) for c in candidates]
            scores = self._reranker.predict(pairs)
            for c, s in zip(candidates, scores, strict=False):
                c.score = float(s)
            candidates.sort(key=lambda c: c.score, reverse=True)
        except ImportError:
            # sentence-transformers not installed: keep RRF order silently.
            pass
        return candidates
