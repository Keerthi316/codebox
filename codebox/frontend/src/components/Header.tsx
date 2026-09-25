import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `whitespace-nowrap rounded-md px-2 py-1.5 text-sm transition-colors sm:px-3 ${
    isActive ? "bg-hover text-ink" : "text-muted hover:text-ink"
  }`;

export function Header() {
  const { user, logout } = useAuth();
  return (
    <header className="flex h-12 shrink-0 items-center gap-1 border-b sm:gap-2 border-line bg-panel px-3 sm:px-4">
      <Link to="/" className="mr-1 flex shrink-0 sm:mr-2 items-center gap-2 font-semibold tracking-tight text-ink">
        <span className="grid size-7 place-items-center rounded-md bg-accent font-mono text-xs font-bold text-emerald-950">
          {"</>"}
        </span>
        <span className="hidden sm:inline">CodeBox</span>
      </Link>
      <nav className="flex items-center gap-1">
        <NavLink to="/problems" className={navClass}>
          Problems
        </NavLink>
        <NavLink to="/playground" className={navClass}>
          Playground
        </NavLink>
        <NavLink to="/submissions" className={navClass}>
          Submissions
        </NavLink>
      </nav>
      <div className="ml-auto flex items-center gap-2">
        {user && (
          <>
            <span className="hidden items-center gap-2 text-sm text-ink-soft sm:flex">
              <span className="grid size-7 place-items-center rounded-full bg-raised text-xs font-semibold uppercase text-ink ring-1 ring-line-strong">
                {user.username.slice(0, 2)}
              </span>
              {user.username}
            </span>
            <button
              onClick={logout}
              aria-label="Log out"
              title="Log out"
              className="whitespace-nowrap rounded-md px-2 py-1.5 text-sm text-muted hover:bg-hover hover:text-ink sm:px-3"
            >
              <span className="hidden sm:inline">Log out</span>
              <svg aria-hidden viewBox="0 0 24 24" className="size-4 sm:hidden" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
              </svg>
            </button>
          </>
        )}
      </div>
    </header>
  );
}
