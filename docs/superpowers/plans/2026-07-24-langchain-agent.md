# LangChain Transcript Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a feature-flagged, tool-using LangChain `create_agent` assistant over indexed transcripts, exposed via `/api/agent/*`, without touching the core transcription app.

**Architecture:** A self-contained `backend/agent/` package (config + tools + service) mirroring the existing `backend/rag/` package. The agent reuses the RAG store for retrieval and the existing OpenAI-compatible/Ollama LLM env for reasoning. Routes and imports are lazy and dependency-guarded so the app runs fine when the agent is disabled or LangChain is absent.

**Tech Stack:** Python 3.12, FastAPI, LangChain v1 (`langchain.agents.create_agent`), `langchain-openai` (`ChatOpenAI`), the `openai` client (already used), the existing `rag` store (Numpy or Chroma), pytest.

## Global Constraints

- All new deps are an **optional** extra `agent = ["langchain>=1.0", "langchain-openai>=0.3"]`; guard every LangChain import so the core app runs without them. Do **not** add them to default `requirements.txt` (matches how the `rag` extra is handled).
- Feature flag `AGENT_ENABLED` (default `false`). Reuse `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` from the existing transcription config; no new cloud provider.
- Everything lazy: importing any module must not load LangChain, load models, or contact Ollama.
- All tests are offline and network-free (no live Ollama, no model downloads).
- No em dashes in code or docs; use a single hyphen `-`. Match existing file style (module docstrings, `from __future__ import annotations`, `# noqa: BLE001` on broad excepts that report-and-continue).
- Work on the current branch. Commit after every task.

---

### Task 1: Store source-listing helpers (`list_sources`, `get_by_source`)

**Files:**
- Modify: `backend/rag/store_numpy.py` (add two methods to `NumpyStore`)
- Modify: `backend/rag/store.py` (add two methods to `HybridStore`)
- Test: `backend/tests/test_store_sources.py`

**Interfaces:**
- Consumes: `RagConfig` (`rag/config.py`), `NumpyStore._ids/_docs/_metas`, `HybridStore._collection_handle()`. Chunk metadata shape is `{"source": str, "chunk": int, "kind": str}`.
- Produces (relied on by Task 3):
  - `NumpyStore.list_sources() -> list[str]`, `NumpyStore.get_by_source(source: str) -> str`
  - `HybridStore.list_sources() -> list[str]`, `HybridStore.get_by_source(source: str) -> str`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/__init__.py` (empty) and `backend/tests/test_store_sources.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_store_sources.py -v`
Expected: FAIL with `AttributeError: 'NumpyStore' object has no attribute 'list_sources'`

- [ ] **Step 3: Add the methods to `NumpyStore`**

In `backend/rag/store_numpy.py`, add these methods to `NumpyStore` (e.g. right after `count`):

```python
    def list_sources(self) -> list[str]:
        """Distinct source names across all stored chunks, in first-seen order."""
        seen: list[str] = []
        for meta in self._metas:
            source = meta.get("source")
            if source and source not in seen:
                seen.append(source)
        return seen

    def get_by_source(self, source: str) -> str:
        """Full text of one source, chunks concatenated in chunk order.

        Returns "" when the source is unknown.
        """
        pairs = [
            (self._metas[i].get("chunk", 0), self._docs[i])
            for i in range(len(self._ids))
            if self._metas[i].get("source") == source
        ]
        pairs.sort(key=lambda p: p[0])
        return "\n".join(doc for _, doc in pairs).strip()
```

- [ ] **Step 4: Add the mirror methods to `HybridStore`**

In `backend/rag/store.py`, add to `HybridStore` (e.g. after `count`):

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_store_sources.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/rag/store_numpy.py backend/rag/store.py backend/tests/__init__.py backend/tests/test_store_sources.py
git commit -m "feat(rag): add list_sources and get_by_source to both stores"
```

---

### Task 2: Agent config (`agent/config.py`)

**Files:**
- Create: `backend/agent/__init__.py` (empty)
- Create: `backend/agent/config.py`
- Test: `backend/tests/test_agent_config.py`

**Interfaces:**
- Consumes: environment variables.
- Produces (relied on by Tasks 3-5):
  - `AgentConfig` frozen dataclass: `enabled: bool`, `base_url: str`, `api_key: str`, `model: str`, `temperature: float`, `max_iterations: int`
  - `load_agent_config() -> AgentConfig`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_config.py`:

```python
from agent.config import AgentConfig, load_agent_config


def test_defaults_disabled_and_reuse_llm_env(monkeypatch):
    monkeypatch.delenv("AGENT_ENABLED", raising=False)
    monkeypatch.delenv("AGENT_MODEL", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "gemma3:4b")
    cfg = load_agent_config()
    assert isinstance(cfg, AgentConfig)
    assert cfg.enabled is False
    assert cfg.base_url == "http://ollama:11434/v1"
    assert cfg.model == "gemma3:4b"
    assert cfg.temperature == 0.2
    assert cfg.max_iterations == 6


def test_agent_model_overrides_llm_model_and_enable_flag(monkeypatch):
    monkeypatch.setenv("AGENT_ENABLED", "true")
    monkeypatch.setenv("LLM_MODEL", "gemma3:4b")
    monkeypatch.setenv("AGENT_MODEL", "qwen2.5:7b")
    monkeypatch.setenv("AGENT_TEMPERATURE", "0.5")
    monkeypatch.setenv("AGENT_MAX_ITERATIONS", "9")
    cfg = load_agent_config()
    assert cfg.enabled is True
    assert cfg.model == "qwen2.5:7b"
    assert cfg.temperature == 0.5
    assert cfg.max_iterations == 9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent'`

- [ ] **Step 3: Create the package and config**

Create empty `backend/agent/__init__.py`. Create `backend/agent/config.py`:

```python
"""Configuration for the optional agentic assistant, loaded from environment.

Reuses the OpenAI-compatible LLM settings the transcription app already uses
(LLM_BASE_URL / LLM_API_KEY / LLM_MODEL) so the agent stays local-first. The
agent is off unless AGENT_ENABLED is set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AgentConfig:
    """Resolved agent settings. Immutable snapshot of the environment."""

    enabled: bool
    base_url: str  # OpenAI-compatible endpoint, e.g. http://ollama:11434/v1
    api_key: str  # required by the client, ignored by Ollama
    model: str  # chat model the agent reasons with
    temperature: float
    max_iterations: int  # cap on agent tool-loop steps


def load_agent_config() -> AgentConfig:
    """Build an AgentConfig from environment variables (see .env.example)."""
    return AgentConfig(
        enabled=_as_bool(os.getenv("AGENT_ENABLED"), default=False),
        base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.getenv("LLM_API_KEY", "ollama"),
        model=os.getenv("AGENT_MODEL") or os.getenv("LLM_MODEL", "gemma3"),
        temperature=float(os.getenv("AGENT_TEMPERATURE", "0.2")),
        max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "6")),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_agent_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/agent/__init__.py backend/agent/config.py backend/tests/test_agent_config.py
git commit -m "feat(agent): add AgentConfig loaded from LLM env"
```

---

### Task 3: Agent tools (`agent/tools.py`)

**Files:**
- Create: `backend/agent/tools.py`
- Test: `backend/tests/test_agent_tools.py`

**Interfaces:**
- Consumes: a store implementing `search(query) -> list[Retrieved]`, `list_sources() -> list[str]`, `get_by_source(source) -> str` (Task 1); an `openai`-style client with `.chat.completions.create(...)`. `Retrieved` has `.source: str`, `.text: str`, `.score: float`.
- Produces (relied on by Task 4):
  - `configure(store, llm_client, llm_model) -> None`
  - `reset_run_state() -> None`, `get_citations() -> list[dict]`
  - `_search_impl(query) -> str`, `_list_impl() -> str`, `_summarize_impl(source) -> str`, `_actions_impl(source) -> str`
  - `TOOLS` (list of 4 LangChain tools named `search_transcripts`, `list_transcripts`, `summarize_transcript`, `extract_action_items`)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_tools.py`:

```python
from dataclasses import dataclass

