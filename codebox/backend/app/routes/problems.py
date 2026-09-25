from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from executor.status import Status

from ..database import get_db
from ..models import Problem, Submission, User
from ..schemas import ProblemDetail, ProblemSummary
from ..services.auth import get_current_user

router = APIRouter(prefix="/problems", tags=["problems"])

def _user_status(db: Session, user: User) -> tuple[set[int], set[int]]:
    """(solved problem ids, attempted problem ids) for this user's judged submissions."""
    rows = db.execute(
        select(Submission.problem_id, func.max(case((Submission.status == Status.ACCEPTED, 1), else_=0)))
        .where(Submission.user_id == user.id, Submission.kind == "submit",
               Submission.problem_id.is_not(None))
        .group_by(Submission.problem_id)
    ).all()
    solved = {pid for pid, accepted in rows if accepted}
    return solved, {pid for pid, _ in rows} - solved


def _community_stats(db: Session) -> dict[int, tuple[int, int]]:
    """problem id -> (judged submissions, accepted) across all users."""
    rows = db.execute(
        select(Submission.problem_id, func.count(Submission.id),
               func.sum(case((Submission.status == Status.ACCEPTED, 1), else_=0)))
        .where(Submission.kind == "submit", Submission.problem_id.is_not(None),
               Submission.status.not_in(Status.PENDING + (Status.FAILED,)))
        .group_by(Submission.problem_id)
    ).all()
    return {pid: (int(total), int(accepted or 0)) for pid, total, accepted in rows}


def _summary(p: Problem, solved: set[int], attempted: set[int], stats: dict) -> dict:
    total, accepted = stats.get(p.id, (0, 0))
    return dict(id=p.id, slug=p.slug, title=p.title, difficulty=p.difficulty, tags=p.tags or [],
                solved=p.id in solved, attempted=p.id in attempted, submissions=total,
                acceptance_rate=round(accepted / total, 4) if total else None)


@router.get("", response_model=list[ProblemSummary])
def list_problems(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    solved, attempted = _user_status(db, user)
    stats = _community_stats(db)
    return [ProblemSummary(**_summary(p, solved, attempted, stats))
            for p in db.scalars(select(Problem).order_by(Problem.id))]


@router.get("/{id_or_slug}", response_model=ProblemDetail)
def get_problem(id_or_slug: str, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    query = select(Problem).where(
        Problem.id == int(id_or_slug) if id_or_slug.isdigit() else Problem.slug == id_or_slug)
    problem = db.scalar(query)
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    solved, attempted = _user_status(db, user)
    # Test cases are deliberately not serialised; only their count is exposed.
    return ProblemDetail(
        **_summary(problem, solved, attempted, _community_stats(db)),
        description=problem.description,
        constraints=problem.constraints, examples=problem.examples,
        starter_code=problem.starter_code, test_case_count=len(problem.test_cases),
    )
