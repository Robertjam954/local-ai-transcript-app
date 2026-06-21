---
name: AI Transcript App - Voice transcription and cleanup (Python + React)
description: Browser-based voice transcription with local Whisper speech-to-text and OpenAI-compatible LLM cleanup.
languages:
- python
- typescript
- javascript
products:
- whisper
- faster-whisper
- fastapi
- react
- vite
- ollama
- lm-studio
- openai
- azure-app-service
- azure-developer-cli
page_type: sample
urlFragment: ai-transcript-app-voice-summarizer
---
<!-- Front-matter follows the Microsoft samples schema style; values reflect this app's actual stack rather than Azure services. -->

# AI Transcript App - Voice transcription and cleanup


##### Table of Contents
- [AI Transcript App - Voice transcription and cleanup](#ai-transcript-app---voice-transcription-and-cleanup)
        - [Table of Contents](#table-of-contents)
  - [User story](#user-story)
    - [About this repo](#about-this-repo)
    - [When should you use this repo?](#when-should-you-use-this-repo)
    - [Key features](#key-features)
    - [Target end users](#target-end-users)
    - [Use case scenarios](#use-case-scenarios)
  - [Branches](#branches)
  - [Deploy](#deploy)
    - [Pre-requisites](#pre-requisites)
    - [Products used](#products-used)
    - [Cost considerations](#cost-considerations)
    - [Setup options](#setup-options)
    - [Running the app](#running-the-app)
    - [Web app quick start (Azure App Service)](#web-app-quick-start-azure-app-service)
    - [Configuration](#configuration)
    - [Testing the deployment](#testing-the-deployment)
  - [Supporting documentation](#supporting-documentation)
    - [Architecture](#architecture)
    - [Troubleshooting](#troubleshooting)
    - [Resource links](#resource-links)
    - [Licensing](#licensing)
  - [Disclaimers](#disclaimers)

## User story

Welcome to the *AI Transcript App* repository! The AI Transcript App is a two-tier web application that turns spoken audio into clean, readable text. A browser-based React frontend captures audio (or accepts uploaded files and pasted text), and a Python FastAPI backend performs local speech-to-text with [Whisper](https://github.com/openai/whisper) and optional cleanup through any OpenAI API-compatible language model. It is designed to run fully on your own machine, so audio and text never have to leave your device.

The project also serves as a portfolio and learning base for aspiring AI engineers, with checkpoint branches that extend the core app toward agentic and framework-based workflows.

**📺 Recommended Video Tutorial:** For project structure and API details, watch the full tutorial on YouTube: https://youtu.be/WUo5tKg2lnE

### About this repo

This repository provides an end-to-end solution for capturing speech and producing clean written text, with the minimum components needed to demonstrate a local-first transcription pattern. It pairs a local Whisper model for speech-to-text with a provider-agnostic LLM cleanup step, and ships a devcontainer so the whole stack (app plus an Ollama model) runs locally with no cloud dependency. It is intended as a base to extend and make your own, not a production deployment as-is. It provides the following features:

* Record audio in the browser, upload an audio file, or paste raw text
* Local English speech-to-text with Whisper (runs on your machine)
* Optional LLM cleanup that removes filler words and fixes errors
* Compatibility with any OpenAI API-format provider (Ollama, LM Studio, OpenAI, and others)
* An editable cleaning system prompt so you can tune the rewrite behavior

### When should you use this repo?

Use this repo when you want a private, local-first transcription tool you can run and customize yourself, or when you want a hands-on portfolio base to learn AI engineering. Because the backend is deliberately provider-agnostic, the same code works against a free local model or a hosted API, so you can start fully offline and graduate to stronger models as your needs grow.

The vanilla version runs a small language model on your CPU. This means the AI may not follow system prompts perfectly depending on the transcript. The challenge for you is to advance the solution and make it your own, for example:

* Modify it for a specific industry
* Add GPU acceleration and a stronger local LLM
* Use a cloud AI model
* Add real-time transcription and LLM streaming
* Add multi-language support beyond English

**📚 Need help and want to learn more?** Full courses on AI Engineering are available at [https://aiengineer.community/join](https://aiengineer.community/join)

### Key features

- **Browser-based voice recording**: Capture speech directly from the microphone, including a hold-V keyboard shortcut to record hands-free.
- **Audio file upload**: Drag-and-drop or pick a file in common formats (mp3, wav, webm, ogg, m4a).
- **Paste-text input**: Clean a transcript you already have, skipping the transcription step.
- **Local speech-to-text**: English Whisper transcription (default `base.en`) that auto-selects GPU acceleration (Metal/CUDA) or CPU.
- **LLM transcript cleanup**: An editable system prompt removes filler words, fixes grammar and speech-to-text errors, trims rambling, and preserves key facts, names, numbers, and action items.
- **OpenAI API compatibility**: Works with any OpenAI-format provider - local Ollama (default), LM Studio, the OpenAI API, or others - via simple `.env` configuration.
- **Graceful degradation**: Raw transcription always works even when the LLM is unavailable; if cleanup fails, the raw transcript is preserved and the user is notified.
- **One-click copy**: Copy raw or cleaned text to the clipboard instantly.

**Note**: Out of the box the app is English-only and runs a small local LLM on CPU, which is free and private but slower and less precise at following the cleaning prompt than a larger or cloud model. A model-quality warning surfaces this in the UI.

### Target end users

Privacy-conscious individuals and knowledge workers who want speech-to-text and cleanup without sending audio to a cloud service, and AI engineering learners using this as a portfolio starting point to extend. It is also suited to anyone who needs to quickly clean up an existing messy transcript by pasting it in.

### Use case scenarios

#### Private voice notes
A knowledge worker dictates a meeting recap or voice memo in the browser. Whisper transcribes it locally, the LLM trims filler and fixes errors, and the cleaned text is copied to a document - with no audio ever leaving the machine.

#### Cleaning an existing transcript
A user pastes a messy auto-generated transcript into the app. The transcription step is skipped and the text is sent straight to the LLM cleanup step, returning tidy, readable prose.

#### Portfolio and learning base
An aspiring AI engineer uses the project as a foundation, then advances it through the checkpoint branches (agentic workflows, PydanticAI, MCP) to demonstrate AI engineering skills to employers.

---

## Branches

This repository uses checkpoint branches to progressively teach AI engineering concepts:

| Branch | Description | Builds On | Learning Resource |
|--------|-------------|-----------|-------------------|
| `main` | Complete transcript app with Whisper + LLM cleaning (runs fully locally, beginner friendly) | — | [YouTube Tutorial](https://youtu.be/WUo5tKg2lnE) |
| `checkpoint-1-fundamentals` | Exercise generation system for learning Python/TypeScript fundamentals | — | [Classroom](https://aiengineer.community/join) |
| `checkpoint-agentic-openrouter` | Agentic workflow with autonomous tool selection | `main` | [Classroom](https://aiengineer.community/join) |
| `checkpoint-pydanticai-openrouter` | PydanticAI framework for structured agent development | `checkpoint-agentic-openrouter` | [Classroom](https://aiengineer.community/join) |
| `checkpoint-rest-mcp-openrouter` | MCP integration with REST API and GitHub Issues | `checkpoint-pydanticai-openrouter` | [Classroom](https://aiengineer.community/join) |

> **Why "openrouter" in branch names?** These branches use [OpenRouter](https://openrouter.ai/) to access powerful cloud models that reliably support tool/function calling. Small local models struggle with agentic workflows.

Switch branches with: `git checkout <branch-name>`

---

## Deploy

### Pre-requisites

The recommended setup is a devcontainer, which provisions the app and an Ollama model automatically.

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [VS Code](https://code.visualstudio.com/)
- [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- A machine with 8+ CPU cores and 16GB RAM recommended (the default setup runs an LLM on CPU)

For manual installation you will instead need Python 3.12+, Node.js 24+, [uv](https://docs.astral.sh/uv/), and an LLM server ([Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/)).

### Products used

- Whisper (via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)) - local speech-to-text
- FastAPI + Uvicorn - backend service
- React 19 + TypeScript + Vite - frontend single-page app
- Ollama - default local LLM server (`gemma3:4b` default)
- Any OpenAI API-compatible provider (LM Studio, OpenAI, and others) - optional alternative for cleanup
- Docker Compose devcontainer - reproducible local dev environment
- Azure App Service + Azure Developer CLI (`azd`) - optional cloud deployment of the backend (see [Web app quick start](#web-app-quick-start-azure-app-service))

### Cost considerations

Run locally, this app is free: Whisper and the default Ollama model run on your own hardware, so there are no per-request charges. Costs only apply if you:

- Point the cleanup step at a paid hosted API (for example the OpenAI API) - you are billed by that provider per token. See [OpenAI API pricing](https://openai.com/api/pricing/).
- Deploy the backend to Azure App Service - you are billed for the App Service plan (the template defaults to a low-cost **B1** plan). See [Azure App Service pricing](https://azure.microsoft.com/pricing/details/app-service/linux/). Run `azd down` to remove the resources when you are done.

### Setup options

#### 🚀 Dev Container (Recommended)

**This project is devcontainer-first.**

1. **Open in Dev Container** - Click **"Reopen in Container"** in VS Code, or `Cmd/Ctrl+Shift+P` → **"Dev Containers: Reopen in Container"**. Wait ~5-10 minutes for the initial build and model download.

   VS Code automatically builds and starts both containers (app + Ollama), installs Python and Node.js dependencies, downloads the Ollama model, and creates `backend/.env` with working defaults.

#### ☁️ GitHub Codespaces (No Powerful PC Required)

Don't have a powerful PC? GitHub Codespaces provides cloud-based development environments that work with this project's devcontainer.

1. Go to the [repository on GitHub](https://github.com/AI-Engineer-Skool/local-ai-transcript-app) → green **"Code"** button → **"Codespaces"** tab → **"Create codespace on main"**. The devcontainer enforces at least **4-core**; select more cores and RAM if you can. Wait ~5-10 minutes for setup.
2. Ports are auto-forwarded (3000, 8000, 11434). Click the port 3000 link or use the **"Ports"** tab to access the frontend.
3. For code that expects true `localhost` access, install the [GitHub Codespaces extension](https://marketplace.visualstudio.com/items?itemName=GitHub.codespaces) in VS Code Desktop and connect to your running Codespace so ports forward to your actual `localhost`.

> **💡 Tip:** Stop your Codespace when not in use to conserve free hours at [github.com/codespaces](https://github.com/codespaces).
> **📺 Video Guide:** Watch the [GitHub Codespaces setup tutorial](https://youtu.be/KkV1O-rXntM).
> **🔄 Other Platforms:** Any cloud platform supporting devcontainers (Gitpod, DevPod, etc.) can also use this repository's `.devcontainer` configuration.

#### 🛠️ Manual Installation

The devcontainer is the easiest supported method for beginners. If you install manually:

- Install Python 3.12+, Node.js 24+, [uv](https://docs.astral.sh/uv/), and an LLM server ([Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/))
- Copy `backend/.env.example` to `backend/.env` and configure
- Install dependencies with `uv sync` (backend) and `npm install` (frontend)
- Start your LLM server and pull a model: `ollama pull llama3.1:8b`

### Running the app

Open **two terminals** and run:

**Terminal 1 - Backend:**

```bash
cd backend
uv sync && uv run uvicorn app:app --reload --host 0.0.0.0 --port 8000 --timeout-keep-alive 600
```

> **Note:** `uv sync` ensures dependencies are up-to-date (useful after switching branches). `--timeout-keep-alive 600` sets a 10-minute timeout for long audio processing.

**Terminal 2 - Frontend:**

```bash
cd frontend
npm install && npm run dev
```

> **Note:** `npm install` ensures dependencies are up-to-date (useful after switching branches).

**Browser:** Open `http://localhost:3000`

### Web app quick start (Azure App Service)

Want to run the backend in the cloud instead of locally? This repo ships an [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/) deployment, adapted from the Azure quickstart [Deploy a Python web app to Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python). It provisions a Linux App Service plan and an App Service, then deploys the **FastAPI backend** (`backend/`) and starts it with `uvicorn`.

**What it deploys:** the `backend/` transcription API only. The React `frontend/` is a static single-page app and is hosted separately (for example Azure Static Web Apps, GitHub Pages, or any static host) - point it at your deployed backend URL.

#### Pre-requisites

- An Azure subscription - [create one for free](https://azure.microsoft.com/free/)
- The [Azure Developer CLI (`azd`)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd) installed

#### Files added for deployment

- `azure.yaml` - declares the `web` service (`project: ./backend`, `language: python`, `host: appservice`)
- `infra/` - Bicep templates: `main.bicep` (resource group, App Service plan, App Service), `main.parameters.json`, and reusable `core/host/*` modules
- `backend/requirements.txt` - pinned dependencies (generated from `uv.lock`) so App Service's Oryx build can install them

#### Deploy

```bash
# From the project root
azd auth login

# (Optional) configure the LLM cleanup step on the deployed app
azd env set LLM_BASE_URL "https://api.openai.com/v1"
azd env set LLM_API_KEY  "<your-api-key>"
azd env set LLM_MODEL    "gpt-4o-mini"

# Provision Azure resources and deploy in one step
azd up
```

`azd up` prompts for an environment name and region, provisions the resources, builds the backend, and prints the deployed App Service URL (also saved as the `WEB_URI` output). Verify it with `GET <WEB_URI>/api/status`.

To tear everything down:

```bash
azd down
```

> ⚠️ **Sizing note:** The template defaults to a **B1** App Service plan to keep costs low. Whisper downloads its model on first request and runs speech-to-text on CPU, which is memory- and compute-intensive; for anything beyond light testing, bump the SKU in `infra/main.bicep` (the `appServicePlan` module `sku`) to a plan with more memory and vCPUs. If no `LLM_*` settings are configured, the deployed app still serves transcription only.

### Configuration

This app is compatible with any OpenAI API-format LLM provider: **Ollama** (default, works out of the box in the devcontainer), **LM Studio**, the **OpenAI API**, or any other OpenAI-compatible API.

The devcontainer automatically creates `backend/.env` with working Ollama defaults, so **no configuration is needed to get started.** To use a different provider, edit `backend/.env`:

- `WHISPER_MODEL` - Whisper model name (default `base.en`)
- `LLM_BASE_URL` - API endpoint
- `LLM_API_KEY` - API key
- `LLM_MODEL` - Model name

### Testing the deployment

1. Open the frontend at `http://localhost:3000`.
2. Record a short clip with the microphone (or hold **V**), upload an audio file, or paste text.
3. Confirm the raw transcription appears. With LLM cleaning enabled, confirm the cleaned text appears alongside it.
4. Use the one-click copy buttons to copy either result to the clipboard.

You can also check backend readiness directly at `http://localhost:8000/api/status`, which reports the configured Whisper and LLM models.

---

## Supporting documentation

### Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full breakdown of the backend (`app.py`, `transcription.py`, system prompt, endpoints), the frontend component structure, the request/response data flow, and how the devcontainer wires the services together. A condensed view of the API:

- `GET /api/status` - readiness plus configured Whisper/LLM models
- `GET /api/system-prompt` - the default cleaning prompt
- `POST /api/transcribe` - upload audio, returns raw Whisper text
- `POST /api/clean` - text + optional system prompt, returns LLM-cleaned text

See also [PRODUCT.md](PRODUCT.md) for the product overview, and [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

### Troubleshooting

**Container won't start or is very slow** - ⚠️ This app runs an LLM on CPU and needs adequate Docker resources. In **Docker Desktop** → **Settings** → **Resources**, set **CPUs** to the maximum available (8+ recommended) and **Memory** to at least 16GB, then **Apply & Restart**. More CPU = faster LLM responses.

**Microphone not working** - Use Chrome or Firefox (Safari may have issues) and check browser microphone permissions.

**Backend fails to start** - Check that the Whisper model downloaded to `~/.cache/huggingface/` and that you have enough disk space (models are ~150MB).

**LLM errors** - Make sure the Ollama service is running (it auto-starts with the devcontainer) and the model is downloaded. Transcription still works without the LLM (raw Whisper only).

**LLM is slow** - See the Docker resources note above. As a fallback, switch to a smaller model via `LLM_MODEL` in `backend/.env` (faster but worse at cleaning), or use a cloud API like OpenAI for instant, high-quality responses.

**Cannot access localhost:3000 or localhost:8000 from the host** - In **Docker Desktop** → **Settings** → **Resources** → **Network**, enable **"Use host networking"** (may require a restart), then restart the servers.

**Port already in use** - Backend: change the port with `--port 8001`. Frontend: edit `vite.config.js` and change `port: 3000`.

### Resource links

- [Whisper](https://github.com/openai/whisper) and [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [React documentation](https://react.dev/) and [Vite documentation](https://vite.dev/)
- [Ollama](https://ollama.com/) and [LM Studio](https://lmstudio.ai/)
- [OpenAI API reference](https://platform.openai.com/docs/api-reference)
- [uv documentation](https://docs.astral.sh/uv/)
- [Azure App Service documentation](https://learn.microsoft.com/en-us/azure/app-service/)
- [Azure Developer CLI (`azd`) documentation](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)
- [Deploy a Python web app to Azure App Service (quickstart)](https://learn.microsoft.com/en-us/azure/app-service/quickstart-python)
- [AI Engineer community courses](https://aiengineer.community/join)

### Licensing

This repository is licensed under the terms in the repository's license file.

## Disclaimers

This software requires the use of third-party components (Whisper, FastAPI, React, Ollama, and others) which are governed by separate proprietary or open-source licenses. You must comply with the terms of each applicable license in order to use the software. This license does not grant you a right to use any such third-party components.

The default configuration runs a small local model and is intended as a learning and portfolio base, not a production deployment as-is. Evaluate transcription and cleanup quality for your own data and tune models, prompts, and configuration accordingly before relying on the output. Speech-to-text and LLM cleanup can introduce errors; review results before use in any setting where accuracy matters.

If you configure a hosted API provider, audio-derived text will be sent to that provider and is subject to that provider's terms and privacy policy.