import agent.tools as t


@dataclass
class FakeHit:
    source: str
    text: str
    score: float


class FakeStore:
    def __init__(self):
        self._by_source = {"a.txt": "full alpha text", "b.txt": "full beta text"}

    def search(self, query):
        if "nothing" in query:
            return []
        return [FakeHit("a.txt", "alpha snippet", 0.9)]

    def list_sources(self):
        return ["a.txt", "b.txt"]

    def get_by_source(self, source):
        return self._by_source.get(source, "")


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeCompletions:
    def create(self, **kwargs):
        # Echo the system instruction so the test can assert routing.
        system = kwargs["messages"][0]["content"]
        tag = "SUMMARY" if "Summarize" in system else "ACTIONS"
        return type("R", (), {"choices": [FakeChoice(f"{tag}-ok")]})()


class FakeLLM:
    def __init__(self):
        self.chat = type("C", (), {"completions": FakeCompletions()})()


def setup_function():
    t.configure(store=FakeStore(), llm_client=FakeLLM(), llm_model="m")
    t.reset_run_state()


def test_search_returns_tagged_snippets_and_records_citations():
    out = t._search_impl("alpha")
    assert "[a.txt] alpha snippet" in out
    cites = t.get_citations()
    assert cites == [{"source": "a.txt", "score": 0.9, "snippet": "alpha snippet"}]


def test_search_empty_is_graceful():
    assert "No matching" in t._search_impl("nothing here")
    assert t.get_citations() == []


def test_list_transcripts():
    assert t._list_impl() == "- a.txt\n- b.txt"


def test_summarize_routes_to_summary_prompt():
    assert t._summarize_impl("a.txt") == "SUMMARY-ok"


def test_extract_routes_to_actions_prompt():
    assert t._actions_impl("a.txt") == "ACTIONS-ok"


def test_summarize_unknown_source_is_graceful():
    assert "No transcript found" in t._summarize_impl("missing.txt")


