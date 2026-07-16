"""Chunking and incremental indexing.

Splits documents into overlapping character windows and tracks a content hash
per source so unchanged sources are skipped on re-index (the incremental-index
pattern from ObsidianRAG). Transcripts are indexed by id; a docs directory can
also be ingested as an extra corpus.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import RagConfig
from .store import HybridStore


def chunk_text(text: str, chunk_chars: int, overlap: int) -> list[str]:
    """Split text into overlapping windows on whitespace boundaries."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    step = max(1, chunk_chars - overlap)
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        window = text[start:end]
        # Prefer to break on the last whitespace inside the window.
        if end < len(text):
            cut = window.rfind(" ")
            if cut > chunk_chars // 2:
                window = window[:cut]
        chunks.append(window.strip())
        start += step
    return [c for c in chunks if c]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class Indexer:
    """Indexes transcripts and files into the HybridStore, incrementally."""

    def __init__(self, config: RagConfig, store: HybridStore):
        self.config = config
        self.store = store
        self._tracker_path = config.vector_dir / "index_state.json"

    def _load_tracker(self) -> dict[str, str]:
        if self._tracker_path.exists():
            try:
                return json.loads(self._tracker_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_tracker(self, tracker: dict[str, str]) -> None:
        self._tracker_path.parent.mkdir(parents=True, exist_ok=True)
        self._tracker_path.write_text(json.dumps(tracker, indent=2))

    def index_source(self, source: str, text: str, extra_meta: dict | None = None) -> int:
        """Index one source (a transcript or document). Returns chunks written.

        If the source was previously indexed with identical content it is
        skipped; if it changed, its old chunks are replaced.
        """
        tracker = self._load_tracker()
        digest = _hash(text)
        if tracker.get(source) == digest:
            return 0  # unchanged

        if source in tracker:
            self.store.delete_source(source)

        chunks = chunk_text(text, self.config.chunk_chars, self.config.chunk_overlap)
        if not chunks:
            return 0
        ids = [f"{_hash(source)}:{i}" for i in range(len(chunks))]
        metas = [
            {"source": source, "chunk": i, **(extra_meta or {})}
            for i in range(len(chunks))
        ]
        self.store.add(ids=ids, texts=chunks, metadatas=metas)

        tracker[source] = digest
        self._save_tracker(tracker)
        return len(chunks)

    def index_docs_dir(self) -> int:
        """Index every .txt/.md file under the configured docs directory."""
        docs = self.config.docs_dir
        if not docs.exists():
            return 0
        total = 0
        for path in sorted(docs.rglob("*")):
            if path.suffix.lower() in {".txt", ".md"} and path.is_file():
                total += self.index_source(
                    source=str(path.relative_to(docs)),
                    text=path.read_text(encoding="utf-8", errors="ignore"),
                    extra_meta={"kind": "document"},
                )
        return total
