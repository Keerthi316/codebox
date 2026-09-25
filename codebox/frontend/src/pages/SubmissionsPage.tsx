import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { SubmissionList } from "../api/types";
import { Button, ErrorBanner, PageShell, Spinner, StatusPill } from "../components/ui";
import { formatDate, formatMemory, formatTime, LANGUAGE_LABEL } from "../lib/format";

const FILTERS = [
  { id: "", label: "All" },
  { id: "submit", label: "Submissions" },
  { id: "run", label: "Runs" },
];
const PAGE_SIZE = 20;

export function SubmissionsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const kind = params.get("kind") ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [data, setData] = useState<SubmissionList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    api
      .submissions({ page, page_size: PAGE_SIZE, kind: kind || undefined })
      .then(setData)
      .catch((e) => setError(e.message));
  }, [kind, page]);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const go = (next: Record<string, string>) => setParams({ kind, page: String(page), ...next });

  return (
    <PageShell>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Submission history</h1>
          <p className="mt-1 text-sm text-muted">Every run and submission you have made. Only you can see these.</p>
        </div>
        <div className="flex rounded-lg bg-panel p-1 ring-1 ring-line">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              onClick={() => go({ kind: f.id, page: "1" })}
              className={`rounded-md px-3 py-1 text-sm ${kind === f.id ? "bg-hover text-ink" : "text-muted hover:text-ink"}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <ErrorBanner>{error}</ErrorBanner>}
      {!data && !error && (
        <div className="flex justify-center py-16 text-muted">
          <Spinner className="size-5" />
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="rounded-xl bg-panel p-10 text-center text-sm text-muted ring-1 ring-line">
          Nothing here yet. Solve a problem or try the playground.
        </div>
      )}
      {data && data.items.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-xl ring-1 ring-line">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-panel text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Problem</th>
                  <th className="px-4 py-3 font-medium">Language</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 text-right font-medium">Runtime</th>
                  <th className="px-4 py-3 text-right font-medium">Memory</th>
                  <th className="px-4 py-3 text-right font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.items.map((s) => (
                  <tr
                    key={s.id}
                    onClick={() => navigate(`/submissions/${s.id}`)}
                    className="cursor-pointer bg-canvas transition-colors hover:bg-panel"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink">{s.problem_title ?? "Playground"}</div>
                      <div className="text-xs text-muted">{s.kind === "submit" ? "Submission" : "Run"}</div>
                    </td>
                    <td className="px-4 py-3 text-ink-soft">{LANGUAGE_LABEL[s.language] ?? s.language}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatusPill status={s.status} />
                        {s.total_count != null && (
                          <span className="font-mono text-xs text-muted">
                            {s.passed_count}/{s.total_count}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-ink-soft">{formatTime(s.execution_time)}</td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-ink-soft">{formatMemory(s.memory_used)}</td>
                    <td className="px-4 py-3 text-right text-xs text-muted">{formatDate(s.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-4 flex items-center justify-between text-sm text-muted">
            <span>
              {data.total} total · page {page} of {pages}
            </span>
            <div className="flex gap-2">
              <Button disabled={page <= 1} onClick={() => go({ page: String(page - 1) })}>
                ← Previous
              </Button>
              <Button disabled={page >= pages} onClick={() => go({ page: String(page + 1) })}>
                Next →
              </Button>
            </div>
          </div>
        </>
      )}
    </PageShell>
  );
}
