import { useState } from "react";
import type { TestResult } from "../api/types";
import { formatMemory, formatTime } from "../lib/format";
import { CodeBlock, StatusText } from "./ui";

export function TestResults({ results }: { results: TestResult[] }) {
  const firstFailure = results.find((r) => !r.passed)?.index ?? null;
  const [open, setOpen] = useState<number | null>(firstFailure);

  return (
    <ul className="divide-y divide-line overflow-hidden rounded-lg ring-1 ring-inset ring-line">
      {results.map((r) => {
        const expandable = r.is_sample || Boolean(r.stderr);
        const expanded = open === r.index && expandable;
        return (
          <li key={r.index} className="bg-raised/40">
            <button
              type="button"
              disabled={!expandable}
              onClick={() => setOpen(expanded ? null : r.index)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm enabled:hover:bg-hover"
              aria-expanded={expandable ? expanded : undefined}
            >
              <span
                aria-hidden
                className={`grid size-5 shrink-0 place-items-center rounded-full text-xs font-bold ${
                  r.passed ? "bg-accent/15 text-accent-strong" : "bg-danger/15 text-danger"
                }`}
              >
                {r.passed ? "✓" : "✗"}
              </span>
              <span className="font-medium text-ink">Test Case {r.index}</span>
              <span className="text-xs text-muted">{r.is_sample ? "sample" : "hidden"}</span>
              <StatusText status={r.status} className="ml-auto text-xs" />
              <span className="hidden w-16 text-right font-mono text-xs text-muted sm:inline">{formatTime(r.time_ms)}</span>
              <span className="hidden w-16 text-right font-mono text-xs text-muted sm:inline">{formatMemory(r.memory_kb)}</span>
              <span aria-hidden className="w-3 text-xs text-muted">{expandable ? (expanded ? "▾" : "▸") : ""}</span>
            </button>
            {expanded && (
              <div className="space-y-3 border-t border-line px-3 py-3">
                {r.input != null && <CodeBlock label="Input">{r.input}</CodeBlock>}
                {r.expected_output != null && <CodeBlock label="Expected output">{r.expected_output}</CodeBlock>}
                {r.actual_output != null && <CodeBlock label="Your output">{r.actual_output || "(no output)"}</CodeBlock>}
                {r.stderr && <CodeBlock label="Error output" tone="bad">{r.stderr}</CodeBlock>}
                {!r.is_sample && (
                  <p className="text-xs text-muted">Hidden test case: input and expected output are not shown.</p>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
