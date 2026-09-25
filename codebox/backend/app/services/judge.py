"""Compares program output with expected output. Runs only in the trusted worker;
expected outputs never enter the sandbox and hidden ones never leave the server."""

from dataclasses import dataclass, field
from typing import Optional

from executor.status import Status

MAX_SHOWN = 4096  # chars of input/output shown for sample cases


def normalize(text: str) -> str:
    """Ignore trailing whitespace on each line and trailing blank lines."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip("\n")


def outputs_match(actual: str, expected: str) -> bool:
    return normalize(actual) == normalize(expected)


def _clip(text: Optional[str], limit: int = MAX_SHOWN) -> Optional[str]:
    if text is None or len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text) - limit} more characters)"


@dataclass
class Verdict:
    status: str
    passed: int
    total: int
    results: list = field(default_factory=list)
    time_ms: int = 0
    memory_kb: int = 0
    stderr: Optional[str] = None


def judge(outcome, test_cases) -> Verdict:
    """Build the verdict for a judged submission.

    `outcome` is an executor ExecutionOutcome whose runs align with `test_cases`.
    """
    total = len(test_cases)
    if outcome.status in (Status.COMPILATION_ERROR, Status.FAILED) and not outcome.runs:
        return Verdict(outcome.status, 0, total)

    results, first_failure, first_stderr = [], None, None
    for index, (test, run) in enumerate(zip(test_cases, outcome.runs)):
        if run.status == Status.COMPLETED:
            passed = outputs_match(run.stdout, test.expected_output)
            status = Status.ACCEPTED if passed else Status.WRONG_ANSWER
        else:
            passed, status = False, run.status
        entry = {
            "index": index + 1,
            "passed": passed,
            "status": status,
            "time_ms": run.time_ms,
            "memory_kb": run.memory_kb,
            "is_sample": test.is_sample,
            "message": run.message,
        }
        if test.is_sample:
            entry.update(input=_clip(test.input), expected_output=_clip(test.expected_output),
                         actual_output=_clip(run.stdout), stderr=_clip(run.stderr))
        elif run.stderr and not passed:
            # The program's own error output is fine to show; hidden data is not.
            entry["stderr"] = _clip(run.stderr, 1024)
        results.append(entry)
        if not passed and first_failure is None:
            first_failure, first_stderr = status, run.stderr

    passed_count = sum(1 for r in results if r["passed"])
    if len(results) < total:
        status = Status.FAILED
    else:
        status = Status.ACCEPTED if passed_count == total else first_failure
    return Verdict(
        status=status,
        passed=passed_count,
        total=total,
        results=results,
        time_ms=max((r["time_ms"] for r in results), default=0),
        memory_kb=max((r["memory_kb"] for r in results), default=0),
        stderr=_clip(first_stderr),
    )
