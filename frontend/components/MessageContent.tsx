"use client";

import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import { InlineCitation } from "@/components/InlineCitation";
import { type Source } from "@/lib/api";

export function MessageContent({
  content,
  sources,
}: {
  content: string;
  sources: Source[];
}) {
  const byNumber = new Map<number, Source>();
  for (const s of sources) {
    byNumber.set(s.n, s);
  }

  // The raw [n] are retrieval positions (can start at any number). Renumber the
  // cited ones to sequential [1], [2], ... in order of first appearance.
  const displayOf = new Map<number, number>();
  for (const match of content.matchAll(/\[(\d+)\]/g)) {
    const n = Number(match[1]);
    if (byNumber.has(n) && !displayOf.has(n)) {
      displayOf.set(n, displayOf.size + 1);
    }
  }

  // Turn known [n] citations into markdown links with a cite: scheme (display
  // number as text, original n in the URL), which the custom `a` renderer below
  // swaps for an InlineCitation. Unknown [n] stay as plain text.
  const processed = content.replace(/\[(\d+)\]/g, (match, digits) => {
    const n = Number(digits);
    return displayOf.has(n) ? `[${displayOf.get(n)}](cite:${n})` : match;
  });

  return (
    <div className="message-md text-sm leading-6">
      <ReactMarkdown
        // Preserve our cite: links (react-markdown strips unknown URL schemes by
        // default); everything else still goes through the standard sanitizer.
        urlTransform={(url) =>
          url.startsWith("cite:") ? url : defaultUrlTransform(url)
        }
        components={{
          a({ href, children }) {
            const m = typeof href === "string" ? href.match(/^cite:(\d+)$/) : null;
            if (m) {
              const n = Number(m[1]);
              const source = byNumber.get(n);
              const display = displayOf.get(n);
              if (source && display) {
                return <InlineCitation n={display} source={source} />;
              }
            }
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 underline dark:text-blue-400"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {processed}
      </ReactMarkdown>
    </div>
  );
}
