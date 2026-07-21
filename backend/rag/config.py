"""Configuration for the local RAG subsystem, loaded from environment variables.

All values have working local-first defaults so that, once the optional deps and
Ollama are installed, RAG works with no extra configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RagConfig:
    """Resolved RAG settings. Immutable snapshot of the environment."""

    enabled: bool
    ollama_base_url: str  # e.g. http://localhost:11434 (no /v1 suffix)
    embed_model: str  # Ollama embedding model, e.g. nomic-embed-text
    llm_model: str  # Ollama chat model used to generate grounded answers
    vector_dir: Path  # ChromaDB persistent directory
    docs_dir: Path  # optional corpus of extra documents to index
    collection: str  # ChromaDB collection name
    chunk_chars: int  # target chunk size in characters
    chunk_overlap: int  # overlap between adjacent chunks in characters
    top_k: int  # chunks returned to the LLM after reranking
    fetch_k: int  # candidates pulled from each retriever before fusion
    rerank: bool  # enable CrossEncoder reranking (needs sentence-transformers)
    rerank_model: str

    @property
    def openai_base_url(self) -> str:
        """Ollama's OpenAI-compatible endpoint, used via the `openai` client."""
        return self.ollama_base_url.rstrip("/") + "/v1"


def load_rag_config() -> RagConfig:
    """Build a RagConfig from environment variables (see .env.example)."""
    backend_dir = Path(__file__).resolve().parent.parent
    default_data = backend_dir / "rag_data"
    return RagConfig(
        enabled=_as_bool(os.getenv("RAG_ENABLED"), default=False),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.getenv("RAG_EMBED_MODEL", "nomic-embed-text"),
        llm_model=os.getenv("RAG_LLM_MODEL", "gemma3"),
        vector_dir=Path(os.getenv("RAG_VECTOR_DIR", str(default_data / "chroma"))),
        docs_dir=Path(os.getenv("RAG_DOCS_DIR", str(default_data / "docs"))),
        collection=os.getenv("RAG_COLLECTION", "transcripts"),
        chunk_chars=int(os.getenv("RAG_CHUNK_CHARS", "1200")),
        chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
        fetch_k=int(os.getenv("RAG_FETCH_K", "20")),
        rerank=_as_bool(os.getenv("RAG_RERANK"), default=False),
        rerank_model=os.getenv(
            "RAG_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        ),
    )
