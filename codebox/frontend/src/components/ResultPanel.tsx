import type { ExecutionResult } from "../api/types";
import { formatMemory, formatTime, isPending, LANGUAGE_LABEL, STATUS_LABEL } from "../lib/format";
import { TestResults } from "./TestResults";
import { CodeBlock, ErrorBanner, Metric, Spinner, StatusText } from "./ui";

export function ResultPanel({
  result,
  busy,
  error,
}: {
  result: ExecutionResult | null;
  busy: null | "run" | "submit";
  error: string | null;
}) {
  if (error) {
    return (
      <div className="p-4">
        <ErrorBanner>{error}</ErrorBanner>
      </div>
    );
  }
  if (!result || isPending(result.status)) {
    if (!busy) {
      return (
        <div className="grid h-full place-items-center p-6 text-center text-sm text-muted">
          <div>
            <p>Run your code to see the output here.</p>
            <p className="mt-1 text-xs">
              Tip: press <kbd className="rounded bg-raised px-1.5 py-0.5 font-mono ring-1 ring-line">Ctrl</kbd> +{" "}
              <kbd className="rounded bg-raised px-1.5 py-0.5 font-mono ring-1 ring-line">Enter</kbd> in the editor.
            </p>
          </div>
        </div>
      );
    }
    return (
      <div className="flex h-full items-center justify-center gap-3 p-6 text-sm text-info">
        <Spinner className="size-4" />
        {result?.status === "RUNNING"
          ? busy === "submit"
            ? "Judging against test cases in the sandbox…"
            : "Running in the sandbox…"
          : "Queued…"}
      </div>
    );
  }

  const judged = result.kind === "submit";
  const compileError = result.status === "COMPILATION_ERROR";
  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <StatusText status={result.status} className="text-lg font-semibold" />
        {judged && result.total_count != null && (
          <span className="text-sm text-ink-soft">
            Passed{" "}
            <span className="font-mono font-semibold text-ink">
              {result.passed_count ?? 0}/{result.total_count}
            </span>{" "}
            test cases
          </span>
        )}
        {result.error_message && !judged && result.status !== "COMPLETED" && (
          <span className="text-sm text-muted">{result.error_message}</span>
        )}
      </div>

      {result.status === "FAILED" && (
        <ErrorBanner>{result.error_message ?? STATUS_LABEL.FAILED}</ErrorBanner>
      )}

      {!compileError && result.status !== "FAILED" && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <Metric label={judged ? "Max runtime" : "Runtime"} value={formatTime(result.execution_time)} />
          <Metric label={judged ? "Peak memory" : "Memory"} value={formatMemory(result.memory_used)} />
          <Metric label="Language" value={LANGUAGE_LABEL[result.language] ?? result.language} />
        </div>
      )}

      {result.compile_output && (
        <CodeBlock label="Compiler output" tone="bad">
          {result.compile_output}
        </CodeBlock>
      )}

      {judged && result.test_results && result.test_results.length > 0 && <TestResults results={result.test_results} />}

      {!judged && !compileError && result.status !== "FAILED" && (
        <CodeBlock label="Output (stdout)">{result.stdout || <span className="text-muted">(no output)</span>}</CodeBlock>
      )}
      {result.stderr && !compileError && (
        <CodeBlock label="Errors (stderr)" tone="bad">
          {result.stderr}
        </CodeBlock>
      )}
    </div>
  );
}
