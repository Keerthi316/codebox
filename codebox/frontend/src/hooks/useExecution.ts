import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../api/client";
import type { ExecutionAccepted, ExecutionResult } from "../api/types";
import { isPending } from "../lib/format";

const POLL_MS = 600;
const MAX_WAIT_MS = 180_000;

/** Starts an execution and polls GET /executions/{id} until it finishes. */
export function useExecution() {
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [busy, setBusy] = useState<null | "run" | "submit">(null);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);

  useEffect(() => () => void generation.current++, []); // stop polling on unmount

  const start = useCallback(async (kind: "run" | "submit", begin: () => Promise<ExecutionAccepted>) => {
    const id = ++generation.current;
    setBusy(kind);
    setError(null);
    setResult(null);
    try {
      const accepted = await begin();
      const deadline = Date.now() + MAX_WAIT_MS;
      while (generation.current === id) {
        const current = await api.execution(accepted.execution_id);
        if (generation.current !== id) return;
        setResult(current);
        if (!isPending(current.status)) return;
        if (Date.now() > deadline) throw new ApiError(0, "Timed out waiting for the result");
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    } catch (e) {
      if (generation.current === id) setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      if (generation.current === id) setBusy(null);
    }
  }, []);

  return { result, busy, error, start };
}
