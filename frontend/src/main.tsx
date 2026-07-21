import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

async function bootstrap() {
  const rootElement = document.getElementById('root');

  if (!rootElement) {
    throw new Error('Root element not found');
  }

  // The static GitHub Pages demo has no backend; install the browser-side
  // API mock before the app makes its first request.
  if (import.meta.env.VITE_DEMO_MODE === 'true') {
    await import('./demo/mockApi');
  }

  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

void bootstrap();
