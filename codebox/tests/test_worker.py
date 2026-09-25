"""Worker task logic with a fake executor (no Docker needed)."""

from sqlalchemy import select

from app.models import Execution, Problem, Submission, User
from app.workers.tasks import process_execution
from executor.executor import ExecutionOutcome, RunResult
from executor.status import Status


class FakeExecutor:
    def __init__(self, outcome=None, error=None):
        self.outcome, self.error, self.calls = outcome, error, []

    def execute(self, language, source, inputs):
        self.calls.append((language, source, inputs))
        if self.error:
            raise self.error
        return self.outcome


def _job(db, kind="run", problem_slug=None, stdin="5"):
    user = User(username="w", email="w@example.com", password_hash="x")
    db.add(user)
    db.flush()
    problem = db.scalar(select(Problem).where(Problem.slug == problem_slug)) if problem_slug else None
    submission = Submission(user_id=user.id, kind=kind, language="python", source_code="code",
                            stdin=stdin, problem_id=problem.id if problem else None)
    execution = Execution(submission=submission)
    db.add_all([submission, execution])
    db.commit()
    return execution.id


def _reload(db, execution_id):
    db.expire_all()
    return db.get(Execution, execution_id)


def test_custom_run_success(db):
    eid = _job(db)
    fake = FakeExecutor(ExecutionOutcome(Status.COMPLETED, runs=[
        RunResult(Status.COMPLETED, stdout="25\n", time_ms=12, memory_kb=8000)]))
    process_execution(eid, fake)
    assert fake.calls == [("python", "code", ["5"])]
    execution = _reload(db, eid)
    sub = execution.submission
    assert execution.status == Status.COMPLETED and sub.status == Status.COMPLETED
    assert (sub.stdout, sub.execution_time, sub.memory_used) == ("25\n", 12, 8000)
    assert execution.started_at and execution.completed_at


def test_custom_run_runtime_error_and_huge_output(db):
    eid = _job(db)
    fake = FakeExecutor(ExecutionOutcome(Status.RUNTIME_ERROR, runs=[
        RunResult(Status.RUNTIME_ERROR, stdout="x" * 200_000, stderr="ZeroDivisionError",
                  exit_code=1, message="Program exited with code 1")]))
    process_execution(eid, fake)
    execution = _reload(db, eid)
    assert execution.status == Status.COMPLETED  # job finished; the program failed
    assert execution.submission.status == Status.RUNTIME_ERROR
    assert execution.error_message == "Program exited with code 1"
    assert len(execution.submission.stdout) < 70_000  # stored output is capped


def test_compilation_error_is_stored(db):
    eid = _job(db)
    process_execution(eid, FakeExecutor(ExecutionOutcome(
        Status.COMPILATION_ERROR, compile_output="main.cpp:1: error", message="Compilation failed")))
    execution = _reload(db, eid)
    assert execution.submission.status == Status.COMPILATION_ERROR
    assert execution.submission.compile_output == "main.cpp:1: error"


def test_submit_is_judged_against_all_test_cases(db):
    eid = _job(db, kind="submit", problem_slug="reverse-string", stdin="")
    problem = db.scalar(select(Problem).where(Problem.slug == "reverse-string"))
    runs = [RunResult(Status.COMPLETED, stdout=t.expected_output, time_ms=3) for t in problem.test_cases]
    runs[-1] = RunResult(Status.COMPLETED, stdout="wrong\n")
    fake = FakeExecutor(ExecutionOutcome(Status.COMPLETED, runs=runs))
    process_execution(eid, fake)

    assert fake.calls[0][2] == [t.input for t in problem.test_cases]
    sub = _reload(db, eid).submission
    total = len(problem.test_cases)
    assert (sub.status, sub.passed_count, sub.total_count) == (Status.WRONG_ANSWER, total - 1, total)
    assert len(sub.test_results) == total
    assert sub.stdout is None  # judged submissions don't store raw output


def test_executor_crash_marks_failed(db):
    eid = _job(db)
    process_execution(eid, FakeExecutor(error=RuntimeError("kaboom")))
    execution = _reload(db, eid)
    assert execution.status == Status.FAILED and execution.submission.status == Status.FAILED
    assert "kaboom" not in execution.error_message  # no internals leaked


def test_infrastructure_failure_is_failed(db):
    eid = _job(db)
    process_execution(eid, FakeExecutor(ExecutionOutcome(Status.FAILED, message="Execution service unavailable")))
    execution = _reload(db, eid)
    assert execution.status == Status.FAILED
    assert execution.error_message == "Execution service unavailable"


def test_duplicate_delivery_is_ignored(db):
    eid = _job(db)
    fake = FakeExecutor(ExecutionOutcome(Status.COMPLETED, runs=[RunResult(Status.COMPLETED)]))
    process_execution(eid, fake)
    process_execution(eid, fake)
    process_execution("missing-id", fake)
    assert len(fake.calls) == 1
