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
        <h1>Running Verification Pipeline</h1>
        <p className="text-muted">Analyzing document integrity, biometrics, and security features.</p>
      </div>

      {error ? (
        <div className="card">
          <div className="alert alert--error" style={{ marginBottom: '1.5rem' }}>
            <strong>Screening Failed:</strong> {error}
          </div>
          <button className="btn btn--primary" onClick={onRetry}>
            Return to Upload
          </button>
        </div>
      ) : (
        <div className="card pipeline-card">
          {PIPELINE_STAGES.map((stage, index) => {
            let status = 'pending';
            if (index < currentStageIndex) status = 'done';
            else if (index === currentStageIndex) status = 'active';

            return (
              <div key={stage.key} className={`pipeline-step pipeline-step--${status}`}>
                <div className="pipeline-step__indicator">
                  {status === 'done' && '✓'}
                  {status === 'active' && <span className="spinner" />}
                  {status === 'pending' && index + 1}
                </div>
                <div className="pipeline-step__label">{stage.label}</div>
                <div className="pipeline-step__status">
                  {status === 'done' && 'Complete'}
                  {status === 'active' && 'Processing...'}
                  {status === 'pending' && 'Waiting'}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PipelineProgress;