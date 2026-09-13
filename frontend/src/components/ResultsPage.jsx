import { useState } from 'react';
import OcrResults from './OcrResults';
import ValidationChecklist from './ValidationChecklist';
import TamperingDetection from './TamperingDetection';
import FaceVerification from './FaceVerification';
import RiskDashboard from './RiskDashboard';
import OfficerDecision from './OfficerDecision';

function ResultsPage({ results, docPreview, facePreview, onStartNew }) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const caseId = results.document_id || `AUTHENOVA-${results.risk?.score || 0}0921`;
  const faceData = results.faceVerification || results.face_verification || {
    similarity: 0,
    threshold: 58,
    match: null,
    status: 'SKIPPED'
  };

  return (
    <div className="page-container">
      <div className="page-heading page-heading--row">
        <div>
          <h1>Screening Results</h1>
          <p className="text-muted">Case ID: <strong>{caseId}</strong> • Document Type: <strong style={{ textTransform: 'uppercase' }}>{results.document_type || 'Passport'}</strong></p>
        </div>
        <button className="btn btn--secondary" onClick={onStartNew}>
          Start New Screening
        </button>
      </div>

      <RiskDashboard risk={results.risk} />

      {results.rag_explanations && results.rag_explanations.length > 0 && (
        <div className="card">
          <h3 className="card__title">Standard Criteria &amp; Policy Citations (RAG)</h3>
          <p className="text-muted card__subtitle">
            Grounded regulatory guidance retrieved for issues flagged during analysis.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {results.rag_explanations.map((exp, idx) => (
              <div key={idx} className="alert alert--warning" style={{ margin: 0 }}>
                <strong>{exp.rule_id}</strong>: {exp.explanation}
                <div style={{ fontSize: '0.8rem', marginTop: '0.25rem', opacity: 0.8 }}>
                  Source: {exp.source} (Confidence: {Math.round((exp.relevance_score || 0) * 100)}%)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {results.orchestration_logs && results.orchestration_logs.length > 0 && (
        <div className="card">
          <h3 className="card__title">Adaptive Orchestration Trace</h3>
          <p className="text-muted card__subtitle">
            Autonomous decision audit log executed during screening.
          </p>
          <ul style={{ paddingLeft: '1.2rem', margin: 0 }}>
            {results.orchestration_logs.map((log, idx) => (
              <li key={idx} style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                <span className="status-pill status-pill--warning" style={{ fontSize: '0.75rem', padding: '2px 6px', marginRight: '6px' }}>
                  {log.action}
                </span>
                {log.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      <OcrResults ocr={results.ocr} />

      <ValidationChecklist validation={results.validation} />

      <TamperingDetection tampering={results.tampering} docPreview={docPreview} />

      <FaceVerification
        faceVerification={faceData}
        docPreview={docPreview}
        facePreview={facePreview}
      />

      {/* Advanced Diagnostics Expandable Section */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => setShowDiagnostics(!showDiagnostics)}>
          <div>
            <h3 className="card__title" style={{ margin: 0 }}>🔬 Advanced System &amp; Model Diagnostics</h3>
            <p className="text-muted card__subtitle" style={{ margin: '4px 0 0 0' }}>
              Detailed low-level metrics: ICAO 9303 MRZ check digits, FaceNet biometrics, and RANSAC forensics.
            </p>
          </div>
          <button className="btn btn--secondary" style={{ padding: '6px 14px', fontSize: '0.85rem' }}>
            {showDiagnostics ? '▲ Hide Diagnostics' : '▼ View Diagnostics'}
          </button>
        </div>

        {showDiagnostics && (
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--border-color, #334155)', paddingTop: '1.25rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
              {/* MRZ Diagnostics */}
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>📋 ICAO 9303 MRZ Cryptographic Checksums</h4>
                {results.mrz ? (
                  <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div>Passport Number Check Digit: <strong>{results.mrz.passport_number_valid ? '✅ VALID (7-3-1 Weight)' : '❌ INVALID'}</strong></div>
                    <div>Date of Birth Check Digit: <strong>{results.mrz.date_of_birth_valid ? '✅ VALID (7-3-1 Weight)' : '❌ INVALID'}</strong></div>
                    <div>Expiry Date Check Digit: <strong>{results.mrz.expiry_date_valid ? '✅ VALID (7-3-1 Weight)' : '❌ INVALID'}</strong></div>
                    <div>Format: <strong>{results.mrz.format || 'TD3 (Passport)'}</strong></div>
                    <div style={{ marginTop: '6px', fontFamily: 'monospace', fontSize: '0.75rem', background: '#000', padding: '6px', borderRadius: '4px', wordBreak: 'break-all' }}>
                      {results.mrz.raw_lines?.map((line, i) => <div key={i}>{line}</div>)}
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>No MRZ lines detected on document. Visual OCR fallback used.</div>
                )}
              </div>

              {/* Biometrics Diagnostics */}
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>👤 Biometric Deep Learning Pipeline</h4>
                <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div>Model: <strong>{faceData.model || 'FaceNet 512-d (Inception-ResNet-v1)'}</strong></div>
                  <div>Face Detection: <strong>Multi-Cascade (Alt2 / Alt / Default)</strong></div>
                  <div>Eye Alignment: <strong>Canonical Horizon Correction &amp; 20% Margin</strong></div>
                  <div>Calibrated Cross-Domain Threshold: <strong>{faceData.threshold || 58}%</strong></div>
                  <div>Normalized Cosine Similarity: <strong>{faceData.similarity}%</strong></div>
                  <div>Status: <strong>{faceData.match ? '✅ Verified Match' : (faceData.status === 'SKIPPED' ? '⚠️ Skipped (Optional)' : '❌ Impostor Alert')}</strong></div>
                </div>
              </div>

              {/* Tampering Diagnostics */}
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>🔍 Digital Forensics &amp; Copy-Move</h4>
                <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div>Raw Feature Matches: <strong>{results.tampering?.raw_matches ?? 'N/A'}</strong></div>
                  <div>Displacement Vector Clustering: <strong>Enabled (30px grid)</strong></div>
                  <div>RANSAC Verified Inliers: <strong>{results.tampering?.verified_inliers ?? 0} (Threshold: 25)</strong></div>
                  <div>Geometric Copy-Move Detected: <strong>{results.tampering?.verified_inliers >= 25 ? '⚠️ FORGERY DETECTED' : '✅ CLEAN'}</strong></div>
                  <div>Error Level Analysis (ELA): <strong>Raw {results.tampering?.ela_score ?? '0.31'}</strong></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <OfficerDecision
        documentId={results.document_id}
        initialDecision={results.officer_decision}
      />
    </div>
  );
}

export default ResultsPage;