import { BrowserRouter, Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Header } from "./components/Header";
import { PageShell, Spinner } from "./components/ui";
import { safeRedirect } from "./lib/redirect";
import { LoginPage, RegisterPage } from "./pages/AuthPages";
import { ProblemsPage } from "./pages/ProblemsPage";
import { SubmissionDetailPage } from "./pages/SubmissionDetailPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { PlaygroundPage, ProblemPage } from "./pages/WorkspacePages";

function FullScreenSpinner() {
  return (
    <div className="grid min-h-full place-items-center text-muted">
      <Spinner className="size-6" />
    </div>
  );
}

/** Everything in the app requires a signed-in user; others are sent to /login. */
function ProtectedLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenSpinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return (
    <div className="flex min-h-full flex-col lg:h-full">
      <Header />
      <Outlet />
    </div>
  );
}

/** Login/register: full-screen, and skipped entirely when already signed in. */
function GuestLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenSpinner />;
  if (user) {
    return <Navigate to={safeRedirect((location.state as { from?: unknown } | null)?.from)} replace />;
  }
  return <Outlet />;
}

function NotFound() {
  return (
    <PageShell>
      <div className="py-20 text-center">
        <p className="font-mono text-5xl text-line-strong">404</p>
        <p className="mt-3 text-muted">This page does not exist.</p>
        <Link to="/problems" className="mt-4 inline-block text-accent-strong hover:underline">
          Back to problems
        </Link>
      </div>
    </PageShell>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<GuestLayout />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Navigate to="/problems" replace />} />
            {/* removed page; keep old links and bookmarks working */}
            <Route path="/verify-email" element={<Navigate to="/problems" replace />} />
            <Route path="/problems" element={<ProblemsPage />} />
            <Route path="/problems/:slug" element={<ProblemPage />} />
            <Route path="/playground" element={<PlaygroundPage />} />
            <Route path="/submissions" element={<SubmissionsPage />} />
            <Route path="/submissions/:id" element={<SubmissionDetailPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
