import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { Language, ProblemDetail, SubmissionSummary } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { useExecution } from "../hooks/useExecution";
import { useMediaQuery } from "../hooks/useMediaQuery";
import { formatMemory, formatTime, LANGUAGE_LABEL, storageGet, storageSet, timeAgo } from "../lib/format";
import { PLAYGROUND_TEMPLATES } from "../lib/templates";
import { AIAssistant } from "./AIAssistant";
import { CodeEditor } from "./CodeEditor";
import { Markdown } from "./Markdown";
import { ResultPanel } from "./ResultPanel";
import { SplitPane } from "./SplitPane";
import { Button, Difficulty, StatusPill, Tabs } from "./ui";

const FALLBACK_LANGUAGES: Language[] = ["python", "javascript", "java", "cpp"].map((key) => ({
  key,
  name: LANGUAGE_LABEL[key],
  monaco: key,
  time_limit_seconds: 2,
}));

type LeftTab = "description" | "submissions" | "ai" | "about";
type ConsoleTab = "input" | "result";

export function Workspace({ problem }: { problem?: ProblemDetail }) {
  const { user } = useAuth();
  const location = useLocation();
  const wide = useMediaQuery("(min-width: 1024px)");
  const scope = problem ? `problem.${problem.slug}` : "playground";

  const [languages, setLanguages] = useState<Language[]>(FALLBACK_LANGUAGES);
  const [limits, setLimits] = useState<{ memory: string; cpus: number } | null>(null);
  const [language, setLanguage] = useState(() => storageGet("codebox.language") ?? "python");
  const starter = useCallback(
    (lang: string) => (problem ? problem.starter_code[lang] : PLAYGROUND_TEMPLATES[lang]) ?? "",
    [problem],
  );
  const [code, setCode] = useState(() => storageGet(`codebox.draft.${scope}.${language}`) ?? starter(language));
  const [stdin, setStdin] = useState(() => problem?.examples[0]?.input ?? "CodeBox");
  const [leftTab, setLeftTab] = useState<LeftTab>(problem ? "description" : "ai");
  const [consoleTab, setConsoleTab] = useState<ConsoleTab>("input");
  const [history, setHistory] = useState<SubmissionSummary[] | null>(null);
  const { result, busy, error, start } = useExecution();

  useEffect(() => {
    api
      .languages()
      .then((res) => {
        setLanguages(res.languages);
        setLimits(res.limits);
      })
      .catch(() => {});
  }, []);

  const loadHistory = useCallback(() => {
    if (!problem || !user) return;
    api
      .submissions({ problem_id: problem.id, kind: "submit", page_size: 50 })
      .then((res) => setHistory(res.items))
      .catch(() => setHistory([]));
  }, [problem, user]);

  useEffect(loadHistory, [loadHistory]);
  useEffect(() => {
    if (result?.kind === "submit" && !busy) loadHistory();
  }, [result, busy, loadHistory]);

  function changeLanguage(next: string) {
    storageSet(`codebox.draft.${scope}.${language}`, code);
    setLanguage(next);
    storageSet("codebox.language", next);
    setCode(storageGet(`codebox.draft.${scope}.${next}`) ?? starter(next));
  }

  function updateCode(next: string) {
    setCode(next);
    storageSet(`codebox.draft.${scope}.${language}`, next);
  }

  function reset() {
    if (window.confirm("Reset the editor to the starter code? Your changes for this language will be lost.")) {
      updateCode(starter(language));
    }
  }

  const run = useCallback(() => {
    if (!user || busy) return;
    setConsoleTab("result");
    start("run", () => api.execute(language, code, stdin, problem?.id));
  }, [user, busy, start, language, code, stdin, problem]);

  const submit = useCallback(() => {
    if (!user || busy || !problem) return;
    setConsoleTab("result");
    start("submit", () => api.submit(problem.id, language, code));
  }, [user, busy, start, problem, language, code]);

  const timeLimit = languages.find((l) => l.key === language)?.time_limit_seconds;

  // ------------------------------------------------------------------ panes
  const leftTabs = useMemo(
    () =>
      problem
        ? [
            { id: "description" as const, label: "Description" },
            { id: "submissions" as const, label: "Submissions" },
            { id: "ai" as const, label: <>✦ AI Assistant</> },
          ]
        : [
            { id: "ai" as const, label: <>✦ AI Assistant</> },
            { id: "about" as const, label: "Sandbox" },
          ],
    [problem],
  );

  const leftPane = (
    <div className="flex h-full min-h-0 flex-col bg-panel">
      <Tabs tabs={leftTabs} active={leftTab} onChange={setLeftTab} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        {leftTab === "description" && problem && <ProblemStatement problem={problem} />}
        {leftTab === "submissions" && problem && (
          <ProblemSubmissions items={history} loggedIn={Boolean(user)} />
        )}
        {leftTab === "about" && <SandboxInfo limits={limits} languages={languages} />}
        {leftTab === "ai" && (
          <AIAssistant language={language} code={code} lastResult={result} stdin={stdin} problemId={problem?.id} />
        )}
      </div>
    </div>
  );

  const toolbar = (
    <div className="flex h-10 shrink-0 items-center gap-2 border-b border-line bg-panel px-2">
      <label className="sr-only" htmlFor="language">
        Language
      </label>
      <select
        id="language"
        value={language}
        onChange={(e) => changeLanguage(e.target.value)}
        className="min-w-0 rounded-md bg-raised px-2 py-1 text-sm text-ink ring-1 ring-inset ring-line-strong focus:outline-none focus:ring-accent"
      >
        {languages.map((l) => (
          <option key={l.key} value={l.key}>
            {l.name}
          </option>
        ))}
      </select>
      {timeLimit && <span className="hidden text-xs text-muted md:inline">Time limit {timeLimit}s</span>}
      <button onClick={reset} className="whitespace-nowrap rounded-md px-2 py-1 text-xs text-muted hover:bg-hover hover:text-ink" title="Reset code">
        ↺ Reset
      </button>
      <div className="ml-auto flex items-center gap-2">
        {user ? (
          <>
            <Button onClick={run} loading={busy === "run"} disabled={Boolean(busy)} title="Run (Ctrl+Enter)">
              ▶ Run
            </Button>
            {problem && (
              <Button variant="primary" onClick={submit} loading={busy === "submit"} disabled={Boolean(busy)}>
                Submit
              </Button>
            )}
          </>
        ) : (
          <Link
            to="/login"
            state={{ from: location.pathname }}
            className="whitespace-nowrap rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-emerald-950 hover:bg-accent-strong"
          >
            Log in to run
          </Link>
        )}
      </div>
    </div>
  );

  const consolePane = (
    <div className="flex h-full min-h-0 flex-col bg-panel">
      <Tabs
        tabs={[
          { id: "input", label: "Custom input" },
          {
            id: "result",
            label: (
              <>
                Result {result && !busy && <StatusDot ok={result.status === "ACCEPTED" || result.status === "COMPLETED"} />}
              </>
            ),
          },
        ]}
        active={consoleTab}
        onChange={setConsoleTab}
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        {consoleTab === "input" ? (
          <div className="flex h-full flex-col gap-2 p-3">
            <textarea
              value={stdin}
              onChange={(e) => setStdin(e.target.value)}
              spellCheck={false}
              placeholder="Program input (stdin)"
              aria-label="Custom input"
              className="min-h-24 flex-1 resize-none rounded-lg bg-canvas p-3 font-mono text-[13px] text-ink ring-1 ring-inset ring-line focus:outline-none focus:ring-accent"
            />
            <p className="text-xs text-muted">
              Used by <span className="text-ink-soft">Run</span>.{" "}
              {problem && "Submit judges your code against all test cases, including hidden ones."}
            </p>
          </div>
        ) : (
          <ResultPanel result={result} busy={busy} error={error} />
        )}
      </div>
    </div>
  );

  const editorPane = (
    <div className="flex h-full min-h-0 flex-col">
      {toolbar}
      <div className="min-h-0 flex-1">
        <CodeEditor language={language} value={code} onChange={updateCode} onRun={run} />
      </div>
    </div>
  );

  if (!wide) {
    return (
      <div className="flex flex-col">
        <div className="max-h-[60vh] overflow-hidden border-b border-line">{leftPane}</div>
        <div className="h-[60vh]">{editorPane}</div>
        <div className="h-[50vh] border-t border-line">{consolePane}</div>
      </div>
    );
  }

  return (
    <SplitPane
      direction="horizontal"
      initial={42}
      min={25}
      storageKey="codebox.split.main"
      className="min-h-0 flex-1"
      first={leftPane}
      second={
        <SplitPane
          direction="vertical"
          initial={62}
          min={20}
          storageKey="codebox.split.editor"
          className="h-full"
          first={editorPane}
          second={consolePane}
        />
      }
    />
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return <span className={`size-1.5 rounded-full ${ok ? "bg-accent" : "bg-danger"}`} />;
}

function ProblemStatement({ problem }: { problem: ProblemDetail }) {
  return (
    <article className="p-5">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-xl font-semibold text-ink">
          {problem.id}. {problem.title}
        </h1>
        {problem.solved && (
          <span className="shrink-0 rounded-full bg-accent/10 px-2 py-0.5 text-xs text-accent-strong ring-1 ring-inset ring-accent/25">
            ✓ Solved
          </span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <Difficulty level={problem.difficulty} />
        <span className="text-xs text-muted">{problem.test_case_count} test cases</span>
        {problem.acceptance_rate !== null && (
          <span className="text-xs text-muted">{Math.round(problem.acceptance_rate * 100)}% acceptance</span>
        )}
        <span className="flex flex-wrap gap-1.5">
          {problem.tags.map((t) => (
            <Link
              key={t}
              to={`/problems?tag=${encodeURIComponent(t)}`}
              className="rounded bg-raised px-1.5 py-0.5 text-[11px] text-muted ring-1 ring-inset ring-line hover:text-ink"
            >
              {t}
            </Link>
          ))}
        </span>
      </div>
      <div className="mt-4">
        <Markdown>{problem.description}</Markdown>
      </div>
      {problem.examples.map((ex, i) => (
        <div key={i} className="mt-5">
          <h3 className="mb-2 text-sm font-semibold text-ink">Example {i + 1}</h3>
          <div className="space-y-2 rounded-lg border-l-2 border-line-strong bg-raised/50 p-3 font-mono text-[13px]">
            <div>
              <span className="text-muted">Input:</span>
              <pre className="mt-1 whitespace-pre-wrap text-ink-soft">{ex.input}</pre>
            </div>
            <div>
              <span className="text-muted">Output:</span>
              <pre className="mt-1 whitespace-pre-wrap text-ink-soft">{ex.output}</pre>
            </div>
            {ex.explanation && (
              <div className="font-sans text-sm">
                <span className="text-muted">Explanation: </span>
                <span className="text-ink-soft">{ex.explanation}</span>
              </div>
            )}
          </div>
        </div>
      ))}
      <h3 className="mb-2 mt-6 text-sm font-semibold text-ink">Constraints</h3>
      <Markdown>{problem.constraints}</Markdown>
    </article>
  );
}

function ProblemSubmissions({ items, loggedIn }: { items: SubmissionSummary[] | null; loggedIn: boolean }) {
  if (!loggedIn) return <p className="p-5 text-sm text-muted">Log in to see your submissions.</p>;
  if (items === null) return <p className="p-5 text-sm text-muted">Loading…</p>;
  if (items.length === 0) return <p className="p-5 text-sm text-muted">No submissions yet. Submit your solution to see it here.</p>;
  return (
    <ul className="divide-y divide-line">
      {items.map((s) => (
        <li key={s.id}>
          <Link to={`/submissions/${s.id}`} className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-hover">
            <StatusPill status={s.status} />
            <span className="text-ink-soft">{LANGUAGE_LABEL[s.language] ?? s.language}</span>
            {s.total_count != null && (
              <span className="font-mono text-xs text-muted">
                {s.passed_count}/{s.total_count}
              </span>
            )}
            <span className="ml-auto hidden font-mono text-xs text-muted sm:inline">{formatTime(s.execution_time)}</span>
            <span className="hidden font-mono text-xs text-muted sm:inline">{formatMemory(s.memory_used)}</span>
            <span className="w-20 text-right text-xs text-muted">{timeAgo(s.created_at)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function SandboxInfo({ limits, languages }: { limits: { memory: string; cpus: number } | null; languages: Language[] }) {
  return (
    <div className="space-y-4 p-5 text-sm text-ink-soft">
      <h2 className="text-base font-semibold text-ink">Playground</h2>
      <p>
        Write any program, give it input and run it. Every run happens in a fresh, throw-away Docker container that is
        destroyed afterwards.
      </p>
      <ul className="space-y-1.5">
        <li>• No network access, read-only filesystem, unprivileged user</li>
        <li>
          • Memory limit <span className="font-mono text-ink">{limits?.memory ?? "—"}</span>, CPU limit{" "}
          <span className="font-mono text-ink">{limits?.cpus ?? "—"}</span> cores
        </li>
        <li>• Process-count and output-size limits</li>
      </ul>
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-muted">
          <tr>
            <th className="py-1 font-medium">Language</th>
            <th className="py-1 font-medium">Time limit</th>
          </tr>
        </thead>
        <tbody>
          {languages.map((l) => (
            <tr key={l.key} className="border-t border-line">
              <td className="py-1.5">{l.name}</td>
              <td className="py-1.5 font-mono">{l.time_limit_seconds}s</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
