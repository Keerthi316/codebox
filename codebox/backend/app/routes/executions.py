from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import ExecuteRequest, ExecutionAccepted, ExecutionResult, SubmitRequest
from ..services.auth import get_current_user
from ..services.executions import (create_execution, expire_if_stale, get_owned_execution,
                                   to_result)

router = APIRouter(tags=["execution"])


@router.post("/execute", response_model=ExecutionAccepted, status_code=status.HTTP_202_ACCEPTED)
def execute(body: ExecuteRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    """Queue a run of the code with custom stdin. Poll GET /executions/{id} for the result."""
    execution = create_execution(db, user, kind="run", language=body.language,
                                 source_code=body.source_code, stdin=body.stdin,
                                 problem_id=body.problem_id)
    return ExecutionAccepted(execution_id=execution.id, submission_id=execution.submission_id,
                             status=execution.status)


@router.post("/submissions", response_model=ExecutionAccepted,
             status_code=status.HTTP_202_ACCEPTED, tags=["submissions"])
def submit(body: SubmitRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    """Queue a judged submission against all of the problem's test cases."""
    execution = create_execution(db, user, kind="submit", language=body.language,
                                 source_code=body.source_code, problem_id=body.problem_id)
    return ExecutionAccepted(execution_id=execution.id, submission_id=execution.submission_id,
                             status=execution.status)


@router.get("/executions/{execution_id}", response_model=ExecutionResult)
def get_execution(execution_id: str, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    execution = get_owned_execution(db, user, execution_id)
    expire_if_stale(db, execution)
    return to_result(execution)
