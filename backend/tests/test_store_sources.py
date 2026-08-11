from rag.config import load_rag_config
from rag.store_numpy import NumpyStore


def _store(tmp_path, monkeypatch):
    monkeypatch.setenv("RAG_VECTOR_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("RAG_DOCS_DIR", str(tmp_path / "docs"))
    store = NumpyStore(load_rag_config())
    # Seed the in-memory index directly (bypass embeddings / Ollama).
    store._ids = ["a:0", "a:1", "b:0"]
    store._docs = ["alpha one", "alpha two", "beta only"]
    store._metas = [
        {"source": "a.txt", "chunk": 1},
        {"source": "a.txt", "chunk": 0},
        {"source": "b.txt", "chunk": 0},
    ]
    return store


def test_list_sources_is_distinct_and_ordered(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    assert store.list_sources() == ["a.txt", "b.txt"]


def test_get_by_source_joins_chunks_in_chunk_order(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    # chunk 0 ("alpha two") must come before chunk 1 ("alpha one").
    assert store.get_by_source("a.txt") == "alpha two\nalpha one"


def test_get_by_source_unknown_returns_empty(tmp_path, monkeypatch):
    store = _store(tmp_path, monkeypatch)
    assert store.get_by_source("missing.txt") == ""
