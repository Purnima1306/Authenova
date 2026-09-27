// ==========================================================================
// TAMPERING DETECTION
// Shows the document preview with an optional overlay rectangle marking a
// suspicious region, plus a tampering level/score and plain explanation.
// ==========================================================================

function levelToStatus(level) {
  if (level === 'Low') return 'pass';
  if (level === 'Medium') return 'warning';
  return 'fail'; // High
}

function TamperingDetection({ tampering, docPreview }) {
  const status = levelToStatus(tampering.level);

  return (
    <div className={`card tampering-card tampering-card--${status}`}>
      <div className="tampering-card__header">
        <div>
          <span className="tampering-card__eyebrow">
            DOCUMENT INTEGRITY
          </span>

          <h3 className="card__title">
            Tampering Detection
          </h3>

          <p className="text-muted tampering-card__subtitle">
            Visual and structural analysis of the submitted document image.
          </p>
        </div>

        <div className={`status-pill status-pill--${status} status-pill--lg`}>
          <span className="status-pill__icon">
            {status === 'pass' && '✓'}
            {status === 'warning' && '!'}
            {status === 'fail' && '✕'}
          </span>

          {tampering.level}
        </div>
      </div>

      <div className="tampering-layout">
        <div className="tampering-image-section">
          <div className="tampering-image-label">
            DOCUMENT ANALYSIS PREVIEW
          </div>

          <div className="tampering-image-wrap">
            {docPreview ? (
              <div className="image-overlay-container">
                <img
                  src={docPreview}
                  alt="Document sample for tampering analysis"
                />

                {tampering.flagged && (
                  <div
                    className="flagged-region"
                    style={{
                      top: tampering.flaggedRegion.top,
                      left: tampering.flaggedRegion.left,
                      width: tampering.flaggedRegion.width,
                      height: tampering.flaggedRegion.height,
                    }}
                    title="Flagged region"
                  />
                )}
              </div>
            ) : (
              <div className="placeholder-box">
                No document preview available
              </div>
            )}
          </div>

          {tampering.flagged && (
            <div className="tampering-image-note">
              <span className="tampering-image-note__dot" />
              Suspicious region detected and highlighted
            </div>
          )}
        </div>

        <div className="tampering-details">
          <div className="tampering-score-card">
            <div className="tampering-score">
              <span className="tampering-score__label">
                TAMPERING SCORE
              </span>

              <span className="tampering-score__value">
                {tampering.score}
                <small>/100</small>
              </span>
            </div>

            <div className="confidence-bar confidence-bar--wide">
              <div
                className={`confidence-bar__fill confidence-bar__fill--${status}`}
                style={{
                  width: `${tampering.score}%`,
                }}
              />
            </div>
          </div>

          <div className="tampering-metrics">
            <div className="tampering-metric">
              <span className="tampering-metric__label">
                Raw Feature Matches
              </span>

              <strong className="tampering-metric__value">
                {tampering.raw_matches ?? 'N/A'}
              </strong>
            </div>

            <div className="tampering-metric">
              <span className="tampering-metric__label">
                RANSAC Verified Inliers
              </span>

              <strong className="tampering-metric__value">
                {tampering.verified_inliers ?? 0}
              </strong>
            </div>
          </div>

          <div className="tampering-explanation-box">
            <span className="tampering-explanation-box__label">
              ANALYSIS
            </span>

            <p className="tampering-explanation">
              {tampering.explanation}
            </p>
          </div>

          {tampering.flagged && (
            <div className="alert alert--warning tampering-warning">
              <span className="tampering-warning__icon">!</span>

              <span>
                A flagged region is marked with a red rectangle on the
                document image.
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TamperingDetection;