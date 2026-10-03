/**
 * ErrorState component.
 *
 * Displays error explanations with an optional retry trigger.
 */

export default function ErrorState({
  message = "Something went wrong.",
  onRetry,
}) {
  return (
    <div className="state-container error-state">
      <p>{message}</p>

      {onRetry && (
        <button onClick={onRetry} type="button">
          Retry
        </button>
      )}
    </div>
  );
}
