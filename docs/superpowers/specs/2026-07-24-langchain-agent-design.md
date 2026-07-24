# LangChain create_agent: agentic assistant over transcripts

Date: 2026-07-24
Status: Approved (design)
Target: `backend/`

## Summary

Add a tool-using agent to the transcript app, built on LangChain v1's
`create_agent` (`from langchain.agents import create_agent`). The agent reasons
in multiple steps and calls tools over the user's indexed transcripts: semantic
search, listing sources, summarizing a transcript, and extracting action items.
It is exposed via new `/api/agent/*` routes and is feature-flagged and
dependency-guarded exactly like the existing optional RAG subsystem, so the core
transcription app is unaffected when the agent is disabled or LangChain is not
installed.

This is additive. It does not replace the existing single-shot `/api/rag/ask`
route or its frontend panel.

## Goals

- Introduce the `create_agent` framework in a self-contained package that
  mirrors the existing `backend/rag/` structure and conventions.
- Provide four genuinely useful tools over indexed transcripts.
- Stay local-first and offline-capable: reuse the existing OpenAI-compatible /
  Ollama env (`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`); introduce no new
  cloud provider.
- Never break or slow the core app: lazy construction, guarded imports, clear
  503s when disabled or deps absent.

## Non-goals (YAGNI, this pass)

- No frontend panel. Backend-only. (Optional follow-up: an Agent tab mirroring
  the RAG panel.)
- No streaming endpoint. Use `agent.invoke`, not `agent.stream`.
- No conversation persistence / checkpointer / multi-turn threads yet.
- No structured-output `response_format` yet (the answer is free-text prose with
  inline `[source]` citations, matching the RAG answer style).

## Architecture

New package `backend/agent/`, structured like `backend/rag/`:

```
backend/agent/
  __init__.py
  config.py    # AgentConfig, load_agent_config()
  tools.py     # @tool wrappers over the RAG store + LLM
  service.py   # AgentService: lazy ChatOpenAI + create_agent; .ask(), .status()
```

### Data / control flow

```
POST /api/agent/ask {question}
  -> AgentService.ask(question)
     -> agent.invoke({"messages": [{"role":"user","content": question}]})
        -> model plans, calls tools (search_transcripts / list_transcripts /
           summarize_transcript / extract_action_items) as needed
        -> tools read from the shared RAG store (Numpy or Chroma backend)
        -> model composes a grounded answer with [source] citations
     -> extract answer text + tool-call trace + citations from final state
  -> {answer, tool_calls: [...], citations: [...]}
```

The agent reuses the existing RAG store as its retrieval/knowledge backend, so
transcripts indexed via `/api/rag/index` are immediately available to the agent.

## Components

### `agent/config.py`

`AgentConfig` (frozen dataclass) built by `load_agent_config()` from env:

| Field | Env var | Default | Notes |
|---|---|---|---|
| `enabled` | `AGENT_ENABLED` | `false` | Master flag, same pattern as `RAG_ENABLED`. |
| `base_url` | `LLM_BASE_URL` | (required when enabled) | Reused from transcription config. |
| `api_key` | `LLM_API_KEY` | `"ollama"` | Reused; ignored by Ollama. |
| `model` | `AGENT_MODEL`, falling back to `LLM_MODEL` | `LLM_MODEL` | Lets the agent optionally use a different model than cleaning. |
| `temperature` | `AGENT_TEMPERATURE` | `0.2` | |
| `max_iterations` | `AGENT_MAX_ITERATIONS` | `6` | Cap agent tool-loop steps. |

Reuse the existing `_as_bool` helper pattern from `rag/config.py`.

### `agent/tools.py`

Four tools defined with `from langchain.tools import tool`. Each is a thin
wrapper; docstrings are the tool descriptions the model sees. Tools obtain the
shared RAG store via a small module-level accessor that builds it lazily (the
same `_build_store` logic `rag/service.py` already uses: prefer Chroma, fall
back to Numpy). To keep tools testable, the store and the LLM client are
injected/overridable rather than hard-wired globals.

- `search_transcripts(query: str) -> str`
  Wraps `store.search(query)`. Returns a formatted block of the top hits, each
  tagged `[source]` with a snippet, so the model can cite. Returns a clear "no
  matches / nothing indexed" string when empty.

- `list_transcripts() -> str`
  Returns the distinct indexed sources (via new `store.list_sources()`), so the
  agent can answer "what recordings do I have?" and pick a valid `source`
  argument for the tools below.

- `summarize_transcript(source: str) -> str`
  Fetches the transcript's full text via new `store.get_by_source(source)`,
  then runs one focused LLM call (concise summary prompt). Returns "unknown
  source" guidance when the source is not found.

- `extract_action_items(source: str) -> str`
  Fetches the transcript via `store.get_by_source(source)`, runs one focused
  LLM call that returns action items / decisions / owners as a short list.
  Returns a "no action items found" style message when appropriate.

The summarize/extract tools use a plain `openai` client pointed at the same
local endpoint (consistent with how `rag/service.py` already calls the LLM),
keeping tool internals independent of LangChain.

### `agent/service.py`

