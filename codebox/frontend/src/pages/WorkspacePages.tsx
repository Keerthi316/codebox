import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ProblemDetail } from "../api/types";
import { ErrorBanner, PageShell, Spinner } from "../components/ui";
import { Workspace } from "../components/Workspace";

export function ProblemPage() {
  const { slug = "" } = useParams();
  const [problem, setProblem] = useState<ProblemDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setProblem(null);
    setError(null);
    api
      .problem(slug)
      .then(setProblem)
      .catch((e) => setError(e.message));
  }, [slug]);

  if (error)
    return (
      <PageShell>
        <ErrorBanner>{error}</ErrorBanner>
      </PageShell>
    );
  if (!problem)
    return (
      <div className="grid flex-1 place-items-center text-muted">
        <Spinner className="size-5" />
      </div>
    );
  return <Workspace key={problem.slug} problem={problem} />;
}

export function PlaygroundPage() {
  return <Workspace />;
}
