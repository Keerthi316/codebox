import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { Status } from "../api/types";
import { STATUS_LABEL, statusTone, type Tone } from "../lib/format";

const TONE_TEXT: Record<Tone, string> = {
  ok: "text-accent-strong",
  bad: "text-danger",
  warn: "text-warn",
  busy: "text-info",
  muted: "text-muted",
};

const TONE_PILL: Record<Tone, string> = {
  ok: "bg-accent/10 text-accent-strong ring-accent/25",
  bad: "bg-danger/10 text-danger ring-danger/25",
  warn: "bg-warn/10 text-warn ring-warn/25",
  busy: "bg-info/10 text-info ring-info/25",
  muted: "bg-hover text-muted ring-line-strong",
};

export function StatusText({ status, className = "" }: { status: Status; className?: string }) {
  return <span className={`${TONE_TEXT[statusTone(status)]} ${className}`}>{STATUS_LABEL[status] ?? status}</span>;
}

export function StatusPill({ status }: { status: Status }) {
  const tone = statusTone(status);
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${TONE_PILL[tone]}`}>
      {tone === "busy" && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}

const DIFFICULTY: Record<string, string> = {
  Easy: "text-accent-strong",
  Medium: "text-warn",
  Hard: "text-danger",
};

export function Difficulty({ level }: { level: string }) {
  return <span className={`text-xs font-medium ${DIFFICULTY[level] ?? "text-muted"}`}>{level}</span>;
}

type Variant = "primary" | "secondary" | "ghost";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-emerald-950 hover:bg-accent-strong font-semibold",
  secondary: "bg-raised text-ink ring-1 ring-inset ring-line-strong hover:bg-hover",
  ghost: "text-ink-soft hover:bg-hover hover:text-ink",
};

export function Button({
  variant = "secondary",
  className = "",
  loading = false,
  children,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANTS[variant]} ${className}`}
    >
      {loading && <Spinner />}
      {children}
    </button>
  );
}

export function Spinner({ className = "size-3.5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
  right,
}: {
  tabs: { id: T; label: ReactNode }[];
  active: T;
  onChange: (id: T) => void;
  right?: ReactNode;
}) {
  return (
    <div className="flex h-10 shrink-0 items-center gap-1 border-b border-line bg-panel px-2" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={active === tab.id}
          onClick={() => onChange(tab.id)}
          className={`relative flex h-full items-center gap-1.5 px-3 text-sm transition-colors ${
            active === tab.id ? "text-ink" : "text-muted hover:text-ink-soft"
          }`}
        >
          {tab.label}
          {active === tab.id && <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-accent" />}
        </button>
      ))}
      <div className="ml-auto flex items-center gap-2">{right}</div>
    </div>
  );
}

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg bg-raised px-3 py-2 ring-1 ring-inset ring-line">
      <div className="text-[11px] uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 font-mono text-sm text-ink">{value}</div>
    </div>
  );
}

export function CodeBlock({ label, children, tone }: { label: string; children: ReactNode; tone?: "bad" }) {
  return (
    <div>
      <div className="mb-1 text-xs font-medium text-muted">{label}</div>
      <pre
        className={`max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-canvas p-3 font-mono text-[13px] leading-relaxed ring-1 ring-inset ${
          tone === "bad" ? "text-danger ring-danger/25" : "text-ink-soft ring-line"
        }`}
      >
        {children}
      </pre>
    </div>
  );
}

export function ErrorBanner({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger ring-1 ring-inset ring-danger/25" role="alert">
      {children}
    </div>
  );
}

export function PageShell({ children }: { children: ReactNode }) {
  return <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>;
}
