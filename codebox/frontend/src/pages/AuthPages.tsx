import { useId, useState, type FormEvent, type InputHTMLAttributes, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { safeRedirect } from "../lib/redirect";
import { Button, ErrorBanner } from "../components/ui";

// ----------------------------------------------------------------- icons

const Icon = {
  user: "M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z",
  mail: "M4 5h16a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1Zm0 1 8 7 8-7",
  lock: "M6 10h12a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Zm2 0V7a4 4 0 1 1 8 0v3",
  eye: "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z",
  eyeOff: "M3 3l18 18M10.6 5.1A10.7 10.7 0 0 1 12 5c6.5 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2M6.6 6.6C3.7 8.5 2 12 2 12s3.5 7 10 7c1.8 0 3.4-.5 4.8-1.3M9.9 9.9a3 3 0 0 0 4.2 4.2",
  shield: "M12 3 4 6v6c0 5 3.4 8.6 8 9 4.6-.4 8-4 8-9V6l-8-3Zm-3 9 2 2 4-4",
  bolt: "M13 2 4 14h7l-1 8 9-12h-7l1-8Z",
  sparkle: "M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6",
  code: "m8 8-4 4 4 4M16 8l4 4-4 4M14 4l-4 16",
};

function Svg({ d, className = "size-4" }: { d: string; className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}

// ----------------------------------------------------------------- layout

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="grid size-9 place-items-center rounded-lg bg-accent font-mono text-sm font-bold text-emerald-950 shadow-lg shadow-accent/20">
        {"</>"}
      </span>
      <span className="text-lg font-semibold tracking-tight text-ink">CodeBox</span>
    </div>
  );
}

const FEATURES = [
  { icon: Icon.code, title: "Four languages", text: "Python, JavaScript, Java and C++ in a real Monaco editor." },
  { icon: Icon.shield, title: "Sandboxed execution", text: "Every run happens in a fresh, locked-down Docker container." },
  { icon: Icon.bolt, title: "Instant judging", text: "Submit against hidden test cases and see runtime and memory." },
  { icon: Icon.sparkle, title: "AI assistant", text: "Explain, debug, analyse complexity and optimise your code." },
];

