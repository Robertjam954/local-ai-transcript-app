"""Local, fully-offline RAG + search over transcripts.

Design adapted from ObsidianRAG (https://github.com/Vasallo94/ObsidianRAG):
hybrid vector + BM25 retrieval, CrossEncoder reranking, incremental indexing,
and answers with source citations. This implementation stays deliberately lean
and 100% local by using ChromaDB for the vector store and Ollama (via its
OpenAI-compatible endpoint) for both embeddings and generation, instead of the
full LangChain/LangGraph stack.

Everything here is optional and feature-flagged. The heavy third-party
dependencies (chromadb, rank-bm25, optional sentence-transformers) are declared
as the `rag` optional-dependency extra and are imported lazily, so the core
transcription app runs unchanged when RAG is disabled or its deps are absent.
"""

from __future__ import annotations

from .config import RagConfig, load_rag_config

__all__ = ["RagConfig", "load_rag_config"]
