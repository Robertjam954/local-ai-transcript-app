import { FlaskConical } from 'lucide-react';
import styles from './DemoBanner.module.css';

export function DemoBanner() {
  return (
    <div className={styles.container} role="note">
      <FlaskConical className={styles.icon} aria-hidden="true" />
      <p className={styles.message}>
        You're viewing the static portfolio demo: transcription and LLM cleanup
        are simulated in your browser, so recording and uploads return a sample
        transcript. Paste your own messy text to try the cleanup step, or{' '}
        <a
          className={styles.link}
          href="https://github.com/Robertjam954/local-ai-transcript-app"
          target="_blank"
          rel="noopener noreferrer"
        >
          clone the repo
        </a>{' '}
        to run real on-device Whisper and a local LLM.
      </p>
    </div>
  );
}
