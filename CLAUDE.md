# AI Transcript App - Voice Transcription & Cleanup

Browser-based voice transcription with local Whisper speech-to-text and OpenAI-compatible LLM cleanup / summarization (Python + React). Deployable to Azure.

## Quick Facts
- **Type**: Full-stack app (FastAPI backend + React frontend)
- **Backend**: Python >= 3.12, package `ai-transcript-app` (`uv`, `backend/pyproject.toml`)
- **Frontend**: React (`frontend/`, scripts: `dev`, `build`, `lint`, `format`, `type-check`)
- **STT**: local Whisper · **LLM**: OpenAI-compatible endpoint
- **Deploy**: Azure (`azure.yaml`, `infra/`) - Azure subscription is on billing hold; deploys blocked until reactivated

## Commands
- Backend: `cd backend && uv sync && uv run fastapi dev`
- Frontend: `cd frontend && npm install && npm run dev`
- Frontend checks: `npm run lint` · `npm run type-check` · `npm run format`
- Build: `npm run build`

## Key Directories
- `backend/` - FastAPI service (Whisper STT + LLM cleanup)
- `frontend/` - React UI
- `infra/`, `azure.yaml` - Azure deployment config
- `scripts/`, `docs/`, `PRODUCT.md`, `ARCHITECTURE.md` - tooling + context

## Working Rules
- **Structure**: keep aligned with the `agentic-ai-app-template` layout.
- **Azure**: this repo keeps the Azure skill bundle for deployment work; the Azure `azure-*` / `microsoft-foundry` skills are available here.
- **Prose**: single hyphen (-), never em dashes.
- **Workflow**: follow `context-engineering-workflow` (curate context -> plan -> implement).
- **Models**: LLM work uses `claude-sonnet-5`.
- A `.claude/settings.json` hook blocks edits on `main`/`master` - branch first.
