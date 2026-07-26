"use client";

import { useState } from "react";
import { openDocument, type Source } from "@/lib/api";

// An inline [n] citation: click opens the source doc in a new tab; hover shows
// which document it points to.
export function InlineCitation({ n, source }: { n: number; source: Source }) {
  const [hover, setHover] = useState(false);

  function open() {
    if (source.document_id) {
      openDocument(source.document_id).catch(() => {
        // 401 clears the token in the api layer; ignore other transient errors.
      });
    }
  }

  return (
    <span
      className="relative inline-block align-baseline"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <button
        type="button"
        onClick={open}
        className="mx-0.5 rounded bg-blue-100 px-1 align-baseline text-xs font-medium text-blue-700 hover:bg-blue-200 dark:bg-blue-950 dark:text-blue-300 dark:hover:bg-blue-900"
      >
        [{n}]
      </button>
      {hover && (
        <span
          onClick={open}
          className="absolute bottom-full left-1/2 z-20 mb-1 w-max max-w-[16rem] -translate-x-1/2 cursor-pointer truncate rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs font-normal text-zinc-700 shadow-md dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
        >
          {source.filename} · open in new tab
        </span>
      )}
    </span>
  );
}
