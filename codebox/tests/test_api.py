from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import get_settings
from app.models import Execution, Submission
from app.services import executions as execution_service
from conftest import register

PY = "print(input())"


def _problem_id(client, auth, slug="two-sum"):
    return client.get(f"/api/v1/problems/{slug}", headers=auth).json()["id"]


# ---------------------------------------------------------------- problems / meta

def test_problems_require_login(client):
    assert client.get("/api/v1/problems").status_code == 401
    assert client.get("/api/v1/problems/two-sum").status_code == 401


def test_problem_list_and_detail_never_expose_test_cases(client, auth):
    problems = client.get("/api/v1/problems", headers=auth).json()
    assert len(problems) >= 5
    detail = client.get("/api/v1/problems/two-sum", headers=auth).json()
    assert detail["title"] == "Two Sum"
    assert detail["test_case_count"] >= 5
    assert set(detail["starter_code"]) == {"python", "javascript", "java", "cpp"}
    assert "test_cases" not in detail and "expected_output" not in str(detail)
    assert client.get(f"/api/v1/problems/{detail['id']}", headers=auth).json()["slug"] == "two-sum"
    assert client.get("/api/v1/problems/nope", headers=auth).status_code == 404


def test_languages_endpoint(client):
    data = client.get("/api/v1/languages").json()
    assert {lang["key"] for lang in data["languages"]} == {"python", "javascript", "java", "cpp"}
    assert data["limits"]["memory"] == get_settings().memory_limit


def test_health_reports_redis_down(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "ok", "redis": "unavailable"}


# ---------------------------------------------------------------- execute

def test_execute_queues_job(client, auth, dispatched, db):
    response = client.post("/api/v1/execute", headers=auth,
                           json={"language": "python", "source_code": PY, "stdin": "hi"})
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "QUEUED"
    assert dispatched == [body["execution_id"]]
    submission = db.get(Submission, body["submission_id"])
    assert (submission.kind, submission.stdin, submission.language) == ("run", "hi", "python")

    result = client.get(f"/api/v1/executions/{body['execution_id']}", headers=auth).json()
    assert result["status"] == "QUEUED" and result["kind"] == "run"


@pytest.mark.parametrize("payload,code", [
    ({"language": "ruby", "source_code": PY}, 400),
    ({"language": "python", "source_code": "   \n"}, 400),
    ({"language": "python", "source_code": ""}, 422),
    ({"language": "python", "source_code": "x" * (65 * 1024)}, 413),
    ({"language": "python", "source_code": PY, "stdin": "y" * (65 * 1024)}, 413),
    ({"language": "python", "source_code": PY, "problem_id": 9999}, 404),
])
def test_execute_validation(client, auth, dispatched, payload, code):
    response = client.post("/api/v1/execute", headers=auth, json=payload)
    assert response.status_code == code
    assert "detail" in response.json()
    assert dispatched == []


def test_language_is_case_insensitive(client, auth):
    response = client.post("/api/v1/execute", headers=auth,
                           json={"language": "Python", "source_code": PY})
    assert response.status_code == 202


def test_pending_execution_limit(client, auth):
    limit = get_settings().max_pending_executions_per_user
    for _ in range(limit):
        assert client.post("/api/v1/execute", headers=auth,
                           json={"language": "python", "source_code": PY}).status_code == 202
    response = client.post("/api/v1/execute", headers=auth,
                           json={"language": "python", "source_code": PY})
    assert response.status_code == 429


def test_queue_failure_marks_execution_failed(client, auth, db, monkeypatch):
    def broken(_execution_id):
        raise ConnectionError("redis down")

    monkeypatch.setattr(execution_service, "dispatch", broken)
    response = client.post("/api/v1/execute", headers=auth,
                           json={"language": "python", "source_code": PY})
    assert response.status_code == 503
    assert "queue" in response.json()["detail"].lower()
    execution = db.scalars(select(Execution)).one()
    db.refresh(execution)
    assert execution.status == "FAILED" and execution.submission.status == "FAILED"


def test_real_dispatch_fails_fast_without_redis(client, auth, monkeypatch):
    """With the real Celery producer and an unreachable Redis, the API returns 503."""
    monkeypatch.undo()
    response = client.post("/api/v1/execute", headers=auth,
                           json={"language": "python", "source_code": PY})
    assert response.status_code == 503


def test_stale_execution_is_expired(client, auth, db):
    body = client.post("/api/v1/execute", headers=auth,
                       json={"language": "python", "source_code": PY}).json()
    execution = db.get(Execution, body["execution_id"])
    execution.created_at = datetime.now(timezone.utc) - timedelta(
        seconds=get_settings().stale_execution_seconds + 5)
    db.commit()
    result = client.get(f"/api/v1/executions/{body['execution_id']}", headers=auth).json()
    assert result["status"] == "FAILED"
    assert "did not finish" in result["error_message"]


