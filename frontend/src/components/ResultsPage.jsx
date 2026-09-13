import OcrResults from './OcrResults';
import ValidationChecklist from './ValidationChecklist';
import TamperingDetection from './TamperingDetection';
import FaceVerification from './FaceVerification';
import RiskDashboard from './RiskDashboard';
import OfficerDecision from './OfficerDecision';

function ResultsPage({ results, docPreview, facePreview, onStartNew }) {
  const caseId = results.document_id || `AUTHENOVA-${results.risk?.score || 0}0921`;
  const faceData = results.faceVerification || results.face_verification || {
    similarity: 0,
    threshold: 75,
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

      <OfficerDecision
        documentId={results.document_id}
        initialDecision={results.officer_decision}
      />
    </div>
  );
}

export default ResultsPage;