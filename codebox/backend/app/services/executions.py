"""API-side execution service: validates requests, persists jobs, enqueues them
and serialises results. It never runs code; the Celery worker does that."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from executor.languages import LANGUAGES, get_language
from executor.status import Status

from ..config import get_settings
from ..models import Execution, Problem, Submission, User
from ..schemas import ExecutionResult
from .rate_limit import enforce

log = logging.getLogger(__name__)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def validate_request(db: Session, user: User, language: str, source_code: str, stdin: str,
                     problem_id: int | None) -> Problem | None:
    settings = get_settings()
    if get_language(language) is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported language '{language}'. Supported: {', '.join(LANGUAGES)}")
    if not source_code.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Source code is empty")
    if len(source_code.encode("utf-8")) > settings.max_source_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            f"Source code exceeds {settings.max_source_bytes // 1024} KB")
    if len(stdin.encode("utf-8")) > settings.max_stdin_bytes:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE,
                            f"Input exceeds {settings.max_stdin_bytes // 1024} KB")
    problem = None
    if problem_id is not None:
        problem = db.get(Problem, problem_id)
        if problem is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")

    pending = db.scalar(
        select(func.count(Execution.id))
        .join(Submission)
        .where(Submission.user_id == user.id, Execution.status.in_(Status.PENDING))
    )
    if pending >= settings.max_pending_executions_per_user:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many executions in progress; wait for them to finish")
    return problem


def dispatch(execution_id: str) -> None:
    """Send the job to the Celery queue (kept separate so tests can stub it)."""
    from ..workers.celery_app import celery_app

    celery_app.send_task("codebox.run_execution", args=[execution_id])


def create_execution(db: Session, user: User, *, kind: str, language: str, source_code: str,
                     stdin: str = "", problem_id: int | None = None) -> Execution:
    language = language.lower()
    enforce(f"execute:{user.id}", get_settings().rate_limit_executions_per_minute)
    validate_request(db, user, language, source_code, stdin, problem_id)
    submission = Submission(user_id=user.id, problem_id=problem_id, kind=kind,
                            language=language, source_code=source_code, stdin=stdin,
                            status=Status.QUEUED)
    execution = Execution(submission=submission, status=Status.QUEUED)
    db.add_all([submission, execution])
    db.commit()

    try:
        dispatch(execution.id)
    except Exception:  # noqa: BLE001 - any broker failure means the job can't run
        log.exception("Failed to enqueue execution %s", execution.id)
        message = "Execution queue is unavailable; please try again shortly"
        execution.status = submission.status = Status.FAILED
        execution.error_message = message
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, message)
    return execution


def expire_if_stale(db: Session, execution: Execution) -> None:
    """Fail jobs that no worker picked up/finished (e.g. worker crashed)."""
    if execution.status not in Status.PENDING:
        return
    limit = timedelta(seconds=get_settings().stale_execution_seconds)
    if datetime.now(timezone.utc) - _as_utc(execution.created_at) > limit:
        execution.status = execution.submission.status = Status.FAILED
        execution.error_message = "Execution did not finish in time; the worker may be unavailable"
        execution.completed_at = datetime.now(timezone.utc)
        db.commit()


def get_owned_execution(db: Session, user: User, execution_id: str) -> Execution:
    execution = db.get(Execution, execution_id)
    # 404 (not 403) so other users' execution ids are not confirmed to exist
    if execution is None or execution.submission.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found")
    return execution


def to_result(execution: Execution) -> ExecutionResult:
    sub = execution.submission
    return ExecutionResult(
        execution_id=execution.id,
        submission_id=sub.id,
        kind=sub.kind,
        language=sub.language,
        status=sub.status,
        stdout=sub.stdout,
        stderr=sub.stderr,
        compile_output=sub.compile_output,
        execution_time=sub.execution_time,
        memory_used=sub.memory_used,
        passed_count=sub.passed_count,
        total_count=sub.total_count,
        test_results=sub.test_results,
        error_message=execution.error_message,
        created_at=execution.created_at,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )
