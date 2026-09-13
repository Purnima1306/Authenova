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
    <div className="card">
      <h3 className="card__title">Tampering Detection</h3>
      <p className="text-muted card__subtitle">
        Visual and structural analysis of the document image.
      </p>

      <div className="tampering-layout">
        <div className="tampering-image-wrap">
          {docPreview ? (
            <div className="image-overlay-container">
              <img src={docPreview} alt="Document sample for tampering analysis" />
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
            <div className="placeholder-box">No document preview available</div>
          )}
        </div>

        <div className="tampering-details">
          <div className={`status-pill status-pill--${status} status-pill--lg`}>
            Tampering Level: {tampering.level}
          </div>

          <div className="tampering-score">
            <span className="tampering-score__label">Tampering Score</span>
            <span className="tampering-score__value">{tampering.score} / 100</span>
          </div>
          <div className="confidence-bar confidence-bar--wide">
            <div
              className={`confidence-bar__fill confidence-bar__fill--${status}`}
              style={{ width: `${tampering.score}%` }}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', marginTop: '10px', fontSize: '0.8rem', color: 'var(--text-muted, #94a3b8)' }}>
            <span>Raw Feature Matches: <strong>{tampering.raw_matches ?? 'N/A'}</strong></span>
            <span>RANSAC Verified Inliers: <strong>{tampering.verified_inliers ?? 0}</strong></span>
          </div>

          <p className="tampering-explanation">{tampering.explanation}</p>

          {tampering.flagged && (
            <div className="alert alert--warning">
              A flagged region is marked with a red rectangle on the document image.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TamperingDetection;