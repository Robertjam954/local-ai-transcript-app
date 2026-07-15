# Repo TODOs

Status snapshot of the repository: what preparation/documentation is already in place, and what work remains. Generated 2026-07-15.

## Prep docs already in place

| Doc | Covers | State |
|-----|--------|-------|
| [README.md](README.md) | User story, features, checkpoint branches, devcontainer/Codespaces/manual setup, Azure App Service deploy (`azd`), configuration, troubleshooting | Complete, but the "Web app quick start" section is out of date (see TODO 3) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Backend (`app.py`, `transcription.py`), frontend component structure, data flow, devcontainer wiring | Complete, but misses the new static-SPA serving, `site/`, and `scripts/` (see TODO 3) |
| [PRODUCT.md](PRODUCT.md) | Product overview, key features, intended users, defaults and constraints | Complete and current |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, running, lint/format tooling, conventions | Complete; notes that no automated test suite exists yet |
| [context-engineering-workflow.md](context-engineering-workflow.md) | Learning notes on context engineering | Standalone learning material, not app docs |
| [claude-md-memory-workflow/](claude-md-memory-workflow/) and [self-documenting-ai-agent/](self-documenting-ai-agent/) | Example AI-agent workflow prompts | Illustration material, not app docs |
| `.devcontainer/` | Docker Compose dev environment (app + Ollama), post-create provisioning | Working, devcontainer-first setup |
| `azure.yaml` + `infra/main.bicep` + `infra/core/host/*` | azd deployment of the backend (single-origin: backend serves the built SPA via the `prepackage` hook) | Working; keep in sync with docs |
| `.github/workflows/pages.yml` + `site/` | GitHub Pages portfolio page | Working; undocumented in the README |

## What remains

### High priority

1. **Add a root LICENSE file.** README's "Licensing" section says the repo "is licensed under the terms in the repository's license file", but no license file exists at the repo root (the only LICENSE is inside the unrelated `infra/core/compose_docker_app/`). Pick a license (e.g. MIT) and add it.
2. **Remove or relocate `infra/core/compose_docker_app/`.** This is a complete, unrelated Docker Compose todo-app sample (~12,700 lines including two `package-lock.json` files) committed under the Bicep infra tree in commit `ae11e31`. It bloats the repo and confuses the `infra/` layout. If it is a deliberate learning sample, move it to a clearly named top-level folder (e.g. `examples/`) with a note; otherwise delete it.
3. **Fix docs drift around single-origin deployment.** Commit `87acdcf` made the FastAPI backend serve the built React SPA from `backend/static` (staged by `scripts/build_frontend.*` via the azd `prepackage` hook). But:
   - README's "Web app quick start" still says the frontend "is hosted separately (for example Azure Static Web Apps, GitHub Pages...)".
   - ARCHITECTURE.md does not mention the static mount, `scripts/`, or `site/`.
   Update both to describe the current behavior.

### Medium priority

4. **Add an automated test suite.** CONTRIBUTING.md explicitly notes there is none. Suggested starting points:
   - Backend: `pytest` + FastAPI `TestClient` for `/api/status`, `/api/system-prompt`, `/api/clean` (including the graceful-degradation path when the LLM is unavailable), and the temp-file cleanup in `/api/transcribe`.
   - Frontend: Vitest + React Testing Library for the three input paths (record / upload / paste) and error states.
5. **Add a CI workflow for the app itself.** The only workflow is the Pages deploy. Add a workflow running the checks CONTRIBUTING already prescribes: `ruff check` + `black --check` (backend), `npm run lint` + `npm run type-check` + `npm run build` (frontend), plus tests once TODO 4 lands.
6. **Document the GitHub Pages portfolio site.** `site/index.html` and `.github/workflows/pages.yml` deploy a portfolio page on pushes to `main`, but neither README nor ARCHITECTURE mentions it.
7. **Tidy the repo root.**
   - Two identical workspace files exist (`ai-transcript-app-voice-summarizer.code-workspace` and `local-ai-transcript-app.code-workspace`) - keep one.
   - Rename `meeting summarizer code and deep eval .mdx` (spaces in the filename) and consider moving it, `context-engineering-workflow.md`, `claude-md-memory-workflow/`, and `self-documenting-ai-agent/` into a `docs/` or `notes/` folder so the root stays app-focused.
8. **Keep `backend/requirements.txt` in sync with `uv.lock`.** It is hand-generated for App Service's Oryx build and will silently drift. Add a regeneration script (e.g. `uv export --no-dev -o backend/requirements.txt`) and/or a CI check.

### Low priority / nice to have

9. **Use descriptive commit messages.** The four most recent commits on `main` are all titled "ok"; the repo is a learning/portfolio base, so history readability matters.
10. **Roadmap extensions** (suggested by README/PRODUCT as learner directions, not gaps):
    - GPU acceleration and a stronger local LLM.
    - Real-time transcription and LLM streaming.
    - Multi-language support beyond English.
    - Industry-specific system prompts.
