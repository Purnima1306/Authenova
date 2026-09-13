import { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
      const response = await fetch(`${API_BASE_URL}/api/v1/decision/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action, comment }),
      });

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
      // Fall back to local recording if offline
      setRecordedDecision({ action, comment });
      setSubmitError('Note: Decision recorded locally (server connection error).');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="card">
      <h3 className="card__title">Officer Decision</h3>
      <p className="text-muted card__subtitle">
        Record your final decision based on the evidence above.
      </p>

      <label className="form-label" htmlFor="comment">
        Comment (optional)
      </label>
      <textarea
        id="comment"
        className="form-textarea"
        placeholder="Add any notes for the case file..."
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={3}
      />

      <div className="decision-actions">
        <button
          className="btn btn--pass"
          disabled={isSubmitting}
          onClick={() => handleDecision('Approved')}
        >
          Approve
        </button>
        <button
          className="btn btn--warning"
          disabled={isSubmitting}
          onClick={() => handleDecision('Flagged for Review')}
        >
          Flag for Review
        </button>
        <button
          className="btn btn--fail"
          disabled={isSubmitting}
          onClick={() => handleDecision('Rejected')}
        >
          Reject
        </button>
      </div>

      {submitError && <div className="alert alert--warning">{submitError}</div>}

      {recordedDecision && (
        <div className="alert alert--success">
          Decision recorded: <strong>{recordedDecision.action}</strong>
          {recordedDecision.comment && (
            <span> — "{recordedDecision.comment}"</span>
          )}
        </div>
      )}
    </div>
  );
}

export default OfficerDecision;