def test_tools_are_exported_with_expected_names():
    names = {tool.name for tool in t.TOOLS}
    assert names == {
        "search_transcripts",
        "list_transcripts",
        "summarize_transcript",
        "extract_action_items",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.tools'`

- [ ] **Step 3: Implement the tools**

Create `backend/agent/tools.py`:

```python
"""LangChain tools the transcript agent can call.

Each tool is a thin @tool wrapper around a plain module function so the logic
stays testable without going through LangChain's tool-invocation machinery.
The store and LLM client are injected via configure() (called by AgentService,
or directly by tests) rather than imported as hard globals, keeping tools
decoupled and offline-testable.
"""

from __future__ import annotations

from langchain.tools import tool

_store = None
_llm_client = None
_llm_model: str | None = None
_citations: list[dict] = []

_SUMMARY_SYSTEM = (
    "Summarize the transcript below in 3-6 concise sentences. Be factual and "
    "do not invent details."
)
_ACTIONS_SYSTEM = (
    "Extract concrete action items, decisions, and owners from the transcript "
    "below as a short bulleted list. If there are none, reply 'No action items "
    "found.'"
)


def configure(store, llm_client, llm_model: str) -> None:
    """Inject the retrieval store and LLM client the tools use."""
    global _store, _llm_client, _llm_model
    _store = store
    _llm_client = llm_client
    _llm_model = llm_model


def reset_run_state() -> None:
    """Clear per-request state (citations) before an agent run."""
    _citations.clear()


def get_citations() -> list[dict]:
    """Citations collected by search_transcripts during the current run."""
    return list(_citations)


def _require_store():
    if _store is None:
        raise RuntimeError("agent tools not configured: store is None")
    return _store


def _require_llm():
    if _llm_client is None or _llm_model is None:
        raise RuntimeError("agent tools not configured: llm is None")
    return _llm_client, _llm_model


def _summarize_with(system: str, text: str) -> str:
    client, model = _require_llm()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()


def _search_impl(query: str) -> str:
    hits = _require_store().search(query)
    if not hits:
        return (
            "No matching transcript passages were found. Nothing may be indexed "
            "yet - the user can index transcripts first."
        )
    lines = []
    for hit in hits:
        _citations.append(
            {
                "source": hit.source,
                "score": round(float(hit.score), 4),
                "snippet": hit.text[:240],
            }
        )
        lines.append(f"[{hit.source}] {hit.text}")
    return "\n\n".join(lines)


def _list_impl() -> str:
    sources = _require_store().list_sources()
    if not sources:
        return "No transcripts are indexed yet."
    return "\n".join(f"- {source}" for source in sources)


def _summarize_impl(source: str) -> str:
    text = _require_store().get_by_source(source)
    if not text:
        return (
            f"No transcript found for source '{source}'. Use list_transcripts to "
            "see available sources."
        )
    return _summarize_with(_SUMMARY_SYSTEM, text)


def _actions_impl(source: str) -> str:
    text = _require_store().get_by_source(source)
    if not text:
        return (
            f"No transcript found for source '{source}'. Use list_transcripts to "
            "see available sources."
        )
    return _summarize_with(_ACTIONS_SYSTEM, text)


@tool
def search_transcripts(query: str) -> str:
    """Search indexed transcripts for passages relevant to the query. Returns
    snippets tagged with their [source] label. Use this to ground answers in the
    user's recordings and to cite sources."""
    return _search_impl(query)


@tool
def list_transcripts() -> str:
    """List the distinct transcript sources currently indexed. Use this to
    discover what recordings exist and to find valid source names for
    summarize_transcript and extract_action_items."""
    return _list_impl()


@tool
def summarize_transcript(source: str) -> str:
    """Summarize a single transcript identified by its exact source name (as
    returned by list_transcripts)."""
    return _summarize_impl(source)


@tool
def extract_action_items(source: str) -> str:
    """Extract action items, decisions, and owners from a single transcript
    identified by its exact source name (as returned by list_transcripts)."""
    return _actions_impl(source)


TOOLS = [
    search_transcripts,
    list_transcripts,
    summarize_transcript,
    extract_action_items,
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent_tools.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/agent/tools.py backend/tests/test_agent_tools.py
git commit -m "feat(agent): add transcript tools (search/list/summarize/extract)"
```

---

### Task 4: Agent service (`agent/service.py`)

**Files:**
- Create: `backend/agent/service.py`
- Test: `backend/tests/test_agent_service.py`

**Interfaces:**
- Consumes: `AgentConfig` / `load_agent_config` (Task 2); `agent.tools.configure/reset_run_state/get_citations/TOOLS` (Task 3); `rag.config.load_rag_config` and `rag.service._build_store` (existing); `langchain_openai.ChatOpenAI`; `langchain.agents.create_agent`.
- Produces (relied on by Task 5):
  - `AgentAnswer` dataclass: `answer: str`, `tool_calls: list[dict]`, `citations: list[dict]`
  - `AgentService(config: AgentConfig | None = None)` with `.config`, `.ask(question: str) -> AgentAnswer`, `.status() -> dict`
  - `_parse_messages(messages) -> tuple[str, list[dict]]` (module function, unit-tested)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_service.py`:

```python
from agent.config import AgentConfig
from agent.service import AgentAnswer, AgentService, _parse_messages


class FakeMsg:
    """Mimics a LangChain message (duck-typed for _parse_messages)."""

    def __init__(self, type_, content="", tool_calls=None, tool_call_id=None):
        self.type = type_
        self.content = content
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id


def test_parse_messages_extracts_answer_and_tool_trace():
    messages = [
        FakeMsg("human", "summarize a.txt"),
        FakeMsg(
            "ai",
            "",
            tool_calls=[{"name": "summarize_transcript", "args": {"source": "a.txt"}, "id": "c1"}],
        ),
        FakeMsg("tool", "SUMMARY-ok", tool_call_id="c1"),
        FakeMsg("ai", "Here is the summary."),
    ]
    answer, trace = _parse_messages(messages)
    assert answer == "Here is the summary."
    assert trace == [
        {
            "tool": "summarize_transcript",
            "arguments": {"source": "a.txt"},
            "output_preview": "SUMMARY-ok",
        }
    ]


def _cfg(enabled=True):
    return AgentConfig(
        enabled=enabled,
        base_url="http://x/v1",
        api_key="k",
        model="m",
        temperature=0.2,
        max_iterations=6,
    )


class FakeAgent:
    def __init__(self):
        self.last_config = None

    def invoke(self, payload, config=None):
        self.last_config = config
        return {
            "messages": [
                FakeMsg("human", payload["messages"][0]["content"]),
                FakeMsg("ai", "final answer"),
            ]
        }


def test_ask_returns_answer_and_sets_recursion_limit():
    svc = AgentService(config=_cfg())
    fake = FakeAgent()
    svc._agent = fake  # bypass building a real LangChain agent
    result = svc.ask("hello")
    assert isinstance(result, AgentAnswer)
    assert result.answer == "final answer"
    assert result.tool_calls == []
    assert result.citations == []
    # max_iterations 6 -> recursion_limit 13
    assert fake.last_config == {"recursion_limit": 13}


def test_status_disabled_reports_unavailable_without_network():
    svc = AgentService(config=_cfg(enabled=False))
    status = svc.status()
    assert status["enabled"] is False
    assert status["available"] is False
    assert "disabled" in status["reason"].lower()
    assert status["tools"] == [
        "search_transcripts",
        "list_transcripts",
        "summarize_transcript",
        "extract_action_items",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.service'`

- [ ] **Step 3: Implement the service**

Create `backend/agent/service.py`:

```python
"""AgentService: the facade the API layer talks to.

Builds a LangChain create_agent over transcript tools, reusing the RAG store
for retrieval and the local OpenAI-compatible endpoint for reasoning. Built
lazily so importing this module never loads LangChain or contacts Ollama.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from . import tools as agent_tools
from .config import AgentConfig, load_agent_config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a meeting assistant over the user's voice transcripts. Answer using "
    "the transcripts only. Use search_transcripts to find relevant passages, "
    "list_transcripts to see what recordings exist, and summarize_transcript / "
    "extract_action_items for a named transcript. Cite sources inline as "
    "[source]. If the transcripts do not cover the question, say so plainly and "
    "do not invent details. Be concise."
)


@dataclass
class AgentAnswer:
    answer: str
    tool_calls: list[dict]
    citations: list[dict]


def _parse_messages(messages) -> tuple[str, list[dict]]:
    """Turn a LangChain message list into (final answer, tool-call trace)."""
    tool_outputs: dict[str, str] = {}
    for msg in messages:
        tcid = getattr(msg, "tool_call_id", None)
        if tcid:
            tool_outputs[tcid] = getattr(msg, "content", "") or ""

    answer = ""
    trace: list[dict] = []
    for msg in messages:
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            for call in tool_calls:
                out = tool_outputs.get(call.get("id"), "")
                trace.append(
                    {
                        "tool": call.get("name"),
                        "arguments": call.get("args"),
                        "output_preview": (out or "")[:300],
                    }
                )
        content = getattr(msg, "content", None)
        if content and not tool_calls and getattr(msg, "type", "") == "ai":
            answer = content if isinstance(content, str) else str(content)
    return answer.strip(), trace


class AgentService:
    """Tool-using agent over indexed transcripts. Construct lazily."""

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or load_agent_config()
        self._agent = None

    def _ensure_agent(self):
        if self._agent is not None:
            return self._agent
        from langchain.agents import create_agent
        from langchain_openai import ChatOpenAI
        from openai import OpenAI

        from rag.config import load_rag_config
        from rag.service import _build_store

        store, _backend = _build_store(load_rag_config())
        llm_client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)
        agent_tools.configure(
            store=store, llm_client=llm_client, llm_model=self.config.model
        )
        chat = ChatOpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model,
            temperature=self.config.temperature,
        )
        self._agent = create_agent(
            model=chat, tools=agent_tools.TOOLS, system_prompt=SYSTEM_PROMPT
        )
        return self._agent

    def ask(self, question: str) -> AgentAnswer:
        agent = self._ensure_agent()
        agent_tools.reset_run_state()
        # LangGraph counts each node; ~2 nodes per agent step, +1 headroom.
        recursion_limit = self.config.max_iterations * 2 + 1
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"recursion_limit": recursion_limit},
        )
        answer, trace = _parse_messages(result["messages"])
        return AgentAnswer(
            answer=answer, tool_calls=trace, citations=agent_tools.get_citations()
        )

    def status(self) -> dict:
        available = self.config.enabled
        reason = "ok" if available else "Agent is disabled (set AGENT_ENABLED=true)."
        backend = None
        indexed = None
        if available:
            try:
                from rag.config import load_rag_config
                from rag.service import _build_store

                store, backend = _build_store(load_rag_config())
                indexed = store.count()
            except Exception as exc:  # noqa: BLE001 - report, don't crash
                available = False
                reason = f"store unavailable: {exc}"
        return {
            "enabled": self.config.enabled,
            "available": available,
            "reason": reason,
            "model": self.config.model,
            "base_url": self.config.base_url,
            "tools": [tool.name for tool in agent_tools.TOOLS],
            "store_backend": backend,
            "indexed_chunks": indexed,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/agent/service.py backend/tests/test_agent_service.py
git commit -m "feat(agent): add AgentService with create_agent and trace parsing"
```

---

### Task 5: API routes (`/api/agent/status`, `/api/agent/ask`)

**Files:**
- Modify: `backend/app.py` (insert agent routes after the RAG routes, before the static-file mount)
- Test: `backend/tests/test_agent_api.py`

**Interfaces:**
- Consumes: `agent.service.AgentService` (Task 4).
- Produces: HTTP routes `GET /api/agent/status`, `POST /api/agent/ask {question}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_agent_api.py`:

```python
from fastapi.testclient import TestClient

# Import WITHOUT the lifespan context manager so the Whisper-loading startup
# hook never runs (the agent routes do not depend on the transcription service).


def _client(monkeypatch):
    monkeypatch.delenv("AGENT_ENABLED", raising=False)  # disabled by default
    import app as app_module

    app_module._agent_service = None  # reset cached singleton
    return TestClient(app_module.app)


def test_agent_status_reports_disabled(monkeypatch):
    client = _client(monkeypatch)
    resp = client.get("/api/agent/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["enabled"] is False
    assert body["available"] is False


def test_agent_ask_returns_503_when_disabled(monkeypatch):
    client = _client(monkeypatch)
    resp = client.post("/api/agent/ask", json={"question": "hello"})
    assert resp.status_code == 503
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent_api.py -v`
Expected: FAIL with 404 on `/api/agent/status` (routes not defined yet)

- [ ] **Step 3: Add the routes to `app.py`**

In `backend/app.py`, insert the following AFTER the `rag_ask` route (currently ends near line 205) and BEFORE the `# Serve the built React SPA` static-mount block. It mirrors the RAG routes' lazy + guarded pattern:

```python
# --------------------------------------------------------------------------
# Optional agentic assistant over transcripts (LangChain create_agent).
# Same lazy + guarded pattern as the RAG routes above: heavy deps (langchain)
# load only when the agent is used, and the routes degrade to 503 when the
# agent is disabled or its deps are absent. See backend/agent/.
# --------------------------------------------------------------------------

_agent_service = None


class AgentAskRequest(BaseModel):
    question: str


def _get_agent_service():
    """Lazily construct the AgentService, or return None with a reason string."""
    global _agent_service
    if _agent_service is not None:
        return _agent_service, None
    try:
        from agent.service import AgentService
    except Exception as e:  # noqa: BLE001 - surface import issues to the caller
        return None, f"Agent unavailable: {e}"
    _agent_service = AgentService()
    return _agent_service, None


@app.get("/api/agent/status")
async def agent_status():
    svc, reason = _get_agent_service()
    if svc is None:
        return {"enabled": False, "available": False, "reason": reason}
    return svc.status()


@app.post("/api/agent/ask")
async def agent_ask(request: AgentAskRequest):
    svc, reason = _get_agent_service()
    if svc is None or not svc.config.enabled:
        raise HTTPException(
            status_code=503,
            detail=reason
            or "Agent is disabled. Set AGENT_ENABLED=true and install the agent extra.",
        )
    try:
        result = svc.ask(request.question)
        return {
            "success": True,
            "answer": result.answer,
            "tool_calls": result.tool_calls,
            "citations": result.citations,
        }
    except Exception as e:
        print(f"❌ Agent query failed: {e}")
        raise HTTPException(
            status_code=502, detail="Agent query failed. Check the backend terminal."
        ) from e
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_agent_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run the full test suite**

Run: `cd backend && python -m pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/tests/test_agent_api.py
git commit -m "feat(agent): expose /api/agent/status and /api/agent/ask routes"
```

---

### Task 6: Dependencies, env, and docs

**Files:**
- Modify: `backend/pyproject.toml` (add the `agent` optional extra)
- Modify: `backend/.env.example` (add the Agent section)
- Modify: `README.md` (add an Agent subsection) and `CLAUDE.md` if present (note the new package/routes/flag)

**Interfaces:** none (packaging + docs).

- [ ] **Step 1: Add the optional extra**

In `backend/pyproject.toml`, under `[project.optional-dependencies]` (next to `rag` and `rag-rerank`), add:

```toml
# Agentic assistant over transcripts (LangChain create_agent). Reuses the RAG
# store for retrieval and the OpenAI-compatible LLM env for reasoning.
# Install with: uv sync --extra agent
agent = [
    "langchain>=1.0",
    "langchain-openai>=0.3",
]
```

- [ ] **Step 2: Add the Agent section to `.env.example`**

Append to `backend/.env.example`:

```
# --------------------------------------------------------------------------
# Optional agentic assistant over transcripts (LangChain create_agent).
# Reuses the OpenAI-compatible LLM config above. Install deps then enable:
#   uv sync --extra agent
# Requires transcripts to be indexed via the RAG routes first (RAG_ENABLED=true).
# --------------------------------------------------------------------------
AGENT_ENABLED=false
# AGENT_MODEL=            # defaults to LLM_MODEL
# AGENT_TEMPERATURE=0.2
# AGENT_MAX_ITERATIONS=6
```

- [ ] **Step 3: Document in README (and CLAUDE.md if present)**

Add a short subsection to `README.md` near the RAG notes:

```markdown
### Optional: agentic assistant over transcripts

A LangChain `create_agent` assistant that reasons over your indexed transcripts
with four tools: search, list, summarize, and extract action items. Off by
default and dependency-guarded, like RAG.

    uv sync --extra agent
    # in .env: AGENT_ENABLED=true  (index transcripts via RAG first)

Endpoints: `GET /api/agent/status`, `POST /api/agent/ask {"question": "..."}`
(returns `{answer, tool_calls, citations}`). Reuses the RAG store and the
`LLM_BASE_URL` / `LLM_MODEL` config. See `backend/agent/`.
```

If `CLAUDE.md` exists at the repo root, add a matching one-paragraph note pointing at `backend/agent/` (config/tools/service), the `AGENT_ENABLED` flag, the `agent` extra, and the two routes.

- [ ] **Step 4: Verify the extra resolves and imports work**

Run: `cd backend && python -c "import langchain, langchain_openai; from langchain.agents import create_agent; print('agent deps ok')"`
Expected: prints `agent deps ok` (deps already present in this environment).

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/.env.example README.md CLAUDE.md
git commit -m "docs(agent): add agent extra, env vars, and README/CLAUDE notes"
```

---

## Manual smoke test (after all tasks, needs a local Ollama)

Not automated (requires models). Run once to confirm the end-to-end path:

```bash
cd backend
uv sync --extra rag --extra agent
# .env: RAG_ENABLED=true, AGENT_ENABLED=true, models pulled (nomic-embed-text + a chat model)
uvicorn app:app --reload
# index a transcript, then:
curl -s localhost:8000/api/agent/status | jq
curl -s -X POST localhost:8000/api/agent/ask \
  -H 'content-type: application/json' \
  -d '{"question":"What are the action items from my standup?"}' | jq
```

Expected: a grounded answer, a non-empty `tool_calls` trace, and `citations`.
