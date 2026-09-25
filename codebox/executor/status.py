"""Execution statuses shared by the executor, worker and API (no Docker import)."""


class Status:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    FAILED = "FAILED"
    # Verdicts for judged submissions (kind="submit")
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"

    PENDING = (QUEUED, RUNNING)
