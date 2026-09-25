import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { ProblemSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ErrorBanner, Spinner } from "../components/ui";

type Difficulty = ProblemSummary["difficulty"];
type StatusFilter = "all" | "todo" | "attempted" | "solved";

const DIFFICULTIES: Difficulty[] = ["Easy", "Medium", "Hard"];
const DIFF_STYLE: Record<Difficulty, { text: string; bar: string; pill: string }> = {
  Easy: { text: "text-accent-strong", bar: "bg-accent", pill: "bg-accent/10 text-accent-strong ring-accent/25" },
  Medium: { text: "text-warn", bar: "bg-warn", pill: "bg-warn/10 text-warn ring-warn/25" },
  Hard: { text: "text-danger", bar: "bg-danger", pill: "bg-danger/10 text-danger ring-danger/25" },
};

function greeting(): string {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

// ----------------------------------------------------------------- small pieces

function StatusIcon({ p }: { p: ProblemSummary }) {
  if (p.solved)
    return (
      <span title="Solved" className="grid size-5 place-items-center rounded-full bg-accent/15 text-[11px] font-bold text-accent-strong">
        ✓
      </span>
    );
  if (p.attempted)
    return (
      <span title="Attempted" className="grid size-5 place-items-center">
        <svg viewBox="0 0 20 20" className="size-5 text-warn" aria-hidden>
          <circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" strokeOpacity="0.3" strokeWidth="2" />
          <path d="M10 2.5a7.5 7.5 0 0 1 0 15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </span>
    );
  return <span title="Not started" className="block size-5 rounded-full ring-2 ring-inset ring-line-strong" />;
}

function ProgressRing({ value, total }: { value: number; total: number }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const pct = total ? value / total : 0;
  return (
    <div className="relative size-28 shrink-0">
      <svg viewBox="0 0 100 100" className="size-full -rotate-90" aria-hidden>
        <circle cx="50" cy="50" r={r} fill="none" stroke="var(--color-line)" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          className="transition-[stroke-dashoffset] duration-700"
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="font-mono text-2xl font-semibold text-ink">
            {value}
            <span className="text-base text-muted">/{total}</span>
          </div>
          <div className="text-[11px] uppercase tracking-wide text-muted">solved</div>
        </div>
      </div>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`whitespace-nowrap rounded-full px-3 py-1 text-xs transition-colors ring-1 ring-inset ${
        active ? "bg-accent/15 text-accent-strong ring-accent/40" : "bg-raised text-ink-soft ring-line-strong hover:bg-hover hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { id: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div className="flex rounded-lg bg-panel p-1 ring-1 ring-line" role="group" aria-label={label}>
      {options.map((o) => (
        <button
          key={o.id}
          type="button"
          aria-pressed={value === o.id}
          onClick={() => onChange(o.id)}
          className={`whitespace-nowrap rounded-md px-3 py-1 text-sm transition-colors ${value === o.id ? "bg-hover text-ink" : "text-muted hover:text-ink"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Acceptance({ rate, submissions }: { rate: number | null; submissions: number }) {
  if (rate === null) return <span className="text-xs text-muted">—</span>;
  return (
    <div className="flex items-center gap-2" title={`${submissions} submission${submissions === 1 ? "" : "s"}`}>
      <div className="h-1.5 w-14 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-ink-soft/60" style={{ width: `${Math.round(rate * 100)}%` }} />
      </div>
      <span className="w-9 text-right font-mono text-xs text-ink-soft">{Math.round(rate * 100)}%</span>
    </div>
  );
}

// ----------------------------------------------------------------- page

export function ProblemsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [problems, setProblems] = useState<ProblemSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();

  const query = params.get("q") ?? "";
  const difficulty = (params.get("difficulty") ?? "all") as Difficulty | "all";
  const status = (params.get("status") ?? "all") as StatusFilter;
  const tag = params.get("tag") ?? "";

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value && value !== "all") next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  useEffect(() => {
    api
      .problems()
      .then(setProblems)
      .catch((e) => setError(e.message));
  }, []);

  const tags = useMemo(() => {
    const counts = new Map<string, number>();
    problems?.forEach((p) => p.tags.forEach((t) => counts.set(t, (counts.get(t) ?? 0) + 1)));
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  }, [problems]);

  const filtered = useMemo(() => {
    if (!problems) return [];
    const q = query.trim().toLowerCase();
    return problems.filter(
      (p) =>
        (!q || p.title.toLowerCase().includes(q) || String(p.id) === q || p.tags.some((t) => t.toLowerCase().includes(q))) &&
        (difficulty === "all" || p.difficulty === difficulty) &&
        (!tag || p.tags.includes(tag)) &&
        (status === "all" ||
          (status === "solved" && p.solved) ||
          (status === "attempted" && p.attempted) ||
          (status === "todo" && !p.solved && !p.attempted)),
    );
  }, [problems, query, difficulty, status, tag]);

  const stats = useMemo(() => {
    const byDiff = DIFFICULTIES.map((d) => {
      const all = problems?.filter((p) => p.difficulty === d) ?? [];
      return { d, total: all.length, solved: all.filter((p) => p.solved).length };
    });
    const solved = problems?.filter((p) => p.solved).length ?? 0;
    const attempted = problems?.filter((p) => p.attempted).length ?? 0;
    return { byDiff, solved, attempted, total: problems?.length ?? 0 };
  }, [problems]);

  const nextUp = useMemo(() => {
    if (!problems) return null;
    const order = (p: ProblemSummary) => DIFFICULTIES.indexOf(p.difficulty) * 1000 + p.id;
    return (
      problems.find((p) => p.attempted) ??
      [...problems].filter((p) => !p.solved).sort((a, b) => order(a) - order(b))[0] ??
      null
    );
  }, [problems]);

  function pickRandom() {
    const pool = filtered.filter((p) => !p.solved);
    const from = pool.length ? pool : filtered.length ? filtered : problems ?? [];
    if (from.length) navigate(`/problems/${from[Math.floor(Math.random() * from.length)].slug}`);
  }

  const filtersActive = Boolean(query || tag || difficulty !== "all" || status !== "all");

  if (error)
    return (
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <ErrorBanner>{error}</ErrorBanner>
      </main>
    );
  if (!problems)
    return (
      <div className="grid flex-1 place-items-center py-24 text-muted">
        <Spinner className="size-5" />
      </div>
    );

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
      {/* ------------------------------------------------ hero + progress */}
      <section className="grid gap-4 lg:grid-cols-3">
        <div className="relative overflow-hidden rounded-2xl bg-panel p-6 ring-1 ring-line lg:col-span-2">
          <div aria-hidden className="pointer-events-none absolute -right-20 -top-24 size-72 rounded-full bg-accent/10 blur-3xl" />
          <div className="relative">
            <p className="text-sm text-muted">{greeting()},</p>
            <h1 className="mt-0.5 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{user?.username}</h1>
            <p className="mt-2 max-w-lg text-sm text-ink-soft">
              {stats.solved === stats.total && stats.total > 0
                ? "You've solved every problem. Impressive! Try a different language next."
                : stats.solved === 0
                  ? "Pick a problem, write a solution in Python, JavaScript, Java or C++, and submit it against hidden tests."
                  : `${stats.solved} down, ${stats.total - stats.solved} to go. Keep the streak going.`}
            </p>

            {nextUp && (
              <div className="mt-5 flex flex-col gap-3 rounded-xl bg-canvas/60 p-4 ring-1 ring-line sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-medium uppercase tracking-wide text-muted">
                    {nextUp.attempted ? "Pick up where you left off" : "Up next"}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="truncate font-medium text-ink">
                      {nextUp.id}. {nextUp.title}
                    </span>
                    <span className={`text-xs font-medium ${DIFF_STYLE[nextUp.difficulty].text}`}>{nextUp.difficulty}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={pickRandom}
                    className="inline-flex items-center gap-1.5 rounded-md bg-raised px-3 py-1.5 text-sm text-ink-soft ring-1 ring-inset ring-line-strong hover:bg-hover hover:text-ink"
                    title="Open a random unsolved problem"
                  >
                    <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
                    </svg>
                    Random
                  </button>
                  <Link
                    to={`/problems/${nextUp.slug}`}
                    className="rounded-md bg-accent px-4 py-1.5 text-sm font-semibold text-emerald-950 hover:bg-accent-strong"
                  >
                    {nextUp.attempted ? "Continue →" : "Start →"}
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-5 rounded-2xl bg-panel p-6 ring-1 ring-line">
          <ProgressRing value={stats.solved} total={stats.total} />
          <div className="min-w-0 flex-1 space-y-3">
            {stats.byDiff.map(({ d, total, solved }) => (
              <div key={d}>
                <div className="mb-1 flex items-baseline justify-between text-xs">
                  <span className={`font-medium ${DIFF_STYLE[d].text}`}>{d}</span>
                  <span className="font-mono text-ink-soft">
                    {solved}
                    <span className="text-muted">/{total}</span>
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-line">
                  <div
                    className={`h-full rounded-full ${DIFF_STYLE[d].bar} transition-[width] duration-700`}
                    style={{ width: total ? `${(solved / total) * 100}%` : 0 }}
                  />
                </div>
              </div>
            ))}
            {stats.attempted > 0 && <p className="text-xs text-muted">{stats.attempted} in progress</p>}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------ filters */}
      <section className="mt-8 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex w-full min-w-0 items-center gap-2 rounded-lg bg-panel px-3 ring-1 ring-inset ring-line-strong focus-within:ring-2 focus-within:ring-accent sm:w-auto sm:max-w-xs sm:flex-1">
            <svg viewBox="0 0 24 24" className="size-4 shrink-0 text-muted" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
            <span className="sr-only">Search problems</span>
            <input
              value={query}
              onChange={(e) => setFilter("q", e.target.value)}
              placeholder="Search problems or topics"
              className="w-full min-w-0 bg-transparent py-2 text-sm text-ink placeholder:text-muted/70 focus:outline-none"
            />
          </label>
          <Segmented
            label="Difficulty"
            value={difficulty}
            onChange={(v) => setFilter("difficulty", v)}
            options={[{ id: "all", label: "All" }, ...DIFFICULTIES.map((d) => ({ id: d, label: d }))]}
          />
          <Segmented
            label="Status"
            value={status}
            onChange={(v) => setFilter("status", v)}
            options={[
              { id: "all", label: "Any status" },
              { id: "todo", label: "To do" },
              { id: "attempted", label: "Attempted" },
              { id: "solved", label: "Solved" },
            ]}
          />
        </div>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
          <Chip active={!tag} onClick={() => setFilter("tag", "")}>
            All topics
          </Chip>
          {tags.map(([t, count]) => (
            <Chip key={t} active={tag === t} onClick={() => setFilter("tag", tag === t ? "" : t)}>
              {t} <span className="ml-0.5 text-muted">{count}</span>
            </Chip>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------ list */}
      <section className="mt-4">
        <div className="mb-2 flex items-center justify-between text-xs text-muted">
          <span>
            {filtered.length} of {problems.length} problems
          </span>
          {filtersActive && (
            <button type="button" onClick={() => setParams({}, { replace: true })} className="text-accent-strong hover:underline">
              Clear filters
            </button>
          )}
        </div>

        {filtered.length === 0 ? (
          <div className="rounded-2xl bg-panel px-6 py-14 text-center ring-1 ring-line">
            <p className="text-ink-soft">No problems match these filters.</p>
            <button type="button" onClick={() => setParams({}, { replace: true })} className="mt-2 text-sm text-accent-strong hover:underline">
              Clear filters
            </button>
          </div>
        ) : (
          <ul className="divide-y divide-line overflow-hidden rounded-2xl bg-panel ring-1 ring-line">
            {filtered.map((p) => (
              <li key={p.id}>
                <Link
                  to={`/problems/${p.slug}`}
                  className="group relative flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-hover sm:px-5"
                >
                  <span aria-hidden className="absolute inset-y-0 left-0 w-0.5 bg-accent opacity-0 transition-opacity group-hover:opacity-100" />
                  <StatusIcon p={p} />
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium text-ink group-hover:text-accent-strong">
                      <span className="mr-1.5 font-mono text-sm text-muted">{p.id}.</span>
                      {p.title}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {p.tags.map((t) => (
                        <span key={t} className="rounded bg-raised px-1.5 py-0.5 text-[11px] text-muted ring-1 ring-inset ring-line">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="hidden md:block">
                    <Acceptance rate={p.acceptance_rate} submissions={p.submissions} />
                  </div>
                  <span className={`w-16 shrink-0 rounded-full px-2 py-0.5 text-center text-xs font-medium ring-1 ring-inset ${DIFF_STYLE[p.difficulty].pill}`}>
                    {p.difficulty}
                  </span>
                  <span aria-hidden className="hidden text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-ink sm:inline">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-3 text-right text-[11px] text-muted">Acceptance = accepted submissions ÷ all submissions, across all users.</p>
      </section>
    </main>
  );
}
