import { useEffect, useState } from 'react';
import { PIPELINE_STAGES } from '../data/mockData';

function PipelineProgress({ error, onRetry }) {
  const [currentStageIndex, setCurrentStageIndex] = useState(0);

  useEffect(() => {
    if (error) return;

    const timer = setInterval(() => {
      setCurrentStageIndex((prev) => {
        if (prev < PIPELINE_STAGES.length - 1) {
          return prev + 1;
        }

        return prev;
      });
    }, 700);

    return () => clearInterval(timer);
  }, [error]);

  return (
    <div className="page-container page-container--narrow">
      <div className="page-heading">
        <div className="pipeline-eyebrow">
          <span className="pipeline-eyebrow__dot" />
          AUTHENOVA VERIFICATION ENGINE
        </div>

        <h1>Running Verification</h1>

        <p className="text-muted">
          The submitted document is being analyzed across multiple
          verification stages.
        </p>
      </div>

      {error ? (
        <div className="card pipeline-error-card">
          <div className="pipeline-error-icon">!</div>

          <div className="pipeline-error-content">
            <h3>Screening Failed</h3>

            <p className="text-muted">
              {error}
            </p>

            <button
              type="button"
              className="btn btn--primary"
              onClick={onRetry}
            >
              Return to Upload
            </button>
          </div>
        </div>
      ) : (
        <div className="card pipeline-card">
          <div className="pipeline-card__header">
            <div>
              <span className="pipeline-card__label">
                VERIFICATION PIPELINE
              </span>
              <h3 className="pipeline-card__title">
                Automated screening in progress
              </h3>
            </div>

            <div className="pipeline-live-status">
              <span className="pipeline-live-status__dot" />
              Processing
            </div>
          </div>

          <div className="pipeline-progress-line">
            <div
              className="pipeline-progress-line__fill"
              style={{
                width: `${
                  PIPELINE_STAGES.length > 1
                    ? (currentStageIndex / (PIPELINE_STAGES.length - 1)) * 100
                    : 100
                }%`,
              }}
            />
          </div>

          <div className="pipeline-steps">
            {PIPELINE_STAGES.map((stage, index) => {
              let status = 'pending';

              if (index < currentStageIndex) {
                status = 'done';
              } else if (index === currentStageIndex) {
                status = 'active';
              }

              return (
                <div
                  key={stage.key}
                  className={`pipeline-step pipeline-step--${status}`}
                >
                  <div className="pipeline-step__indicator">
                    {status === 'done' && '✓'}

                    {status === 'active' && (
                      <span className="spinner" />
                    )}

                    {status === 'pending' && index + 1}
                  </div>

                  <div className="pipeline-step__content">
                    <div className="pipeline-step__label">
                      {stage.label}
                    </div>

                    <div className="pipeline-step__status">
                      {status === 'done' && 'Verification complete'}
                      {status === 'active' && 'Analyzing...'}
                      {status === 'pending' && 'Waiting'}
                    </div>
                  </div>

                  <div className="pipeline-step__state">
                    {status === 'done' && 'Complete'}
                    {status === 'active' && 'Active'}
                    {status === 'pending' && 'Pending'}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pipeline-card__footer">
            <span>
              Please keep this window open while screening is in progress.
            </span>

            <span className="pipeline-secure-label">
              Secure processing
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default PipelineProgress;