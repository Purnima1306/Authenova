import { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

function OfficerDecision({ documentId, initialDecision, onDecisionRecorded }) {
  const [comment, setComment] = useState(initialDecision?.comment || '');
  const [recordedDecision, setRecordedDecision] = useState(initialDecision || null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  async function handleDecision(action) {
    if (!documentId) {
      setRecordedDecision({ action, comment });
      return;
    }

    setIsSubmitting(true);
    setSubmitError('');

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/decision/${documentId}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ action, comment }),
        }
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      const decisionObj = data.decision || { action, comment };

      setRecordedDecision(decisionObj);

      if (onDecisionRecorded) {
        onDecisionRecorded(decisionObj);
      }
    } catch (err) {
      console.error('Failed to submit decision:', err);
      setRecordedDecision({ action, comment });
      setSubmitError(
        'Note: Decision recorded locally (server connection error).'
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="card officer-decision-card">
      <div className="officer-decision__header">
        <div>
          <span className="officer-decision__eyebrow">
            FINAL REVIEW
          </span>

          <h3 className="card__title">Officer Decision</h3>

          <p className="text-muted officer-decision__subtitle">
            Record your final decision based on the evidence above.
          </p>
        </div>

        <div className="officer-decision__secure">
          <span className="officer-decision__secure-dot" />
          Officer Review
        </div>
      </div>

      <div className="officer-decision__body">
        <label className="form-label" htmlFor="comment">
          Case Comment
          <span className="officer-decision__optional">Optional</span>
        </label>

        <textarea
          id="comment"
          className="form-textarea officer-decision__textarea"
          placeholder="Add any notes for the case file..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          rows={4}
        />

        <div className="officer-decision__actions-label">
          Select final decision
        </div>

        <div className="decision-actions">
          <button
            type="button"
            className="btn btn--pass"
            disabled={isSubmitting}
            onClick={() => handleDecision('Approved')}
          >
            <span className="decision-button__icon">✓</span>
            Approve
          </button>

          <button
            type="button"
            className="btn btn--warning"
            disabled={isSubmitting}
            onClick={() => handleDecision('Flagged for Review')}
          >
            <span className="decision-button__icon">!</span>
            Flag for Review
          </button>

          <button
            type="button"
            className="btn btn--fail"
            disabled={isSubmitting}
            onClick={() => handleDecision('Rejected')}
          >
            <span className="decision-button__icon">✕</span>
            Reject
          </button>
        </div>
      </div>

      {submitError && (
        <div className="alert alert--warning officer-decision__alert">
          {submitError}
        </div>
      )}
      {recordedDecision && (
        <div className="alret alert--success officer-decision__alert">
          <span>Desicion reorded: </span>
          <strong>{recordedDecision.action}</strong>
          {recordedDecision.comment && (
            <span> -
              "{recordedDecision.comment}"</span>
          )}
          
        </div>
      )}
      </div>
  );
}
export default OfficerDecision
      