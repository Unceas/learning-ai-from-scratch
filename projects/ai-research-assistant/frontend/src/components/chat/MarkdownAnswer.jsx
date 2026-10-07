/**
 * MarkdownAnswer component.
 *
 * Renders research answers formatted in Markdown with GitHub Flavored Markdown (GFM),
 * dynamically converting valid [S1] citation references in prose into interactive,
 * accessible source buttons while protecting code blocks and unrecognized citations.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getSourceMap } from "../../utils/citations";

export function transformCitations(markdown, sourceMap = {}) {
  if (!markdown) return "";

  // Split text by fenced code blocks (```...```) and inline code (`...`) to avoid modifying code contents
  const parts = markdown.split(/(```[\s\S]*?```|`[^`\n]*`)/g);

  return parts
    .map((part) => {
      if (part.startsWith("```") || part.startsWith("`")) {
        return part;
      }

      return part.replace(/(?<![`])\[S(\d+)\](?![`])/g, (match, number) => {
        const id = `S${number}`;

        if (!sourceMap[id]) {
          return match;
        }

        return `[${id}](#source-${id})`;
      });
    })
    .join("");
}

export default function MarkdownAnswer({
  content,
  sources = [],
  onSourceClick,
}) {
  const sourceMap = getSourceMap(sources);
  const markdown = transformCitations(content, sourceMap);

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children, ...props }) {
            if (href?.startsWith("#source-")) {
              const sourceId = href.replace("#source-", "");

              return (
                <button
                  type="button"
                  className="citation-badge"
                  onClick={() => onSourceClick?.(sourceId)}
                  aria-label={`Open source ${sourceId}`}
                >
                  {children}
                </button>
              );
            }

            return (
              <a
                href={href}
                target="_blank"
                rel="noreferrer"
                {...props}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
