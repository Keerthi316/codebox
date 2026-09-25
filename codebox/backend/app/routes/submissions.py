from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Submission, User
from ..schemas import SubmissionDetail, SubmissionList, SubmissionSummary
from ..services.auth import get_current_user
from ..services.executions import expire_if_stale

router = APIRouter(prefix="/submissions", tags=["submissions"])


def _summary_fields(sub: Submission) -> dict:
    return dict(
        id=sub.id,
        execution_id=sub.execution.id if sub.execution else None,
        kind=sub.kind,
        problem_id=sub.problem_id,
        problem_title=sub.problem.title if sub.problem else None,
        language=sub.language,
        status=sub.status,
        execution_time=sub.execution_time,
        memory_used=sub.memory_used,
        passed_count=sub.passed_count,
        total_count=sub.total_count,
        created_at=sub.created_at,
    )


@router.get("", response_model=SubmissionList)
def list_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    kind: Literal["run", "submit"] | None = None,
    problem_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conditions = [Submission.user_id == user.id]
    if kind:
        conditions.append(Submission.kind == kind)
    if problem_id is not None:
        conditions.append(Submission.problem_id == problem_id)
    total = db.scalar(select(func.count(Submission.id)).where(*conditions))
    rows = db.scalars(
        select(Submission).where(*conditions)
        .options(joinedload(Submission.problem), joinedload(Submission.execution))
        .order_by(Submission.created_at.desc(), Submission.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    return SubmissionList(items=[SubmissionSummary(**_summary_fields(s)) for s in rows],
                          total=total, page=page, page_size=page_size)


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(submission_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    sub = db.get(Submission, submission_id)
    if sub is None or sub.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    if sub.execution:
        expire_if_stale(db, sub.execution)
    return SubmissionDetail(
        **_summary_fields(sub),
        source_code=sub.source_code,
        stdin=sub.stdin,
        stdout=sub.stdout,
        stderr=sub.stderr,
        compile_output=sub.compile_output,
        test_results=sub.test_results,
        error_message=sub.execution.error_message if sub.execution else None,
    )
