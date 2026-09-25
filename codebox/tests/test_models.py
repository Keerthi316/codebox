from sqlalchemy import func, inspect, select

from app.database import engine
from app.models import Execution, Problem, Submission, TestCase, User
from app.seed.problems import PROBLEMS, seed_problems


def _user(db, name="zoe"):
    user = User(username=name, email=f"{name}@example.com", password_hash="x")
    db.add(user)
    db.commit()
    return user


def test_seed_creates_required_problems_with_hidden_tests(db):
    slugs = set(db.scalars(select(Problem.slug)))
    assert {"two-sum", "reverse-string", "valid-parentheses",
            "maximum-subarray", "binary-search"} <= slugs
    for problem in db.scalars(select(Problem)):
        assert problem.description and problem.constraints and problem.examples
        assert set(problem.starter_code) == {"python", "javascript", "java", "cpp"}
        assert len(problem.test_cases) >= 5
        assert sum(t.is_sample for t in problem.test_cases) == 1
        assert all(t.expected_output.endswith("\n") for t in problem.test_cases)


def test_sample_test_matches_first_example(db):
    for problem in db.scalars(select(Problem)):
        sample = next(t for t in problem.test_cases if t.is_sample)
        assert sample.input.strip() == problem.examples[0]["input"].strip()
        assert sample.expected_output.strip() == problem.examples[0]["output"].strip()


def test_seed_is_idempotent(db):
    before = db.scalar(select(func.count(TestCase.id)))
    seed_problems(db)
    seed_problems(db)
    assert db.scalar(select(func.count(Problem.id))) == len(PROBLEMS)
    assert db.scalar(select(func.count(TestCase.id))) == before


def test_submission_execution_relationships_and_cascade(db):
    user = _user(db)
    problem = db.scalar(select(Problem).where(Problem.slug == "two-sum"))
    submission = Submission(user_id=user.id, problem_id=problem.id, kind="submit",
                            language="python", source_code="print(1)")
    execution = Execution(submission=submission)
    db.add_all([submission, execution])
    db.commit()

    assert len(execution.id) == 36  # UUID, not guessable
    assert execution.status == "QUEUED" and submission.status == "QUEUED"
    assert submission.execution is execution and submission.user is user
    assert submission.problem.slug == "two-sum"

    db.delete(user)
    db.commit()
    assert db.scalar(select(func.count(Submission.id))) == 0
    assert db.scalar(select(func.count(Execution.id))) == 0


def test_expected_indexes_exist():
    inspector = inspect(engine)
    sub_indexes = {ix["name"] for ix in inspector.get_indexes("submissions")}
    assert {"ix_submissions_user_created", "ix_submissions_user_id",
            "ix_submissions_status", "ix_submissions_created_at"} <= sub_indexes
    assert "ix_test_cases_problem_id" in {ix["name"] for ix in inspector.get_indexes("test_cases")}
    user_indexes = {ix["name"]: ix for ix in inspector.get_indexes("users")}
    assert user_indexes["ix_users_username"]["unique"]
    assert user_indexes["ix_users_email"]["unique"]
