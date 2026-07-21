import os
import tempfile
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from transcription import TranscriptionService

load_dotenv()


class CleanRequest(BaseModel):
    text: str
    system_prompt: str | None = None


service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uses OpenAI-compatible API (Ollama, OpenAI, LM Studio, etc.). Configure via .env file."""
    global service
    print("🚀 Starting AI Transcript App...")

    service = TranscriptionService(
        whisper_model=os.getenv("WHISPER_MODEL"),
        llm_base_url=os.getenv("LLM_BASE_URL"),
        llm_api_key=os.getenv("LLM_API_KEY"),
        llm_model=os.getenv("LLM_MODEL"),
    )
    print("✅ Ready!")
    yield


app = FastAPI(title="AI Transcript App", lifespan=lifespan)

# CORS for localhost development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server (Vite)
        "http://localhost:5173",  # React dev server (Vite alternative port)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/status")
async def get_status():
    return {
        "status": "ready" if service else "initializing",
        "whisper_model": os.getenv("WHISPER_MODEL"),
        "llm_model": os.getenv("LLM_MODEL"),
        "llm_base_url": os.getenv("LLM_BASE_URL"),
    }


@app.get("/api/system-prompt")
async def get_system_prompt():
    if not service:
        raise HTTPException(status_code=503, detail="Service not ready")

    return {"default_prompt": service.get_default_system_prompt()}


@app.post("/api/transcribe")
async def transcribe_audio(audio: Annotated[UploadFile, File()]):
    if not service:
        raise HTTPException(
            status_code=503, detail="Service not ready, still initializing models"
        )

    suffix = os.path.splitext(audio.filename)[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        raw_text = service.transcribe(tmp_path)
        return {"success": True, "text": raw_text}

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Transcription failed: {str(e)}"
        ) from e

    finally:
        # Always clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/api/clean")
async def clean_text(request: CleanRequest):
    if not service:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        cleaned_text = service.clean_with_llm(
            request.text, system_prompt=request.system_prompt
        )
        return {"success": True, "text": cleaned_text}

    except Exception as e:
        # Log the full error to the backend terminal; keep the response generic so no
        # raw error detail leaks to the frontend.
        print(f"❌ LLM cleaning failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="LLM cleaning failed. Check the backend terminal for details.",
        ) from e


# --------------------------------------------------------------------------
# Optional local RAG + search over transcripts (fully offline, Ollama-backed).
#
# Feature-flagged and dependency-guarded: the routes below are always mounted,
# but the RAG service and its heavy deps (chromadb, rank-bm25, optional
# sentence-transformers) load lazily only when RAG is enabled and used. When
# RAG_ENABLED is false or the deps are absent, the routes return 503 with a
# clear reason and the core transcription app is completely unaffected.
# See backend/rag/ and RAG setup notes in the README.
# --------------------------------------------------------------------------

_rag_service = None


class RagIndexRequest(BaseModel):
    text: str
    source: str


class RagAskRequest(BaseModel):
    question: str


def _get_rag_service():
    """Lazily construct the RagService, or return None with a reason string."""
    global _rag_service
    if _rag_service is not None:
        return _rag_service, None
    try:
        from rag.service import RagService
    except Exception as e:  # noqa: BLE001 - surface import issues to the caller
        return None, f"RAG unavailable: {e}"
    _rag_service = RagService()
    return _rag_service, None


@app.get("/api/rag/status")
async def rag_status():
    svc, reason = _get_rag_service()
    if svc is None:
        return {"enabled": False, "available": False, "reason": reason}
    return svc.status()


@app.post("/api/rag/index")
async def rag_index(request: RagIndexRequest):
    svc, reason = _get_rag_service()
    if svc is None or not svc.config.enabled:
        raise HTTPException(
            status_code=503,
            detail=reason or "RAG is disabled. Set RAG_ENABLED=true and install the rag extra.",
        )
    try:
        written = svc.index_transcript(text=request.text, source=request.source)
        return {"success": True, "indexed_chunks": written, "source": request.source}
    except Exception as e:
        print(f"❌ RAG indexing failed: {e}")
        raise HTTPException(
            status_code=502, detail="RAG indexing failed. Check the backend terminal."
        ) from e


@app.post("/api/rag/ask")
async def rag_ask(request: RagAskRequest):
    svc, reason = _get_rag_service()
    if svc is None or not svc.config.enabled:
        raise HTTPException(
            status_code=503,
            detail=reason or "RAG is disabled. Set RAG_ENABLED=true and install the rag extra.",
        )
    try:
        result = svc.ask(request.question)
        return {
            "success": True,
            "answer": result.answer,
            "citations": [vars(c) for c in result.citations],
        }
    except Exception as e:
        print(f"❌ RAG query failed: {e}")
        raise HTTPException(
            status_code=502, detail="RAG query failed. Check the backend terminal."
        ) from e


# Serve the built React SPA (single-origin deployment). The frontend build is
# staged into backend/static by the azd `prepackage` hook (see azure.yaml /
# scripts/build_frontend.*). Mounted at "/" AFTER the /api/* routes above so the
# API keeps priority; guarded so local dev runs fine without a build present.
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="spa")
