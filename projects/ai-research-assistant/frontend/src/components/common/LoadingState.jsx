/**
 * LoadingState component.
 *
 * Displays a spinner and descriptive message during asynchronous data retrieval.
 */

export default function LoadingState({ message = "Loading..." }) {
  return (
    <div className="state-container">
      <div className="loading-spinner" />
      <p>{message}</p>
    </div>
  );
}
