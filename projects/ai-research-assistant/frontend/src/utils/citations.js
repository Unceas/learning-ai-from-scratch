/**
 * Citation and source mapping utilities.
 *
 * Provides citation pattern detection, ID extraction, source map indexing,
 * and citation validity verification.
 */

const CITATION_PATTERN = /\[S(\d+)\]/g;

export function getCitationIds(text = "") {
  const ids = [];
  let match;
  const regex = new RegExp(CITATION_PATTERN.source, "g");

  while ((match = regex.exec(text)) !== null) {
    ids.push(`S${match[1]}`);
  }

  return [...new Set(ids)];
}

export function normalizeSourceId(source, index) {
  return source?.id || `S${index + 1}`;
}

export function getSourceMap(sources = []) {
  const safeSources = Array.isArray(sources) ? sources : [];
  return safeSources.reduce((map, source, index) => {
    const id = normalizeSourceId(source, index);
    map[id] = source;
    return map;
  }, {});
}

export function isValidCitation(citationId, sourceMap = {}) {
  return Boolean(sourceMap && sourceMap[citationId]);
}
