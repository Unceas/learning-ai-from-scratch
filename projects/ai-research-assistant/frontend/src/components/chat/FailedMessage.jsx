/**
 * FailedMessage component.
 *
 * Displays inline notification and retry action for failed user messages.
 */

export default function FailedMessage({ onRetry }) {
  return (
    <div className="failed-message">
      <span>Failed to send.</span>

      {onRetry && (
        <button type="button" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
