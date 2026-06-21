# Architecture

AI Transcript App is a two-tier web application that turns spoken audio into clean, readable text. A browser-based React frontend captures audio (or accepts uploaded files / pasted text), and a Python FastAPI backend performs local speech-to-text with Whisper and optional text cleaning through an OpenAI-compatible LLM.

## High-Level Layout

```
ai-transcript-app-voice-summarizer/
├── backend/        FastAPI service: transcription + LLM cleaning
├── frontend/       React + Vite single-page app
└── .devcontainer/  Docker Compose dev environment (app + Ollama)
```

The frontend and backend run as separate processes. In development the Vite dev server (port 3000) proxies all `/api/*` requests to the backend (port 8000), so the browser talks to a single origin. The default LLM provider, Ollama, runs as a third service (port 11434).

## Backend

Located in `backend/`. Python 3.12+, dependencies managed with `uv` (`pyproject.toml`, `uv.lock`).

- `app.py` - FastAPI application. Defines the HTTP API, CORS for localhost, and a lifespan hook that constructs a single `TranscriptionService` at startup. Endpoints:
  - `GET /api/status` - reports readiness and configured Whisper/LLM models.
  - `GET /api/system-prompt` - returns the default cleaning prompt.
  - `POST /api/transcribe` - accepts an uploaded audio file, writes it to a temp file, transcribes it with Whisper, returns raw text, and always cleans up the temp file.
  - `POST /api/clean` - accepts text plus an optional system prompt and returns LLM-cleaned text.
- `transcription.py` - `TranscriptionService`, the core domain class:
  - Loads a `faster-whisper` `WhisperModel` with `device="auto"` (Metal / CUDA / CPU) and `compute_type="int8"`.
  - Connects to the LLM via the `openai` client pointed at a configurable `base_url`, making it compatible with any OpenAI-format provider.
  - `transcribe()` runs Whisper (English, `beam_size=5`) and joins segments into text.
  - `clean_with_llm()` sends a system prompt + raw text chat completion (`temperature=0.3`, `max_tokens=200`).
- `system_prompt.txt` - the default editor prompt (remove filler words, fix grammar, preserve key facts). Loaded at import time and used unless the client supplies a custom prompt.
- Configuration is read from environment variables (`.env`, see `.env.example`): `WHISPER_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`.

## Frontend

Located in `frontend/`. React 19 + TypeScript, built and served by Vite 7. UI icons from `lucide-react`. Styling uses CSS Modules plus a shared `styles/variables.css`.

- `src/App.tsx` - the single stateful container. Manages recording, processing, results, error, settings, and prompt state with React hooks. It owns the three input paths and the calls to the backend.
- `src/components/` - presentational components: `Header`, `RecordButton`, `UploadZone` (drag/drop + file picker), `TextInputZone` (paste text), `SettingsPanel` (LLM toggle + editable system prompt), `TranscriptionResults`, `ErrorMessage`, `Footer`, plus shared primitives `Box`, `TextBox`, `Spinner`, and `ModelQualityWarning`.
- `src/types/index.ts` - shared TypeScript interfaces and accepted audio MIME types.
- Audio capture uses the browser `MediaRecorder` API (webm), with a hold-V keyboard shortcut to record.

## Data Flow

1. The user records audio, uploads an audio file, or pastes text in the browser.
2. For audio, the frontend POSTs a `FormData` blob to `/api/transcribe`; the backend transcribes with Whisper and returns raw text.
3. If LLM cleaning is enabled, the frontend POSTs the raw text (and current system prompt) to `/api/clean`; the backend returns cleaned text. Pasted text skips step 2 and goes straight to `/api/clean`.
4. The UI shows both raw and cleaned text, with one-click copy. LLM failures are reported without discarding the raw transcription.

## Key Technologies

- Backend: FastAPI, Uvicorn, faster-whisper, openai SDK, python-dotenv, python-multipart, numpy; tooling: uv, ruff, black.
- Frontend: React 19, TypeScript, Vite, lucide-react; tooling: ESLint, Prettier.
- Local models: Whisper (`base.en` default) for speech-to-text; Ollama-served LLM (`gemma3:4b` default) for cleaning. Any OpenAI-compatible endpoint (LM Studio, OpenAI, etc.) can be substituted via `.env`.
- Dev environment: Docker Compose devcontainer running the app container alongside an `ollama/ollama` service with a persistent model volume.

## How It Fits Together

The backend is deliberately provider-agnostic: Whisper runs locally for privacy and zero API cost, while the cleaning step is an OpenAI-compatible HTTP call so the same code works against a local Ollama model or a hosted API. The frontend keeps all orchestration in `App.tsx`, treating the backend as a thin REST surface. The devcontainer wires these together (auto-generating `backend/.env`, pulling the model) so the whole stack runs locally with no cloud dependency.
