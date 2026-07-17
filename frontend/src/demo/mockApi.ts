// Browser-side mock of the backend API for the static GitHub Pages demo.
// Loaded only when VITE_DEMO_MODE=true (see main.tsx). It patches
// window.fetch so the real UI code paths run unmodified: transcription
// returns a sample transcript and cleanup runs a small heuristic editor,
// all in the browser with no backend.

const DEFAULT_PROMPT = `You are a transcript editor. Transform raw transcripts into clear, concise text.

INSTRUCTIONS:
- Remove filler words (um, uh, like, you know, basically, actually, etc.)
- Remove redundant statements and rambling
- Fix grammar and speech-to-text errors
- Preserve key points, technical details, names, numbers, and action items
- Use proper punctuation and maintain the speaker's tone

Return ONLY the cleaned text with NO preamble.`;

const DEMO_TRANSCRIPT =
  'um so this is like a quick demo of the voice summarizer app, you know, ' +
  'normally whisper would uh transcribe your actual audio right here on your ' +
  'own machine, and then a local LLM would basically clean it up. in this ' +
  'static demo the the transcription step is simulated, but you can, um, ' +
  'paste your own messy text below and actually watch the cleanup step run. ' +
  'clone the repo to try the real thing with your own voice.';

// Phrases first so "you know" is removed before "know" could survive alone.
const FILLERS = [
  'you know',
  'i mean',
  'sort of',
  'kind of',
  'kinda',
  'basically',
  'literally',
  'actually',
  'like',
  'umm',
  'um',
  'uhh',
  'uh',
  'erm',
  'hmm',
];

function cleanTranscript(raw: string): string {
  let text = raw;

  for (const filler of FILLERS) {
    // A filler flanked by commas ("could, uh, create") takes both commas
    // with it; otherwise stray commas litter the cleaned sentence.
    text = text.replace(new RegExp(`,\\s*${filler}\\s*,`, 'gi'), ' ');
    text = text.replace(
      new RegExp(`(^|[\\s,])${filler}(?=[\\s,.!?]|$)`, 'gi'),
      '$1'
    );
  }

  text = text
    .replace(/\b(\w+)(\s+\1\b)+/gi, '$1') // collapse stutters ("the the")
    .replace(/\s+([,.!?])/g, '$1')
    .replace(/,{2,}/g, ',')
    .replace(/([.!?])\s*,/g, '$1')
    .replace(/^[,\s]+/, '')
    .replace(/\s{2,}/g, ' ')
    .trim();

  text = text
    .replace(/\bi\b/g, 'I')
    .replace(
      /(^|[.!?]\s+)([a-z])/g,
      (_match, prefix: string, char: string) => prefix + char.toUpperCase()
    );

  if (text && !/[.!?]$/.test(text)) {
    text += '.';
  }

  return text;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

const realFetch = window.fetch.bind(window);

window.fetch = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> => {
  const url =
    typeof input === 'string'
      ? input
      : input instanceof URL
        ? input.toString()
        : input.url;
  const path = url.split('?')[0] ?? url;

  if (path.endsWith('/api/system-prompt')) {
    return jsonResponse({ default_prompt: DEFAULT_PROMPT });
  }

  if (path.endsWith('/api/status')) {
    return jsonResponse({
      ready: true,
      whisper_model: 'simulated (static demo)',
      llm_model: 'simulated (static demo)',
    });
  }

  if (path.endsWith('/api/transcribe')) {
    await delay(1800);
    return jsonResponse({ success: true, text: DEMO_TRANSCRIPT });
  }

  if (path.endsWith('/api/clean')) {
    await delay(1200);
    let text = '';
    if (typeof init?.body === 'string') {
      const parsed = JSON.parse(init.body) as { text?: string };
      text = parsed.text ?? '';
    }
    return jsonResponse({ success: true, text: cleanTranscript(text) });
  }

  return realFetch(input, init);
};

export {};
