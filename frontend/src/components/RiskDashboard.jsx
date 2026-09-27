const LEVEL_TO_STATUS = {
  LOW: 'pass',
  MEDIUM: 'warning',
  HIGH: 'fail',
};

function RiskDashboard({ risk }) {
  const status = LEVEL_TO_STATUS[risk.level] || 'warning';

  return (
    <div className={`card risk-card risk-card--${status}`}>
      <div className="risk-card__header">
        <div>
          <span className="risk-card__eyebrow">
            OVERALL ASSESSMENT
          </span>

          <h3 className="card__title">
            Overall Risk Assessment
          </h3>

          <p className="text-muted risk-card__subtitle">
            Consolidated risk evaluation based on the verification results.
          </p>
        </div>

        <div className={`risk-badge risk-badge--${status}`}>
          <span className="risk-badge__dot" />
          {risk.level}
        </div>
      </div>

      <div className="risk-summary">
        <div className="risk-score-block">
          <span className="risk-score-block__label">
            RISK SCORE
          </span>

          <div className="risk-score-block__value">
            {risk.score}
            <span>/100</span>
          </div>
        </div>

        <div className="risk-score-bar">
          <div
            className={`risk-score-bar__fill risk-score-bar__fill--${status}`}
            style={{
              width: `${Math.min(Math.max(risk.score, 0), 100)}%`,
            }}
          />
        </div>
      </div>

      <div className="risk-reasons-section">
        <div className="risk-reasons__header">
          <h4 className="risk-reasons__title">
            Assessment Factors
          </h4>

          <span className="risk-reasons__count">
            {risk.reasons.length} factor
            {risk.reasons.length !== 1 ? 's' : ''}
          </span>
        </div>

        <ul className="risk-reasons">
          {risk.reasons.map((reason, index) => (
            <li
              key={index}
              className={`risk-reason risk-reason--${reason.tone}`}
            >
              <span
                className={`risk-reason__dot risk-reason__dot--${reason.tone}`}
              />

              <span className="risk-reason__text">
                {reason.text}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default RiskDashboard;