# ---------------------------------------------------------------- ownership

def test_users_cannot_see_each_others_work(client, auth):
    body = client.post("/api/v1/execute", headers=auth,
                       json={"language": "python", "source_code": PY}).json()
    mallory = register(client, "mallory")
    assert client.get(f"/api/v1/executions/{body['execution_id']}", headers=mallory).status_code == 404
    assert client.get(f"/api/v1/submissions/{body['submission_id']}", headers=mallory).status_code == 404
    assert client.get("/api/v1/submissions", headers=mallory).json()["total"] == 0
    assert client.get("/api/v1/executions/does-not-exist", headers=auth).status_code == 404


# ---------------------------------------------------------------- submissions

def test_submit_and_history(client, auth, dispatched):
    pid = _problem_id(client, auth)
    submit = client.post("/api/v1/submissions", headers=auth,
                         json={"problem_id": pid, "language": "cpp", "source_code": "int main(){}"})
    assert submit.status_code == 202
    client.post("/api/v1/execute", headers=auth, json={"language": "python", "source_code": PY})
    assert len(dispatched) == 2

    history = client.get("/api/v1/submissions", headers=auth).json()
    assert history["total"] == 2
    latest, first = history["items"]
    assert latest["kind"] == "run" and first["kind"] == "submit"
    assert first["problem_title"] == "Two Sum"

    only_submits = client.get("/api/v1/submissions?kind=submit", headers=auth).json()
    assert [i["id"] for i in only_submits["items"]] == [first["id"]]
    by_problem = client.get(f"/api/v1/submissions?problem_id={pid}", headers=auth).json()
    assert by_problem["total"] == 1

    detail = client.get(f"/api/v1/submissions/{first['id']}", headers=auth).json()
    assert detail["source_code"] == "int main(){}" and detail["language"] == "cpp"


def test_submit_requires_existing_problem(client, auth):
    response = client.post("/api/v1/submissions", headers=auth,
                           json={"problem_id": 424242, "language": "python", "source_code": PY})
    assert response.status_code == 404


def test_submission_pagination(client, auth, dispatched, db):
    for i in range(3):
        client.post("/api/v1/execute", headers=auth,
                    json={"language": "python", "source_code": f"print({i})"})
    page = client.get("/api/v1/submissions?page=2&page_size=2", headers=auth).json()
    assert page["total"] == 3 and len(page["items"]) == 1 and page["page"] == 2
    assert client.get("/api/v1/submissions?page_size=500", headers=auth).status_code == 422


def test_problem_list_has_tags_status_and_community_stats(client, auth, db):
    from app.models import Execution, User

    problems = client.get("/api/v1/problems", headers=auth).json()
    assert len(problems) == 15
    assert [p["id"] for p in problems] == sorted(p["id"] for p in problems)
    assert {p["difficulty"] for p in problems} == {"Easy", "Medium", "Hard"}
    assert all(p["tags"] for p in problems)
    two_sum = next(p for p in problems if p["slug"] == "two-sum")
    assert (two_sum["solved"], two_sum["attempted"], two_sum["submissions"], two_sum["acceptance_rate"]) == (False, False, 0, None)

    me = db.scalar(select(User).where(User.username == "alice"))
    other = register(client, "bob")  # noqa: F841 - second user for community stats
    bob = db.scalar(select(User).where(User.username == "bob"))

    def judged(user, status):
        sub = Submission(user_id=user.id, problem_id=two_sum["id"], kind="submit", language="python",
                         source_code="x", status=status)
        db.add_all([sub, Execution(submission=sub, status="COMPLETED")])
        db.commit()

    judged(me, "WRONG_ANSWER")
    summary = next(p for p in client.get("/api/v1/problems", headers=auth).json() if p["slug"] == "two-sum")
    assert (summary["solved"], summary["attempted"]) == (False, True)

    judged(me, "ACCEPTED")
    judged(bob, "ACCEPTED")
    judged(bob, "TIME_LIMIT_EXCEEDED")
    summary = next(p for p in client.get("/api/v1/problems", headers=auth).json() if p["slug"] == "two-sum")
    assert (summary["solved"], summary["attempted"]) == (True, False)
    assert summary["submissions"] == 4 and summary["acceptance_rate"] == 0.5
    detail = client.get("/api/v1/problems/two-sum", headers=auth).json()
    assert detail["solved"] is True and detail["tags"] == ["Array", "Hash Table"]
