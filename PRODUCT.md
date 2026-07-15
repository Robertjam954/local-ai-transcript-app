# Product Overview

AI Transcript App is a browser-based voice transcription and cleanup tool. It captures speech, converts it to text locally with Whisper, and optionally rewrites that raw transcript into clear, concise prose using a language model. It is designed to run fully on your own machine, so audio and text never have to leave your device.

The project also serves as a portfolio/learning base for aspiring AI engineers, with checkpoint branches that extend the core app toward agentic and framework-based workflows.

## What It Does

1. Capture - record audio directly in the browser, upload an existing audio file, or paste raw text.
2. Transcribe - convert recorded or uploaded audio to text using a local Whisper model (English).
3. Clean - optionally send the raw transcript to an LLM that removes filler words, fixes grammar and speech-to-text errors, trims rambling, and preserves key points, names, numbers, and action items.
4. Use the result - view raw and cleaned text side by side and copy either to the clipboard with one click.

## Key Features

- Browser-based voice recording via the microphone, including a hold-V keyboard shortcut to record hands-free.
- Audio file upload with drag-and-drop, supporting common formats (mp3, wav, webm, ogg, m4a).
- Paste-text input for cleaning transcripts you already have, skipping the transcription step.
- Local English speech-to-text with Whisper (default `base.en`), auto-selecting GPU acceleration (Metal/CUDA) or CPU.
- LLM transcript cleaning driven by an editable system prompt, so users can tune how aggressively text is rewritten or adapt it to a specific style or industry.
- Toggle to enable or disable LLM cleaning; raw transcription always works even if the LLM is unavailable.
- Provider flexibility: works with any OpenAI API-compatible LLM - local Ollama (default), LM Studio, the OpenAI API, or others - via simple `.env` configuration.
- Graceful error handling: if LLM cleaning fails, the raw transcription is preserved and the user is notified.
- One-click copy to clipboard for both raw and cleaned text.
- A model-quality warning so users understand that small local models may follow the cleaning prompt imperfectly.

## Intended Users and Use Cases

- AI engineering learners using this as a portfolio starting point to extend (for example: adding GPU acceleration, a stronger local or cloud model, real-time streaming, or multi-language support).
- Privacy-conscious individuals who want speech-to-text and cleanup without sending audio to a cloud service.
- Knowledge workers turning voice notes, meeting snippets, or dictation into clean written text.
- Anyone who needs to quickly clean up an existing messy transcript by pasting it in.

## Defaults and Constraints

- Out of the box the app is English-only and runs a small local LLM on CPU, which is free and private but slower and less precise at following the cleaning prompt than a larger or cloud model.
- Cleaning output is bounded (short responses), tuned for tidying spoken passages rather than long-form generation.
- The recommended setup is a devcontainer (locally via Docker or in GitHub Codespaces) that provisions the app and an Ollama model automatically; a manual install is also supported.

The README frames the app explicitly as a base to make your own: swapping in stronger models, targeting a specific industry, or adding streaming and multi-language support are all suggested directions.

## Live Demo

A public, in-browser demo lives at [robertjam954.github.io/local-ai-transcript-app/demo.html](https://robertjam954.github.io/local-ai-transcript-app/demo.html). It runs Whisper `tiny.en` on the visitor's own device (WebAssembly/WebGPU via transformers.js), so it can be tried instantly without installing anything - and, true to the product's privacy stance, no audio is ever uploaded. The full local app remains the primary experience, with a larger Whisper model and local LLM cleanup.
