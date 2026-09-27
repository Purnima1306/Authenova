const STATUS_CONFIG = {
  pass: {
    label: 'Pass',
    icon: '✓',
  },
  warning: {
    label: 'Warning',
    icon: '!',
  },
  fail: {
    label: 'Fail',
    icon: '✕',
  },
};

function ValidationChecklist({ validation }) {
  return (
    <div className="card validation-card">
      <div className="validation-card__header">
        <div>
          <span className="validation-card__eyebrow">
            DOCUMENT VALIDATION
          </span>

          <h3 className="card__title">
            Validation Checklist
          </h3>

          <p className="text-muted validation-card__subtitle">
            Rule-based checks performed on the extracted document fields.
          </p>
        </div>

        <div className="validation-card__count">
          {validation.length} checks
        </div>
      </div>

      <div className="checklist">
        {validation.map((item) => {
          const config = STATUS_CONFIG[item.status];

          return (
            <div
              key={item.field}
              className={`checklist-row checklist-row--${item.status}`}
            >
              <div
                className={`status-pill status-pill--${item.status}`}
              >
                <span className="status-pill__icon">
                  {config.icon}
                </span>

                {config.label}
              </div>

              <div className="checklist-row__body">
                <div className="checklist-row__field">
                  {item.field}
                </div>

                <div className="checklist-row__explanation text-muted">
                  {item.explanation}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ValidationChecklist;