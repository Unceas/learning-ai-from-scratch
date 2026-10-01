/**
 * SourceList component.
 *
 * Renders ordered list of source attribution cards below the assistant answer.
 */

import SourceCard from "./SourceCard";

export default function SourceList({ sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <section className="source-list">
      <div className="source-list-header">
        <h3>Sources</h3>
        <span>{sources.length}</span>
      </div>

      <div className="source-list-items">
        {sources.map((source) => (
          <SourceCard
            key={source.id}
            source={source}
          />
        ))}
      </div>
    </section>
  );
}
