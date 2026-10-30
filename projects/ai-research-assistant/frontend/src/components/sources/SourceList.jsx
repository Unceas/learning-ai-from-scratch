/**
 * SourceList component.
 *
 * Renders ordered list of source provenance cards with selection highlighting
 * and click propagation.
 */

import { memo } from "react";
import SourceCard from "./SourceCard";

function SourceList({
  sources = [],
  selectedSource,
  onSourceClick,
}) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className="source-list">
      <div className="source-list-title">
        Sources
      </div>

      <div className="source-list-items">
        {sources.map((source, index) => {
          const sourceId = source.id || `S${index + 1}`;

          return (
            <SourceCard
              key={sourceId}
              source={source}
              index={index}
              selected={
                selectedSource === source ||
                selectedSource === sourceId ||
                selectedSource?.id === sourceId
              }
              onClick={onSourceClick}
            />
          );
        })}
      </div>
    </div>
  );
}

export default memo(SourceList);
