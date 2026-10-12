import { useState } from "react";
import { submitFeedback } from "../../api/feedback";

/**
 * AnswerFeedback component.
 *
 * Captures user feedback (helpful / not helpful) on persisted assistant messages,
 * providing structured failure reason categorization and comment capture.
 */
export default function AnswerFeedback({ messageId }) {
  const [rating, setRating] = useState(null);
  const [reason, setReason] = useState("");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");

  if (!messageId) {
    return null;
  }

  async function handleSubmit(nextRating) {
    setSaving(true);
    setError("");

    try {
      await submitFeedback({
        message_id: messageId,
        rating: nextRating,
        reason: nextRating === "not_helpful" ? reason || null : null,
        comment: comment.trim() || null,
      });

      setRating(nextRating);
      setSubmitted(true);
    } catch {
      setError("Feedback could not be saved. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="answer-feedback" aria-label="Answer feedback">
      <span>Was this answer helpful?</span>

      <div className="feedback-actions">
        <button
          type="button"
          disabled={saving}
          aria-pressed={rating === "helpful"}
          className={`feedback-btn ${rating === "helpful" ? "active" : ""}`}
          onClick={() => handleSubmit("helpful")}
        >
          Helpful
        </button>

        <button
          type="button"
          disabled={saving}
          aria-pressed={rating === "not_helpful"}
          className={`feedback-btn ${rating === "not_helpful" ? "active" : ""}`}
          onClick={() => {
            setRating("not_helpful");
            setSubmitted(false);
          }}
        >
          Not helpful
        </button>
      </div>

      {rating === "not_helpful" && !submitted && (
        <div className="feedback-details">
          <label>
            <span>What went wrong?</span>
            <select
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              aria-label="Reason for feedback"
            >
              <option value="">Select a reason</option>
              <option value="incorrect">Incorrect information</option>
              <option value="missing_evidence">Missing evidence</option>
              <option value="poor_retrieval">Wrong sources retrieved</option>
              <option value="incomplete">Incomplete answer</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            <span>Optional details</span>
            <textarea
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="What should the answer have included?"
              aria-label="Optional details"
            />
          </label>

          <button
            type="button"
            disabled={saving}
            className="feedback-submit-btn"
            onClick={() => handleSubmit("not_helpful")}
          >
            {saving ? "Saving..." : "Submit feedback"}
          </button>
        </div>
      )}

      {submitted && (
        <p className="feedback-thanks">Thanks for your feedback.</p>
      )}

      {error && (
        <p role="alert" className="feedback-error">
          {error}
        </p>
      )}
    </div>
  );
}
