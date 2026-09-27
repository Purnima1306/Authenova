const CONFIDENCE_THRESHOLD = 70;

const FIELD_LABELS = {
  name: 'Full Name',
  idNumber: 'Document Number',
  dateOfBirth: 'Date of Birth',
  nationality: 'Nationality',
  expiryDate: 'Expiry Date',
};

function OcrResults({ ocr }) {
  return (
    <div className="card ocr-card">
      <div className="ocr-card__header">
        <div>
          <span className="ocr-card__eyebrow">
            DOCUMENT EXTRACTION
          </span>

          <h3 className="card__title">
            Extracted Information
          </h3>

          <p className="text-muted ocr-card__subtitle">
            Information extracted from the submitted document using OCR.
          </p>
        </div>

        <div className="ocr-source-badge">
          {ocr.source}
        </div>
      </div>

      <div className="ocr-fields">
        {Object.entries(FIELD_LABELS).map(([key, label]) => {
          const field = ocr.fields?.[key];

          if (!field) return null;

          const confidence = field.confidence ?? 0;
          const isLowConfidence = confidence < CONFIDENCE_THRESHOLD;

          return (
            <div
              key={key}
              className={`ocr-field ${
                isLowConfidence ? 'ocr-field--warning' : ''
              }`}
            >
              <div className="ocr-field__top">
                <span className="ocr-field__label">
                  {label}
                </span>

                <span
                  className={`ocr-confidence ${
                    isLowConfidence
      ? 'ocr-confidence--warning'
      : 'ocr-confidence--pass'
  }`}
>
  {confidence}% confidence
</span>
</div>

<div className="ocr-field__value">
  {field.value || 'Not detected'}
</div>

<div className="ocr-confidence-bar">
  <div
    className={`ocr-confidence-bar__fill ${
      isLowConfidence
        ? 'ocr-confidence-bar__fill--warning'
        : 'ocr-confidence-bar__fill--pass'
    }`}
    style={{
      width: `${Math.min(Math.max(confidence, 0), 100)}%`,
    }}
  />
</div>

{isLowConfidence && (
  <div className="ocr-field__warning">
    <span>!</span>
    Low confidence extraction — manual verification recommended.
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