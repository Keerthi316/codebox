from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .execution import TestResultOut


class SubmissionSummary(BaseModel):
    id: int
    execution_id: Optional[str]
    kind: str
    problem_id: Optional[int]
    problem_title: Optional[str]
    language: str
    status: str
    execution_time: Optional[int]
    memory_used: Optional[int]
    passed_count: Optional[int]
    total_count: Optional[int]
    created_at: datetime


class SubmissionList(BaseModel):
    items: list[SubmissionSummary]
    total: int
    page: int
    page_size: int


class SubmissionDetail(SubmissionSummary):
    source_code: str
    stdin: str
    stdout: Optional[str]
    stderr: Optional[str]
    compile_output: Optional[str]
    test_results: Optional[list[TestResultOut]]
    error_message: Optional[str]
