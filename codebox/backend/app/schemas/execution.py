from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExecuteRequest(BaseModel):
    language: str = Field(examples=["python"])
    source_code: str = Field(min_length=1)
    stdin: str = ""
    problem_id: Optional[int] = Field(default=None, description="Optional problem context")


class SubmitRequest(BaseModel):
    problem_id: int
    language: str
    source_code: str = Field(min_length=1)


class ExecutionAccepted(BaseModel):
    execution_id: str
    submission_id: int
    status: str


class TestResultOut(BaseModel):
    __test__ = False

    index: int
    passed: bool
    status: str
    time_ms: int = 0
    memory_kb: int = 0
    is_sample: bool = False
    message: Optional[str] = None
    # Only present for sample test cases; hidden cases never reveal data.
    input: Optional[str] = None
    expected_output: Optional[str] = None
    actual_output: Optional[str] = None
    stderr: Optional[str] = None


class ExecutionResult(BaseModel):
    execution_id: str
    submission_id: int
    kind: str
    language: str
    status: str
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    execution_time: Optional[int] = Field(default=None, description="milliseconds")
    memory_used: Optional[int] = Field(default=None, description="kilobytes")
    passed_count: Optional[int] = None
    total_count: Optional[int] = None
    test_results: Optional[list[TestResultOut]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
