"""RagService: the facade the API layer talks to.

Ties together the config, the hybrid store, and the indexer, and generates
grounded answers with citations using an Ollama chat model through its
OpenAI-compatible endpoint. Built lazily so importing this module (and starting
the app) never loads heavy deps or contacts Ollama.
"""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from .config import RagConfig, load_rag_config
from .index import Indexer
from .store import HybridStore, Retrieved, check_dependencies

ANSWER_SYSTEM_PROMPT = (
    "You answer questions using ONLY the provided transcript excerpts. "
    "Each excerpt is tagged with a [source] label. Cite the sources you use "
    "inline like [source]. If the excerpts do not contain the answer, say you "
    "don't have that information in the transcripts. Be concise and factual."
)


@dataclass
class Citation:
    source: str
    score: float
    snippet: str


@dataclass
class Answer:
    answer: str
    citations: list[Citation]


class RagService:
    """Local RAG over transcripts. Instantiate once; construct lazily."""

    def __init__(self, config: RagConfig | None = None):
        self.config = config or load_rag_config()
        self._store: HybridStore | None = None
        self._indexer: Indexer | None = None
        self._chat: OpenAI | None = None

    # -- lifecycle ---------------------------------------------------------

    @property
    def store(self) -> HybridStore:
        if self._store is None:
            self._store = HybridStore(self.config)
        return self._store

    @property
    def indexer(self) -> Indexer:
        if self._indexer is None:
            self._indexer = Indexer(self.config, self.store)
        return self._indexer

    def _chat_client(self) -> OpenAI:
        if self._chat is None:
            self._chat = OpenAI(
                base_url=self.config.openai_base_url, api_key="ollama"
            )
        return self._chat

    def status(self) -> dict:
        """Report readiness without loading models or contacting Ollama."""
        deps_ok, reason = check_dependencies()
        indexed = None
        if deps_ok:
            try:
                indexed = self.store.count()
            except Exception as exc:  # noqa: BLE001 - report, don't crash
                reason = f"store unavailable: {exc}"
                deps_ok = False
        return {
            "enabled": self.config.enabled,
            "available": deps_ok and self.config.enabled,
            "reason": reason if not (deps_ok and self.config.enabled) else "ok",
            "embed_model": self.config.embed_model,
            "llm_model": self.config.llm_model,
            "ollama_base_url": self.config.ollama_base_url,
            "indexed_chunks": indexed,
        }

    # -- operations --------------------------------------------------------

    def index_transcript(self, text: str, source: str) -> int:
        """Index a transcript so it becomes searchable. Returns chunks written."""
        return self.indexer.index_source(
            source=source, text=text, extra_meta={"kind": "transcript"}
        )

    def index_docs_dir(self) -> int:
        return self.indexer.index_docs_dir()

    def ask(self, question: str) -> Answer:
        """Retrieve relevant chunks and generate a cited, grounded answer."""
        hits: list[Retrieved] = self.store.search(question)
        if not hits:
            return Answer(
                answer=(
                    "I don't have anything indexed yet that answers that. "
                    "Index some transcripts first."
                ),
                citations=[],
            )

        context = "\n\n".join(f"[{h.source}] {h.text}" for h in hits)
        resp = self._chat_client().chat.completions.create(
            model=self.config.llm_model,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Transcript excerpts:\n{context}\n\nQuestion: {question}",
                },
            ],
            temperature=0.2,
        )
        answer_text = (resp.choices[0].message.content or "").strip()
        citations = [
            Citation(source=h.source, score=round(h.score, 4), snippet=h.text[:240])
            for h in hits
        ]
        return Answer(answer=answer_text, citations=citations)
