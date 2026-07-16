import { Search, Database, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import styles from './TranscriptSearch.module.css';
import { Box } from './Box';

interface RagStatus {
  enabled: boolean;
  available: boolean;
  reason?: string;
  llm_model?: string;
  indexed_chunks?: number | null;
}

interface Citation {
  source: string;
  score: number;
  snippet: string;
}

interface AskResponse {
  success: boolean;
  answer?: string;
  citations?: Citation[];
}

interface IndexResponse {
  success: boolean;
  indexed_chunks?: number;
  source?: string;
}

interface TranscriptSearchProps {
  /** The current transcript the user can add to the searchable index. */
  currentTranscript: string | null;
}

export function TranscriptSearch({ currentTranscript }: TranscriptSearchProps) {
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<string | null>(null);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [isAsking, setIsAsking] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const refreshStatus = async () => {
    try {
      const res = await fetch('/api/rag/status');
      setStatus((await res.json()) as RagStatus);
    } catch {
      setStatus({ enabled: false, available: false, reason: 'backend unreachable' });
    }
  };

  useEffect(() => {
    void refreshStatus();
  }, []);

  // Feature is off or its dependencies aren't installed: stay out of the way,
  // mirroring the app's graceful-degradation behavior elsewhere.
  if (!status || !status.available) {
    return null;
  }

  const indexCurrent = async () => {
    if (!currentTranscript?.trim() || isIndexing) return;
    setIsIndexing(true);
    setNotice(null);
    try {
      const res = await fetch('/api/rag/index', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: currentTranscript.trim(),
          source: `transcript-${new Date().toISOString().slice(0, 19)}`,
        }),
      });
      const data = (await res.json()) as IndexResponse;
      if (!res.ok || !data.success) throw new Error('index failed');
      setNotice(
        data.indexed_chunks === 0
          ? 'Already indexed (no changes).'
          : `Indexed ${data.indexed_chunks} chunk(s).`
      );
      await refreshStatus();
    } catch {
      setNotice('Indexing failed - check the backend terminal.');
    } finally {
      setIsIndexing(false);
    }
  };

  const ask = async () => {
    if (!question.trim() || isAsking) return;
    setIsAsking(true);
    setAnswer(null);
    setCitations([]);
    try {
      const res = await fetch('/api/rag/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim() }),
      });
      const data = (await res.json()) as AskResponse;
      if (!res.ok || !data.success) throw new Error('ask failed');
      setAnswer(data.answer ?? '');
      setCitations(data.citations ?? []);
    } catch {
      setAnswer('Query failed - check the backend terminal.');
    } finally {
      setIsAsking(false);
    }
  };

  const indexed = status.indexed_chunks ?? 0;

  return (
    <div className={styles.container}>
      <Box header="Ask Your Transcripts" icon={Search}>
        <p className={styles.sub}>
          Fully local retrieval over transcripts you index - answers are grounded
          in your own recordings, with sources.
          {status.llm_model ? ` Model: ${status.llm_model}.` : ''}
        </p>

        <div className={styles.indexRow}>
          <button
            className={`${styles.secondary} ${
              !currentTranscript?.trim() || isIndexing ? styles.disabled : ''
            }`}
            onClick={indexCurrent}
            disabled={!currentTranscript?.trim() || isIndexing}
            type="button"
          >
            {isIndexing ? (
              <Loader2 className={styles.spin} size={16} />
            ) : (
              <Database size={16} />
            )}
            Index current transcript
          </button>
          <span className={styles.count}>{indexed} chunk(s) indexed</span>
        </div>

        <div className={styles.askRow}>
          <input
            className={styles.input}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void ask()}
            placeholder="Ask a question about your transcripts..."
            aria-label="Question about your transcripts"
            disabled={isAsking}
          />
          <button
            className={`${styles.button} ${
              !question.trim() || isAsking ? styles.disabled : ''
            }`}
            onClick={ask}
            disabled={!question.trim() || isAsking}
            type="button"
          >
            {isAsking ? 'Searching...' : 'Ask'}
          </button>
        </div>

        {notice && <p className={styles.notice}>{notice}</p>}

        {answer !== null && (
          <div className={styles.answer}>
            <p className={styles.answerText}>{answer}</p>
            {citations.length > 0 && (
              <div className={styles.citations}>
                <span className={styles.citationsLabel}>Sources</span>
                {citations.map((c, i) => (
                  <details key={i} className={styles.citation}>
                    <summary>
                      {c.source}
                      <span className={styles.score}>
                        {c.score.toFixed(3)}
                      </span>
                    </summary>
                    <p className={styles.snippet}>{c.snippet}</p>
                  </details>
                ))}
              </div>
            )}
          </div>
        )}
      </Box>
    </div>
  );
}
