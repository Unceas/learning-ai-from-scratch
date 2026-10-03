/**
 * EmptyState component.
 *
 * Displays placeholder visuals, title, description, and actions when content is absent.
 */

export default function EmptyState({
  title,
  description,
  action,
}) {
  return (
    <div className="state-container empty-state">
      {title && <h3>{title}</h3>}

      {description && <p>{description}</p>}

      {action && action}
    </div>
  );
}
