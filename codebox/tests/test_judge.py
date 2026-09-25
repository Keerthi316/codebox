from types import SimpleNamespace

from app.services.judge import judge, normalize, outputs_match
from executor.executor import ExecutionOutcome, RunResult
from executor.status import Status


def _tests(*pairs):
    return [SimpleNamespace(input=i, expected_output=o, is_sample=(n == 0))
            for n, (i, o) in enumerate(pairs)]


def _ok(out, time_ms=10, memory_kb=1000):
    return RunResult(Status.COMPLETED, stdout=out, time_ms=time_ms, memory_kb=memory_kb)


def test_normalize_ignores_trailing_whitespace_only():
    assert outputs_match("1 2\n", "1 2")
    assert outputs_match("a  \r\nb\n\n\n", "a\nb")
    assert not outputs_match("1  2", "1 2")
    assert not outputs_match(" 1", "1")
    assert normalize("x\r\ny  \n") == "x\ny"


def test_all_passed_is_accepted():
    tests = _tests(("1", "1\n"), ("2", "2\n"))
    verdict = judge(ExecutionOutcome(Status.COMPLETED, runs=[_ok("1\n", 5, 900), _ok("2", 9, 1200)]), tests)
    assert (verdict.status, verdict.passed, verdict.total) == (Status.ACCEPTED, 2, 2)
    assert verdict.time_ms == 9 and verdict.memory_kb == 1200
    assert [r["passed"] for r in verdict.results] == [True, True]


def test_wrong_answer_reports_4_of_5_and_hides_hidden_data():
    tests = _tests(*[(f"in{i}", f"out{i}\n") for i in range(5)])
    runs = [_ok(f"out{i}") for i in range(4)] + [_ok("nope")]
    verdict = judge(ExecutionOutcome(Status.COMPLETED, runs=runs), tests)
    assert (verdict.status, verdict.passed, verdict.total) == (Status.WRONG_ANSWER, 4, 5)
    sample, hidden = verdict.results[0], verdict.results[4]
    assert sample["expected_output"] == "out0\n" and sample["input"] == "in0"
    assert not hidden["passed"] and hidden["status"] == Status.WRONG_ANSWER
    for key in ("input", "expected_output", "actual_output"):
        assert key not in hidden
    assert "out4" not in str(verdict.results[1:])


def test_first_failure_determines_status():
    tests = _tests(("a", "1"), ("b", "2"), ("c", "3"))
    runs = [_ok("1"), RunResult(Status.TIME_LIMIT_EXCEEDED, message="Time limit exceeded"),
            RunResult(Status.RUNTIME_ERROR, stderr="Traceback: boom")]
    verdict = judge(ExecutionOutcome(Status.TIME_LIMIT_EXCEEDED, runs=runs), tests)
    assert verdict.status == Status.TIME_LIMIT_EXCEEDED
    assert verdict.passed == 1
    assert verdict.results[2]["stderr"] == "Traceback: boom"  # program's own stderr is OK


def test_compilation_error_and_failure():
    tests = _tests(("a", "1"))
    ce = judge(ExecutionOutcome(Status.COMPILATION_ERROR, compile_output="error"), tests)
    assert (ce.status, ce.passed, ce.total, ce.results) == (Status.COMPILATION_ERROR, 0, 1, [])
    failed = judge(ExecutionOutcome(Status.FAILED, message="docker down"), tests)
    assert failed.status == Status.FAILED


def test_missing_runs_is_failure():
    tests = _tests(("a", "1"), ("b", "2"))
    verdict = judge(ExecutionOutcome(Status.COMPLETED, runs=[_ok("1")]), tests)
    assert verdict.status == Status.FAILED
