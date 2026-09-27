import { useState } from 'react';
import OcrResults from './OcrResults';
import ValidationChecklist from './ValidationChecklist';
import TamperingDetection from './TamperingDetection';
import FaceVerification from './FaceVerification';
import RiskDashboard from './RiskDashboard';
import OfficerDecision from './OfficerDecision';


function ResultsPage({ results, docPreview, facePreview, onStartNew }) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  const caseId =
    results.document_id || `AUTHENOVA-${results.risk?.score || 0}0921`;

  const faceData =
    results.faceVerification ||
    results.face_verification || {
      similarity: 0,
      threshold: 58,
      match: null,
      status: 'SKIPPED',
    };

  return (
    <div className="page-container results-page">
      <div className="results-header">
        <div>
          <span className="results-header__eyebrow">
            VERIFICATION COMPLETE
          </span>

          <h1>Screening Results</h1>

          <div className="results-header__meta">
            <span>
              Case ID <strong>{caseId}</strong>
            </span>
            <span>•</span>
            <span>
              Document Type{' '}
              <strong>
                {(results.document_type || 'Passport').toUpperCase()}
              </strong>
            </span>
            </div>
            </div>
            </div>
            <div className="results-summary">
        <div className="results-summary__status">
          <span className="results-summary__dot" />
          Screening completed successfully
        </div>

        <button
          type="button"
          className="btn btn--primary"
          onClick={onStartNew}
        >
          Start New Screening
        </button>
      </div>

      <div className="results-rag-list">
        <RiskDashboard risk={results.risk} />

        <OcrResults ocr={results.ocr} />

        <ValidationChecklist validation={results.validation} />

        <TamperingDetection
          tampering={results.tampering}
          docPreview={docPreview}
        />

        <FaceVerification
          faceVerification={faceData}
          docPreview={docPreview}
          facePreview={facePreview}
        />

        <OfficerDecision
          documentId={results.document_id || results.documentId}
          initialDecision={results.officer_decision}
        />
      </div>

      <div className="diagnostics-grid">
        <div className="diagnostics-card">
          <span className="diagnostics-card__label">VERIFICATION STATUS</span>
          <strong className="diagnostics-card__value">
            {results.status || 'Completed'}
          </strong>
        </div>

        <div className="diagnostics-card">
          <span className="diagnostics-card__label">DOCUMENT TYPE</span>
          <strong className="diagnostics-card__value">
            {(results.document_type || 'Passport').toUpperCase()}
          </strong>
        </div>

        <div className="diagnostics-card">
          <span className="diagnostics-card__label">FACE VERIFICATION</span>
          <strong className="diagnostics-card__value">
            {faceData.status === 'SKIPPED'
              ? 'Skipped'
              : faceData.match
                ? 'Match'
                : 'No Match'}
          </strong>
        </div>
      </div>

      <div className="results-footer">
        <span>AUTHENOVA · Identity Verification System</span>
        <span>Verification report generated for officer review</span>
      </div>
    </div>
  );
}

export default ResultsPage;