function ShowcasePanel() {
  return (
    <aside className="relative hidden overflow-hidden border-r border-line bg-panel lg:flex lg:w-[52%] lg:flex-col lg:justify-between lg:p-12 xl:p-16">
      {/* soft grid + glow background */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.35]"
        style={{
          backgroundImage:
            "linear-gradient(var(--color-line) 1px, transparent 1px), linear-gradient(90deg, var(--color-line) 1px, transparent 1px)",
          backgroundSize: "44px 44px",
          maskImage: "radial-gradient(ellipse at 30% 40%, black 20%, transparent 75%)",
        }}
      />
      <div aria-hidden className="pointer-events-none absolute -left-32 -top-32 size-[28rem] rounded-full bg-accent/15 blur-3xl" />
      <div aria-hidden className="pointer-events-none absolute -bottom-40 right-0 size-[24rem] rounded-full bg-info/10 blur-3xl" />

      <div className="relative">
        <Logo />
      </div>

      <div className="relative max-w-lg">
        <h2 className="text-4xl font-semibold leading-tight tracking-tight text-ink xl:text-5xl">
          Write code.
          <br />
          <span className="text-accent-strong">Run it safely.</span>
        </h2>
        <p className="mt-4 text-base leading-relaxed text-ink-soft">
          Solve coding problems, get judged against hidden tests in seconds, and learn faster with an AI pair programmer.
        </p>

        {/* verdict card */}
        <div className="mt-8 overflow-hidden rounded-xl bg-canvas/80 shadow-2xl shadow-black/40 ring-1 ring-line-strong backdrop-blur">
          <div className="flex items-center gap-1.5 border-b border-line px-4 py-2.5">
            <span className="size-2.5 rounded-full bg-danger/70" />
            <span className="size-2.5 rounded-full bg-warn/70" />
            <span className="size-2.5 rounded-full bg-accent/70" />
            <span className="ml-3 font-mono text-xs text-muted">two_sum.py — submit</span>
          </div>
          <div className="space-y-1.5 px-4 py-4 font-mono text-[13px]">
            {["sample", "hidden", "hidden", "hidden", "hidden", "hidden"].map((kind, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="text-accent-strong">✓</span>
                <span className="text-ink-soft">Test Case {i + 1}</span>
                <span className="text-muted">{kind}</span>
                <span className="ml-auto text-muted">{[23, 77, 15, 13, 84, 41][i]} ms</span>
              </div>
            ))}
            <div className="mt-3 flex items-center gap-3 border-t border-line pt-3">
              <span className="font-sans text-base font-semibold text-accent-strong">Accepted</span>
              <span className="text-ink-soft">6/6 passed</span>
              <span className="ml-auto text-muted">84 ms · 10.6 MB</span>
            </div>
          </div>
        </div>
      </div>

      <ul className="relative grid max-w-xl grid-cols-2 gap-x-8 gap-y-5">
        {FEATURES.map((f) => (
          <li key={f.title} className="flex gap-3">
            <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-accent/10 text-accent-strong ring-1 ring-inset ring-accent/20">
              <Svg d={f.icon} />
            </span>
            <div>
              <div className="text-sm font-medium text-ink">{f.title}</div>
              <div className="mt-0.5 text-xs leading-relaxed text-muted">{f.text}</div>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="flex min-h-full bg-canvas">
      <ShowcasePanel />
      <main className="flex flex-1 flex-col px-5 py-10 sm:px-8">
        <div className="lg:hidden">
          <Logo />
        </div>
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
          <p className="mt-1.5 text-sm text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-8 text-center text-sm text-muted">{footer}</div>
        </div>
        <p className="text-center text-xs text-muted/80">Code runs in isolated containers with no network access.</p>
      </main>
    </div>
  );
}

// ----------------------------------------------------------------- fields

function Field({
  label,
  icon,
  hint,
  error,
  trailing,
  ...props
}: {
  label: string;
  icon: string;
  hint?: ReactNode;
  error?: string | null;
  trailing?: ReactNode;
} & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink-soft">
        {label}
      </label>
      <div
        className={`flex items-center rounded-lg bg-panel ring-1 ring-inset transition focus-within:ring-2 ${
          error ? "ring-danger/60 focus-within:ring-danger" : "ring-line-strong focus-within:ring-accent"
        }`}
      >
        <span className="pl-3 text-muted">
          <Svg d={icon} />
        </span>
        <input
          id={id}
          {...props}
          aria-invalid={Boolean(error)}
          aria-describedby={hint || error ? `${id}-hint` : undefined}
          className="w-full min-w-0 bg-transparent px-3 py-2.5 text-sm text-ink placeholder:text-muted/70 focus:outline-none"
        />
        {trailing}
      </div>
      {(error || hint) && (
        <p id={`${id}-hint`} className={`mt-1.5 text-xs ${error ? "text-danger" : "text-muted"}`}>
          {error || hint}
        </p>
      )}
    </div>
  );
}

function PasswordField(props: Omit<Parameters<typeof Field>[0], "icon" | "type" | "trailing">) {
  const [visible, setVisible] = useState(false);
  return (
    <Field
      {...props}
      icon={Icon.lock}
      type={visible ? "text" : "password"}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          title={visible ? "Hide password" : "Show password"}
          className="mr-1.5 rounded-md p-1.5 text-muted hover:bg-hover hover:text-ink"
        >
          <Svg d={visible ? Icon.eyeOff : Icon.eye} />
        </button>
      }
    />
  );
}

function passwordStrength(pw: string): { score: number; label: string } {
  if (!pw) return { score: 0, label: "" };
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
  if (/\d/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const clamped = Math.min(4, Math.max(1, score - (pw.length < 8 ? 1 : 0)));
  return { score: clamped, label: ["", "Weak", "Fair", "Good", "Strong"][clamped] };
}

function StrengthMeter({ password }: { password: string }) {
  const { score, label } = passwordStrength(password);
  if (!password) return null;
  const colors = ["", "bg-danger", "bg-warn", "bg-info", "bg-accent"];
  return (
    <div className="mt-2 flex items-center gap-3" aria-live="polite">
      <div className="flex flex-1 gap-1">
        {[1, 2, 3, 4].map((i) => (
          <span key={i} className={`h-1 flex-1 rounded-full ${i <= score ? colors[score] : "bg-line"}`} />
        ))}
      </div>
      <span className="w-12 text-right text-xs text-muted">{label}</span>
    </div>
  );
}

function useRedirectTarget() {
  const location = useLocation();
  return safeRedirect((location.state as { from?: unknown } | null)?.from);
}

// ----------------------------------------------------------------- pages

export function LoginPage() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const target = useRedirectTarget();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate(target, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to continue to CodeBox."
      footer={
        <>
          New to CodeBox?{" "}
          <Link to="/register" state={{ from: target }} className="font-medium text-accent-strong hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5" noValidate={false}>
        {sessionExpired && !error && (
          <div className="rounded-lg bg-warn/10 px-3 py-2 text-sm text-warn ring-1 ring-inset ring-warn/25" role="status">
            Your session has expired. Please sign in again.
          </div>
        )}
        {error && <ErrorBanner>{error}</ErrorBanner>}
        <Field
          label="Username or email"
          icon={Icon.user}
          autoComplete="username"
          autoFocus
          required
          placeholder="you@example.com"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <PasswordField
          label="Password"
          autoComplete="current-password"
          required
          placeholder="Your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <Button type="submit" variant="primary" loading={loading} className="w-full py-2.5 text-[15px]">
          Sign in
        </Button>
      </form>
    </AuthLayout>
  );
}

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const target = useRedirectTarget();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const usernameError =
    username && !/^[A-Za-z0-9_.-]{3,32}$/.test(username)
      ? "3–32 characters: letters, digits, dot, dash or underscore"
      : null;
  const passwordError = password && password.length < 8 ? "Use at least 8 characters" : null;
  const confirmError = confirm && confirm !== password ? "Passwords don't match" : null;
  const canSubmit = username && email && password && confirm && !usernameError && !passwordError && !confirmError;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      await register(username.trim(), email.trim(), password);
      navigate(target, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="Start solving problems in under a minute."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" state={{ from: target }} className="font-medium text-accent-strong hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-5">
        {error && <ErrorBanner>{error}</ErrorBanner>}
        <Field
          label="Username"
          icon={Icon.user}
          autoComplete="username"
          autoFocus
          required
          maxLength={32}
          placeholder="ada_lovelace"
          value={username}
          error={usernameError}
          onChange={(e) => setUsername(e.target.value)}
        />
        <Field
          label="Email"
          icon={Icon.mail}
          type="email"
          autoComplete="email"
          required
          placeholder="you@example.com"
          hint="Use a real address, e.g. your Gmail. We check that it can receive mail."
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <div>
          <PasswordField
            label="Password"
            autoComplete="new-password"
            required
            maxLength={72}
            placeholder="At least 8 characters"
            value={password}
            error={passwordError}
            onChange={(e) => setPassword(e.target.value)}
          />
          <StrengthMeter password={password} />
        </div>
        <PasswordField
          label="Confirm password"
          autoComplete="new-password"
          required
          maxLength={72}
          placeholder="Repeat your password"
          value={confirm}
          error={confirmError}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <Button type="submit" variant="primary" loading={loading} disabled={!canSubmit} className="w-full py-2.5 text-[15px]">
          Create account
        </Button>
      </form>
    </AuthLayout>
  );
}
