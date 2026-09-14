import { useState } from 'react';
import Navbar from './components/Navbar';
import LoginPage from './components/LoginPage';
import UploadPage from './components/UploadPage';
import PipelineProgress from './components/PipelineProgress';
import ResultsPage from './components/ResultsPage';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function App() {
  // 'login' | 'upload' | 'pipeline' | 'results'
  const [page, setPage] = useState('login');
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const [docPreview, setDocPreview] = useState(null);
  const [facePreview, setFacePreview] = useState(null);
  const [results, setResults] = useState(null);
  const [screeningError, setScreeningError] = useState('');

  function handleLoginSuccess() {
    setIsLoggedIn(true);
    setPage('upload');
  }

  function handleLogout() {
    setIsLoggedIn(false);
    setPage('login');
    setDocPreview(null);
    setFacePreview(null);
    setResults(null);
    setScreeningError('');
  }

  async function handleStartScreening({ docFile, faceFile, docPreview, facePreview }) {
    setDocPreview(docPreview);
    setFacePreview(facePreview);
    setScreeningError('');
    setPage('pipeline');

    try {
      const formData = new FormData();
      formData.append('file', docFile);
      formData.append('document_type', 'passport');
      if (faceFile) {
        formData.append('verification_image', faceFile);
      }

      const response = await fetch(`${API_BASE_URL}/api/v1/screen`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned status ${response.status}`);
      }

      const data = await response.json();
      if (!data.success || !data.report) {
        throw new Error(data.message || 'Screening returned an incomplete report.');
      }

      setResults(data.report);
      setPage('results');
    } catch (err) {
      console.error('Screening failed:', err);
      const msg = err.message === 'Failed to fetch'
        ? 'Cannot connect to backend server. Please make sure the FastAPI backend is running on http://127.0.0.1:8000.'
        : (err.message || 'Failed to connect to Authenova verification server.');
      setScreeningError(msg);
    }
  }

  function handleStartNew() {
    setDocPreview(null);
    setFacePreview(null);
    setResults(null);
    setScreeningError('');
    setPage('upload');
  }

  return (
    <div className="app-shell">
      <Navbar isLoggedIn={isLoggedIn} onLogout={handleLogout} />

      <main className="app-main">
        {page === 'login' && <LoginPage onLoginSuccess={handleLoginSuccess} />}

        {page === 'upload' && <UploadPage onStartScreening={handleStartScreening} />}

        {page === 'pipeline' && (
          <PipelineProgress
            error={screeningError}
            onRetry={handleStartNew}
          />
        )}

        {page === 'results' && results && (
          <ResultsPage
            results={results}
            docPreview={docPreview}
            facePreview={facePreview}
            onStartNew={handleStartNew}
          />
        )}
      </main>
    </div>
  );
}

export default App;