`AgentService`:
- `__init__(config=None)` — stores config, no heavy work.
- Lazy `_agent` property: builds
  `ChatOpenAI(base_url=config.base_url, api_key=config.api_key,
  model=config.model, temperature=config.temperature)` (from
  `langchain_openai`), then `create_agent(model=chat, tools=[...],
  system_prompt=SYSTEM_PROMPT)`. An explicit `ChatOpenAI` instance is used
  (not a `"provider:model"` string) because the endpoint is a custom local
  OpenAI-compatible URL.
- `SYSTEM_PROMPT` — instructs: answer from transcripts only; use tools to
  search/list/summarize/extract; cite `[source]`; say so when transcripts do not
  cover the question; be concise.
- `ask(question: str) -> AgentAnswer` — calls
  `agent.invoke({"messages": [{"role": "user", "content": question}]})`, then
  parses the returned message list into: final answer text, a `tool_calls`
  trace (name + args + short output preview per hop, mirroring the tutor app's
  trace shape), and `citations` collected from any `search_transcripts` results.
- `status() -> dict` — `{enabled, available, reason, model, base_url,
  tools: [names], store_backend, indexed_chunks}` without contacting the LLM.
  Reports `available=False` with a reason when disabled or when LangChain import
  fails.

`AgentAnswer` dataclass: `answer: str`, `tool_calls: list[dict]`,
`citations: list[dict]`.

### Store additions (`rag/store_numpy.py` and `rag/store.py`)

Add two small, additive read methods to both `NumpyStore` and `HybridStore`
(identical surface, per the existing "same surface" contract):

- `list_sources() -> list[str]` — distinct `source` values across stored chunks.
- `get_by_source(source: str) -> str` — concatenated chunk text for one source
  (ordered by chunk index when available), or `""` if the source is unknown.

For `NumpyStore` these read from the in-memory `_metas` / `_docs`. For
`HybridStore` they use a Chroma `get(where={"source": source})` query.

### API routes (`app.py`)

Mirror the existing RAG routes' lazy + guarded pattern (`_get_rag_service`
style):

- `_get_agent_service()` — lazily import `agent.service.AgentService`; return
  `(None, reason)` on ImportError so missing deps degrade gracefully.
- `GET /api/agent/status` — returns `service.status()`, or
  `{enabled: false, available: false, reason}` when unavailable.
- `POST /api/agent/ask` `{question: str}` — 503 when disabled or deps absent
  (clear reason); otherwise `{success, answer, tool_calls, citations}`.
  Errors are logged to the backend terminal and surfaced as a generic 502, same
  as the RAG routes.

### Dependencies (`pyproject.toml`)

New optional extra, guarded like `rag`:

```toml
agent = [
    "langchain>=1.0",
    "langchain-openai>=0.3",
]
```

`langgraph` arrives transitively via `langchain`. Regenerate `requirements.txt`
via `uv export` per repo convention (the agent extra stays out of the default
lockfile export unless the repo already exports extras; document the
`uv sync --extra agent` install path in `.env.example` / README).

### Configuration (`.env.example`)

Add an Agent section:

```
# --------------------------------------------------------------------------
# Optional agentic assistant over transcripts (LangChain create_agent).
# Reuses the OpenAI-compatible LLM config above. Install deps then enable:
#   uv sync --extra agent
# --------------------------------------------------------------------------
AGENT_ENABLED=false
# AGENT_MODEL=            # defaults to LLM_MODEL
# AGENT_TEMPERATURE=0.2
# AGENT_MAX_ITERATIONS=6
```

## Error handling

- Disabled (`AGENT_ENABLED=false`) or LangChain not installed: routes return
  503 with a clear, actionable reason. Core app unaffected.
- Unknown `source` in summarize/extract tools: the tool returns a guidance
  string (not an exception) so the agent can recover and tell the user.
- LLM / endpoint failure during `ask`: logged to the terminal; route returns a
  generic 502 (no raw error leaked), matching the RAG routes.
- Tool-loop runaway: bounded by `AGENT_MAX_ITERATIONS`.

## Testing

Offline-only, no live Ollama:

- `tests/test_agent_tools.py` — tool behavior against an in-memory fake store
  (implements `search`, `list_sources`, `get_by_source`); the summarize/extract
  LLM call is monkeypatched to a stub. Assert formatting, `[source]` tagging,
  and unknown-source handling.
- `tests/test_agent_service.py` — build `AgentService` with a stubbed chat model
  (a fake that returns a canned tool call then a final answer) and assert `.ask`
  parses answer + tool_calls + citations. Assert `.status()` shape and that a
  disabled config reports `available=False` without touching the network.
- `tests/test_store_sources.py` — `list_sources` / `get_by_source` on
  `NumpyStore` with seeded metadata.
- API-level: assert `/api/agent/*` return 503 when disabled (no deps needed).

If the repo has no test harness yet, add a minimal `pytest` dev dependency and a
`tests/` dir; keep tests import-light and network-free.

## Rollout

1. Store additions + their tests.
2. `agent/` package (config, tools, service) + tests.
3. Wire `/api/agent/*` routes.
4. `pyproject.toml` extra, `.env.example`, README/CLAUDE.md notes.
5. Manual smoke test with a local Ollama (`AGENT_ENABLED=true`,
   `uv sync --extra agent`): index a transcript, ask a multi-step question,
   confirm the tool trace and citations.

## Open questions

None blocking. Frontend Agent panel and streaming are deferred follow-ups.
