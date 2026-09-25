"""Celery tasks. This is the only component with Docker access; it drives the
sandbox containers but never runs user code in its own process."""

import logging
from datetime import datetime, timezone

from celery.signals import worker_ready

from executor.executor import DockerExecutor
from executor.status import Status

from ..database import SessionLocal
from ..models import Execution
from ..services.judge import judge
from .celery_app import celery_app

log = logging.getLogger(__name__)

MAX_STORED_OUTPUT = 64 * 1024
_executor: DockerExecutor | None = None


def get_executor() -> DockerExecutor:
    global _executor
    if _executor is None:
        _executor = DockerExecutor()
    return _executor


def _clip(text: str | None) -> str | None:
    if text is None or len(text) <= MAX_STORED_OUTPUT:
        return text
    return text[:MAX_STORED_OUTPUT] + "\n... (output truncated)"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def process_execution(execution_id: str, executor) -> None:
    db = SessionLocal()
    try:
        execution = db.get(Execution, execution_id)
        if execution is None:
            log.warning("Execution %s not found", execution_id)
            return
        if execution.status not in Status.PENDING:
            return  # already finished (duplicate delivery)
        submission = execution.submission
        execution.status = submission.status = Status.RUNNING
        execution.started_at = _now()
        db.commit()

        try:
            if submission.kind == "submit":
                tests = list(submission.problem.test_cases)
                outcome = executor.execute(submission.language, submission.source_code,
                                           [t.input for t in tests])
                verdict = judge(outcome, tests)
                submission.status = verdict.status
                submission.passed_count, submission.total_count = verdict.passed, verdict.total
                submission.test_results = verdict.results
                submission.execution_time = verdict.time_ms
                submission.memory_used = verdict.memory_kb
                submission.stderr = verdict.stderr
            else:
                outcome = executor.execute(submission.language, submission.source_code,
                                           [submission.stdin or ""])
                submission.status = outcome.status
                if outcome.runs:
                    run = outcome.runs[0]
                    submission.stdout = _clip(run.stdout)
                    submission.stderr = _clip(run.stderr)
                    submission.execution_time = run.time_ms
                    submission.memory_used = run.memory_kb
                    execution.error_message = run.message
            submission.compile_output = _clip(outcome.compile_output) or None
            if outcome.message and not execution.error_message:
                execution.error_message = outcome.message
            execution.status = (Status.FAILED if outcome.status == Status.FAILED
                                else Status.COMPLETED)
        except Exception:  # noqa: BLE001 - never leave a job stuck in RUNNING
            log.exception("Execution %s crashed", execution_id)
            db.rollback()
            submission.status = execution.status = Status.FAILED
            execution.error_message = "Internal error while executing the code"
        execution.completed_at = _now()
        db.commit()
    finally:
        db.close()


@celery_app.task(name="codebox.run_execution")
def run_execution(execution_id: str) -> None:
    process_execution(execution_id, get_executor())


@worker_ready.connect
def _cleanup_on_start(**_kwargs) -> None:
    removed = get_executor().cleanup_stale_containers()
    if removed:
        log.warning("Removed %d stale sandbox container(s)", removed)
