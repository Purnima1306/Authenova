// ==========================================================================
// FACE VERIFICATION
// Shows document face vs live/presented face side by side, a similarity
// meter, and a clear Match / No Match status.
// ==========================================================================

function FaceVerification({ faceVerification, docPreview, facePreview }) {
  const { similarity, match } = faceVerification;

  return (
    <div className="card face-verification-card">
      <div className="face-verification-card__header">
        <div>
          <span className="face-verification-card__eyebrow">
            BIOMETRIC VERIFICATION
          </span>

          <h3 className="card__title">
            Face Verification
          </h3>

          <p className="text-muted face-verification-card__subtitle">
            Comparison between the document photo and the presented face photo.
          </p>
        </div>

        {faceVerification.status === 'SKIPPED' ? (
          <div className="status-pill status-pill--lg status-pill--warning">
            Skipped
          </div>
        ) : (
          <div
            className={`status-pill status-pill--lg ${
              match
                ? 'status-pill--pass'
                : 'status-pill--fail'
            }`}
          >
            <span className="status-pill__icon">
              {match ? '✓' : '✕'}
            </span>

            {match ? 'Match' : 'No Match'}
          </div>
        )}
      </div>

      <div className="face-compare">
        <div className="face-slot">
          <div className="face-slot__image-wrap">
            {docPreview ? (
              <img
                src={docPreview}
                alt="Face on document"
                className="face-slot__image"
              />
            ) : (
              <div className="placeholder-box placeholder-box--face">
                Document Face
              </div>
            )}
          </div>

          <div className="face-slot__meta">
            <span className="face-slot__label">
              Document Photo
            </span>

            <span
              className={`face-detection-status ${
                faceVerification.document_face_detected
                  ? 'face-detection-status--pass'
                  : 'face-detection-status--fail'
              }`}
            >
              {faceVerification.document_face_detected
                ? 'Face detected'
                : 'Not found'}
            </span>
          </div>
        </div>

        <div className="face-compare__vs">
          VS
        </div>

        <div className="face-slot">
          <div className="face-slot__image-wrap">
            {facePreview ? (
              <img
                src={facePreview}
                alt="Live presented face"
                className="face-slot__image"
              />
            ) : (
              <div className="placeholder-box placeholder-box--face">
                No Live Photo
              </div>
            )}
          </div>

          <div className="face-slot__meta">
            <span className="face-slot__label">
              Live / Presented Photo
            </span>

            <span
              className={`face-detection-status ${
                faceVerification.presented_face_detected
                  ? 'face-detection-status--pass'
                  : 'face-detection-status--fail'
              }`}
            >
              {faceVerification.presented_face_detected
                ? 'Face detected'
                : 'Not found'}
            </span>
          </div>
        </div>
      </div>

      {faceVerification.status === 'SKIPPED' ? (
        <div className="face-skipped-section">
          <div className="alert alert--warning face-skipped-alert">
            <span className="face-skipped-alert__icon">
              !
            </span>

            <span>
              Biometric face verification was skipped because no live
              selfie was provided. This does not penalize the risk score.
            </span>
          </div>

          <div className="face-skipped-meta">
            <span className="status-pill status-pill--lg status-pill--warning">
              Status: Skipped (Optional)
            </span>
          </div>
        </div>
      ) : (
        <>
          <div className="face-meter">
            <div className="face-meter__row">
              <div>
                <span className="face-meter__label">
                  SIMILARITY SCORE
                </span>

                <span className="face-meter__description">
                  Facial similarity between both images
                </span>
              </div>

              <span className="face-meter__value">
                {similarity}%
              </span>
            </div>

            <div className="confidence-bar confidence-bar--wide">
              <div
                className={`confidence-bar__fill ${
                  match
                    ? 'confidence-bar__fill--pass'
                    : 'confidence-bar__fill--fail'
                }`}
                style={{
                  width: `${similarity}%`,
                }}
              />
            </div>
          </div>

          <div className="face-verification-meta">
            <div
              className={`status-pill status-pill--lg ${
                match
                  ? 'status-pill--pass'
                  : 'status-pill--fail'
              }`}
            >
              <span className="status-pill__icon">
                {match ? '✓' : '✕'}
              </span>

              {match ? 'Biometric Match' : 'No Match'}
              </div>

            <div className="face-model-info">
              <span>
                Model:
                <strong>
                  {faceVerification.model || 'FaceNet 512-d'}
                </strong>
              </span>

              <span className="face-model-divider">•</span>

              <span>
                Threshold:
                <strong>
                  {faceVerification.threshold || 58}%
                </strong>
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default FaceVerification;