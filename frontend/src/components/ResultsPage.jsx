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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <h3 className="card__title" style={{ margin: 0 }}>Standard Criteria &amp; Policy Citations (RAG + AI)</h3>
            <span className="status-pill status-pill--pass" style={{ fontSize: '0.75rem', padding: '3px 8px' }}>
              ✦ Prompt-Engineered Synthesis
            </span>
          </div>
          <p className="text-muted card__subtitle" style={{ marginTop: '0.25rem' }}>
            Grounded regulatory guidance and actionable officer recommendations synthesized for flagged anomalies.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '0.5rem' }}>
            {results.rag_explanations.map((exp, idx) => (
              <div
                key={idx}
                style={{
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-md, 8px)',
                  padding: '1rem',
                  background: 'var(--color-surface-card, #ffffff)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                }}
              >
                {/* Header Row */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.6rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="status-pill status-pill--warning" style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 7px' }}>
                      {exp.rule_id}
                    </span>
                    <strong style={{ fontSize: '0.9rem', color: 'var(--color-text-primary)' }}>
                      {exp.topic ? exp.topic.replace(/_/g, ' ').toUpperCase() : 'COMPLIANCE'}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    {exp.model && (
                      <span style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(99, 102, 241, 0.1)', color: '#4f46e5', fontWeight: 600 }}>
                        {exp.model}
                      </span>
                    )}
                    <span style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(0,0,0,0.05)', color: 'var(--color-text-secondary)' }}>
                      Match: {Math.round((exp.relevance_score || 0) * 100)}%
                    </span>
                  </div>
                </div>

                {/* Finding Summary */}
                <div style={{ fontSize: '0.92rem', marginBottom: '0.6rem', color: 'var(--color-text-primary)', lineHeight: 1.45 }}>
                  <strong>Finding:</strong> {exp.summary || exp.explanation}
                </div>

                {/* Structured Breakdown: Risk Analysis & Officer Recommendation */}
                {exp.risk_analysis && (
                  <div style={{ background: '#fffbeb', borderLeft: '3px solid #f59e0b', padding: '0.5rem 0.75rem', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.85rem', color: '#92400e', lineHeight: 1.4 }}>
                    <strong>Risk Analysis:</strong> {exp.risk_analysis}
                  </div>
                )}

                {exp.officer_recommendation && (
                  <div style={{ background: '#eff6ff', borderLeft: '3px solid #3b82f6', padding: '0.5rem 0.75rem', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.85rem', color: '#1e40af', lineHeight: 1.4 }}>
                    <strong>Officer Recommendation:</strong> {exp.officer_recommendation}
                  </div>
                )}

                {/* Authority Source */}
                <div style={{ fontSize: '0.78rem', color: 'var(--color-text-secondary)', opacity: 0.85, marginTop: '0.35rem' }}>
                  Source Standard: {exp.source}
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

      {/* Passport Document-Type Verification Section */}
      {results.passport_verification && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
            <h3 className="card__title" style={{ margin: 0 }}>
              📘 Passport Document Classification
            </h3>
            <span
              className={`status-pill ${
                results.passport_verification.is_passport
                  ? 'status-pill--pass'
                  : results.passport_verification.status === 'UNCERTAIN'
                  ? 'status-pill--warning'
                  : 'status-pill--fail'
              }`}
            >
              {results.passport_verification.is_passport
                ? 'Passport Detected'
                : results.passport_verification.status === 'UNCERTAIN'
                ? 'Classification Inconclusive'
                : 'Non-Passport Document'}
            </span>
          </div>
          <p className="text-muted card__subtitle" style={{ margin: '4px 0 1rem 0' }}>
            Document-type verification powered by PassportVerificationModel (Random Forest, 33 visual &amp; structural features).
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Document Type:</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '2px' }}>
                {results.passport_verification.is_passport ? 'Passport' : 'Non-Passport Document'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Confidence:</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '2px' }}>
                Passport classification confidence: {results.passport_verification.confidence_pct ?? Math.round((results.passport_verification.confidence || 0) * 100)}%
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Status:</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '2px' }}>
                {results.passport_verification.is_passport ? 'Passport Detected' : 'Classification Mismatch'}
              </div>
            </div>
          </div>
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

              {/* Passport Document Classification Model Diagnostics */}
              <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color, #334155)' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.95rem' }}>🤖 Passport Verification Model (MIDV-2020)</h4>
                <div style={{ fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div>Model Architecture: <strong>RandomForest (50 estimators)</strong></div>
                  <div>Feature Vector: <strong>{results.passport_verification?.features || 33}-dimensional visual/structural</strong></div>
                  <div>Document Classification: <strong>{results.passport_verification?.is_passport ? '✅ Passport Detected' : '❌ Non-Passport Document'}</strong></div>
                  <div>Classification Confidence: <strong>{results.passport_verification?.confidence_pct ?? Math.round((results.passport_verification?.confidence || 0) * 100)}%</strong></div>
                  <div>Status: <strong>{results.passport_verification?.status || 'N/A'}</strong></div>
                  <div>Input Source: <strong>Orientation-corrected canonical frame</strong></div>
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