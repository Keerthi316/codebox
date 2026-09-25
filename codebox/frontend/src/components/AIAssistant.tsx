import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { AIAction, AIResponse, ExecutionResult } from "../api/types";
import { Markdown } from "./Markdown";
import { Button, ErrorBanner, Spinner } from "./ui";

const ACTIONS: { id: AIAction; label: string; hint: string }[] = [
  { id: "explain", label: "Explain", hint: "Walk through what the code does" },
  { id: "debug", label: "Debug", hint: "Find bugs and explain errors" },
  { id: "complexity", label: "Complexity", hint: "Time & space analysis" },
  { id: "optimize", label: "Optimize", hint: "Suggest improvements" },
];

interface Entry {
  prompt: string;
  response?: AIResponse;
  error?: string;
}

export function AIAssistant({
  language,
  code,
  lastResult,
  stdin,
  problemId,
}: {
  language: string;
  code: string;
  lastResult: ExecutionResult | null;
  stdin?: string;
  problemId?: number;
}) {
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .aiStatus()
      .then((s) => setEnabled(s.enabled))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => {
    // Block body on purpose: scrollIntoView returns a Promise in newer browsers, and
    // React would treat an implicitly returned value as the effect's cleanup function.
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries]);

  async function ask(action: AIAction, prompt: string, text?: string) {
    if (!code.trim() || loading) return;
    // Only the relevant context: code, language, and the last run's error/IO.
    const error =
      lastResult?.compile_output ||
      lastResult?.stderr ||
      (lastResult && lastResult.status !== "COMPLETED" && lastResult.status !== "ACCEPTED"
        ? lastResult.error_message ?? lastResult.status
        : undefined);
    setLoading(true);
    setEntries((e) => [...e, { prompt }]);
    try {
      const response = await api.assist({
        action,
        language,
        source_code: code,
        question: text || undefined,
        error: error || undefined,
        stdin: lastResult?.kind === "run" ? stdin || undefined : undefined,
        stdout: lastResult?.kind === "run" ? lastResult.stdout || undefined : undefined,
        problem_id: problemId,
      });
      setEntries((e) => e.map((x, i) => (i === e.length - 1 ? { ...x, response } : x)));
    } catch (err) {
      const message = err instanceof Error ? err.message : "AI request failed";
      setEntries((e) => e.map((x, i) => (i === e.length - 1 ? { ...x, error: message } : x)));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        {enabled === false && (
          <div className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn ring-1 ring-inset ring-warn/25">
            The AI assistant is not configured on this server (set{" "}
            <code className="font-mono">OPENROUTER_API_KEY</code> or <code className="font-mono">OPENAI_API_KEY</code>).
            Everything else keeps working.
          </div>
        )}
        {entries.length === 0 && (
          <div className="space-y-2 text-sm text-muted">
            <p className="text-ink-soft">Ask the assistant about your current code.</p>
            <p>
              It sees your code, the language and, after a run, the error and input/output — nothing else. Pick an action
              or type a question; questions are routed to the right specialist automatically.
            </p>
          </div>
        )}
        {entries.map((entry, i) => (
          <div key={i} className="space-y-2">
            <div className="ml-auto w-fit max-w-[85%] rounded-lg rounded-br-sm bg-accent/15 px-3 py-2 text-sm text-ink">
              {entry.prompt}
            </div>
            {entry.response && (
              <div className="rounded-lg rounded-bl-sm bg-raised px-3 py-2 ring-1 ring-inset ring-line">
                <div className="mb-1 text-[11px] font-medium uppercase tracking-wide text-accent-strong">
                  {entry.response.agent}
                </div>
                <Markdown>{entry.response.content}</Markdown>
              </div>
            )}
            {entry.error && <ErrorBanner>{entry.error}</ErrorBanner>}
            {!entry.response && !entry.error && (
              <div className="flex items-center gap-2 text-sm text-muted">
                <Spinner /> Thinking…
              </div>
            )}
          </div>
        ))}
        <div ref={bottom} />
      </div>

      <div className="space-y-2 border-t border-line bg-panel p-3">
        <div className="flex flex-wrap gap-1.5">
          {ACTIONS.map((a) => (
            <button
              key={a.id}
              title={a.hint}
              disabled={loading || enabled === false}
              onClick={() => ask(a.id, a.label + " my code")}
              className="rounded-full bg-raised px-3 py-1 text-xs text-ink-soft ring-1 ring-inset ring-line-strong transition-colors hover:bg-hover hover:text-ink disabled:opacity-50"
            >
              {a.label}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!question.trim()) return;
            ask("auto", question.trim(), question.trim());
            setQuestion("");
          }}
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            disabled={enabled === false}
            placeholder="Ask anything, e.g. “why does test 3 fail?”"
            className="min-w-0 flex-1 rounded-md bg-canvas px-3 py-1.5 text-sm text-ink ring-1 ring-inset ring-line-strong placeholder:text-muted focus:outline-none focus:ring-accent"
          />
          <Button type="submit" variant="primary" disabled={!question.trim() || enabled === false} loading={loading}>
            Ask
          </Button>
        </form>
      </div>
    </div>
  );
}
