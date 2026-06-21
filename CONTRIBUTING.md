# Contributing

This is a monorepo with a Python FastAPI backend (`backend/`) and a React + TypeScript frontend (`frontend/`). The recommended environment is the devcontainer, which provisions both plus an Ollama LLM service.

## Setup

### Devcontainer (recommended)

1. Install Docker Desktop, VS Code, and the Dev Containers extension.
2. Open the repo in VS Code and choose "Reopen in Container" (or run it in GitHub Codespaces).
3. The container installs Python and Node dependencies, downloads the Ollama model, and creates `backend/.env` with working defaults. Allow plenty of CPU and RAM (8+ cores, 16GB recommended) since the LLM runs on CPU by default.

### Manual setup

Requires Python 3.12+, Node.js 24+, [uv](https://docs.astral.sh/uv/), and an OpenAI-compatible LLM server (Ollama or LM Studio).

- Backend: `cd backend && uv sync`, then copy `.env.example` to `.env` and configure `WHISPER_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.
- Frontend: `cd frontend && npm install`.
- Start your LLM server and pull a model, e.g. `ollama pull gemma3:4b`.

## Running

Use two terminals.

```bash
# Terminal 1 - backend
cd backend
uv sync && uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 600

# Terminal 2 - frontend
cd frontend
npm install && npm run dev
```

Open http://localhost:3000. The Vite dev server proxies `/api/*` to the backend on port 8000.

## Code Quality and Tooling

There is no automated test suite in the repo; verify changes by running the app and exercising the record / upload / paste flows. Before committing, run the linters and formatters.

Backend (Python):

- Format with Black (`uv run black .`) and lint with Ruff (`uv run ruff check .`). Configuration lives in `pyproject.toml`.
- Line length 88, target Python 3.12. Ruff enforces pycodestyle, pyflakes, isort import ordering, pep8-naming, pyupgrade, bugbear, and related rule sets.

Frontend (TypeScript/React):

```bash
npm run lint         # ESLint, zero warnings allowed
npm run lint:fix     # auto-fix
npm run format       # Prettier
npm run type-check   # tsc --noEmit
npm run build        # tsc + vite build
```

## Conventions and Best Practices

- Match existing style: typed Python with `pydantic` request models on the backend; functional React components with hooks and CSS Modules on the frontend. Shared types go in `frontend/src/types/index.ts`.
- Keep the backend provider-agnostic. Talk to the LLM only through the OpenAI-compatible client and read configuration from environment variables - do not hardcode endpoints, keys, or model names.
- Never commit secrets. `.env` is git-ignored; update `.env.example` when adding new configuration.
- Preserve graceful degradation: transcription must keep working even when the LLM is unavailable, and raw errors should be logged server-side rather than leaked to the client.
- Use single hyphens, not em dashes, in code, comments, and docs.
- The project uses checkpoint branches (see README) to layer in advanced features; build new lessons on the appropriate branch rather than reworking `main`.
