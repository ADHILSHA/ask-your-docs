import { type AskResponse } from "@/lib/api";

export function AnswerView({ result }: { result: AskResponse }) {
  return (
    <section className="flex flex-col gap-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div>
        <h2 className="mb-2 text-sm font-medium">Answer</h2>
        <p className="whitespace-pre-wrap text-sm leading-6">{result.answer}</p>
      </div>

      {result.sources.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium">Sources</h3>
          <ul className="flex flex-col gap-1">
            {result.sources.map((s, i) => (
              <li
                key={`${s.filename}-${s.chunk_index}-${i}`}
                className="font-mono text-xs text-zinc-600 dark:text-zinc-400"
              >
                {s.filename} #{s.chunk_index + 1}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
