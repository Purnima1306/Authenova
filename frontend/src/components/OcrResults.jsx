// ==========================================================================
// OCR RESULTS
// Displays extracted document fields, each with a confidence percentage.
// Any confidence below 70% is visually flagged as a warning.
// ==========================================================================

const CONFIDENCE_THRESHOLD = 70;

const FIELD_LABELS = {
  name: 'Name',
  idNumber: 'ID Number',
  dateOfBirth: 'Date of Birth',
  nationality: 'Nationality',
  expiryDate: 'Expiry Date',
};

function OcrResults({ ocr }) {
  return (
    <div className="card">
      <h3 className="card__title">OCR Extraction Results</h3>
      <p className="text-muted card__subtitle">
        Fields automatically extracted from the uploaded document.
      </p>

      <div className="ocr-grid">
        {Object.entries(ocr).map(([key, field]) => {
          const isLowConfidence = field.confidence < CONFIDENCE_THRESHOLD;
          return (
            <div
              key={key}
              className={`ocr-field ${isLowConfidence ? 'ocr-field--warning' : ''}`}
            >
              <div className="ocr-field__label">
                <span>{FIELD_LABELS[key] || key}</span>
                {field.source && (
                  <span className="status-pill" style={{ fontSize: '0.7rem', padding: '1px 6px', marginLeft: '6px' }}>
                    {field.source}
                  </span>
                )}
              </div>
              <div className="ocr-field__value">{field.value}</div>

              <div className="ocr-field__confidence-row">
                <div className="confidence-bar">
                  <div
                    className={`confidence-bar__fill ${
                      isLowConfidence ? 'confidence-bar__fill--warning' : ''
                    }`}
                    style={{ width: `${field.confidence}%` }}
                  />
                </div>
                <span
                  className={`confidence-value ${
                    isLowConfidence ? 'confidence-value--warning' : ''
                  }`}
                >
                  {field.confidence}%
                </span>
              </div>

              {isLowConfidence && (
                <div className="ocr-field__warning-text">
                  Low confidence — recommend manual verification
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default OcrResults;