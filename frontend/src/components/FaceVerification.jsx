// ==========================================================================
// FACE VERIFICATION
// Shows document face vs live/presented face side by side, a similarity
// meter, and a clear Match / No Match status.
// ==========================================================================

function FaceVerification({ faceVerification, docPreview, facePreview }) {
  const { similarity, match } = faceVerification;

  return (
    <div className="card">
      <h3 className="card__title">Face Verification</h3>
      <p className="text-muted card__subtitle">
        Comparison between the document photo and the presented face photo.
      </p>

      <div className="face-compare">
        <div className="face-slot">
          <div className="face-slot__image-wrap">
            {docPreview ? (
              <img src={docPreview} alt="Face on document" className="face-slot__image" />
            ) : (
              <div className="placeholder-box placeholder-box--face">Document Face</div>
            )}
          </div>
          <span className="face-slot__label">Document Photo</span>
        </div>

        <div className="face-compare__vs">VS</div>

        <div className="face-slot">
          <div className="face-slot__image-wrap">
            {facePreview ? (
              <img src={facePreview} alt="Live presented face" className="face-slot__image" />
            ) : (
              <div className="placeholder-box placeholder-box--face">No Live Photo</div>
            )}
          </div>
          <span className="face-slot__label">Live / Presented Photo</span>
        </div>
      </div>

      {faceVerification.status === 'SKIPPED' ? (
        <div style={{ marginTop: '16px' }}>
          <div className="alert alert--warning" style={{ margin: 0, fontSize: '13px' }}>
            Biometric face verification was skipped because no live selfie was provided. This does not penalize the risk score.
          </div>
          <div style={{ marginTop: '10px' }} className="status-pill status-pill--lg status-pill--warning">
            Status: Skipped (Optional)
          </div>
        </div>
      ) : (
        <>
          <div className="face-meter">
            <div className="face-meter__row">
              <span>Similarity Score</span>
              <span className="face-meter__value">{similarity}%</span>
            </div>
            <div className="confidence-bar confidence-bar--wide">
              <div
                className={`confidence-bar__fill ${match ? 'confidence-bar__fill--pass' : 'confidence-bar__fill--fail'}`}
                style={{ width: `${similarity}%` }}
              />
            </div>
          </div>

          <div className={`status-pill status-pill--lg ${match ? 'status-pill--pass' : 'status-pill--fail'}`}>
            {match ? 'Match' : 'No Match'}
          </div>
        </>
      )}
    </div>
  );
}

export default FaceVerification;