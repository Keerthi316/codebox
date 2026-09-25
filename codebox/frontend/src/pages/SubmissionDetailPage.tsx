import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { SubmissionDetail } from "../api/types";
import { CodeEditor } from "../components/CodeEditor";
import { TestResults } from "../components/TestResults";
import { CodeBlock, ErrorBanner, Metric, PageShell, Spinner, StatusText } from "../components/ui";
import { formatDate, formatMemory, formatTime, isPending, LANGUAGE_LABEL } from "../lib/format";

export function SubmissionDetailPage() {
  const { id } = useParams();
  const [sub, setSub] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;
    const load = () =>
      api
        .submission(Number(id))
        .then((s) => {
          if (cancelled) return;
          setSub(s);
          if (isPending(s.status)) timer = window.setTimeout(load, 1000);
        })
        .catch((e) => !cancelled && setError(e.message));
    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [id]);

  if (error)
    return (
      <PageShell>
        <ErrorBanner>{error}</ErrorBanner>
      </PageShell>
    );
  if (!sub)
    return (
      <div className="grid flex-1 place-items-center text-muted">
        <Spinner className="size-5" />
      </div>
    );

  const judged = sub.kind === "submit";
  const lines = Math.min(40, Math.max(8, sub.source_code.split("\n").length + 1));

  return (
    <PageShell>
      <Link to="/submissions" className="text-sm text-muted hover:text-ink">
        ← All submissions
      </Link>
      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">
            {sub.problem_title ?? "Playground run"}{" "}
            <span className="text-base font-normal text-muted">#{sub.id}</span>
          </h1>
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <StatusText status={sub.status} className="text-lg font-semibold" />
            {judged && sub.total_count != null && (
              <span className="text-sm text-ink-soft">
                Passed <span className="font-mono font-semibold text-ink">{sub.passed_count}/{sub.total_count}</span> test cases
              </span>
            )}
          </div>
        </div>
        {sub.problem_id && (
          <Link
            to={`/problems/${sub.problem_id}`}
            className="rounded-md bg-raised px-3 py-1.5 text-sm text-ink ring-1 ring-inset ring-line-strong hover:bg-hover"
          >
            Open problem →
          </Link>
        )}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Metric label="Language" value={LANGUAGE_LABEL[sub.language] ?? sub.language} />
        <Metric label={judged ? "Max runtime" : "Runtime"} value={formatTime(sub.execution_time)} />
        <Metric label={judged ? "Peak memory" : "Memory"} value={formatMemory(sub.memory_used)} />
        <Metric label="Submitted" value={formatDate(sub.created_at)} />
      </div>

      {sub.error_message && sub.status === "FAILED" && (
        <div className="mt-4">
          <ErrorBanner>{sub.error_message}</ErrorBanner>
        </div>
      )}

      <section className="mt-6">
        <h2 className="mb-2 text-sm font-medium text-muted">Source code</h2>
        <div className="overflow-hidden rounded-lg ring-1 ring-line" style={{ height: `${lines * 20 + 24}px` }}>
          <CodeEditor language={sub.language} value={sub.source_code} readOnly />
        </div>
      </section>

      <section className="mt-6 space-y-4">
        {sub.compile_output && (
          <CodeBlock label="Compiler output" tone="bad">
            {sub.compile_output}
          </CodeBlock>
        )}
        {judged && sub.test_results && sub.test_results.length > 0 && (
          <div>
            <h2 className="mb-2 text-sm font-medium text-muted">Test results</h2>
            <TestResults results={sub.test_results} />
          </div>
        )}
        {!judged && (
          <div className="grid gap-4 md:grid-cols-2">
            <CodeBlock label="Input (stdin)">{sub.stdin || <span className="text-muted">(empty)</span>}</CodeBlock>
            <CodeBlock label="Output (stdout)">{sub.stdout || <span className="text-muted">(no output)</span>}</CodeBlock>
          </div>
        )}
        {sub.stderr && (
          <CodeBlock label="Errors (stderr)" tone="bad">
            {sub.stderr}
          </CodeBlock>
        )}
      </section>
    </PageShell>
  );
}
