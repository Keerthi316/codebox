"""End-to-end tests against a running stack (frontend proxy → API → Redis →
Celery → Docker sandbox → PostgreSQL).

    docker compose up -d --build
    CODEBOX_E2E_URL=http://127.0.0.1:8080 pytest tests/e2e -m e2e
"""

import os
import secrets
import time

import httpx
import pytest

from solutions import solution

BASE = os.environ.get("CODEBOX_E2E_URL")
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not BASE, reason="set CODEBOX_E2E_URL to run end-to-end tests"),
]


@pytest.fixture(scope="module")
def http():
    with httpx.Client(base_url=f"{BASE}/api/v1", timeout=30) as client:
        yield client


def _user(http):
    name = "e2e_" + secrets.token_hex(4)
    email = f"codebox.{name.replace('_', '')}@gmail.com"  # real mail domain, valid Gmail username
    response = http.post("/auth/register", json={
        "username": name, "email": email, "password": "e2e-password-123"})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_undeliverable_and_disposable_emails_are_rejected(http):
    for email in ("someone@no-such-domain-codebox-e2e.com", "someone@mailinator.com",
                  "abc@gmail.com", "someone@gmal.co"):
        response = http.post("/auth/register", json={
            "username": "bad_" + secrets.token_hex(3), "email": email, "password": "e2e-password-123"})
        assert response.status_code == 422, response.text


@pytest.fixture(scope="module")
def auth(http):
    return _user(http)


def wait(http, auth, execution_id, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = http.get(f"/executions/{execution_id}", headers=auth).json()
        if result["status"] not in ("QUEUED", "RUNNING"):
            return result
        time.sleep(0.5)
    raise AssertionError("execution did not finish")


def run(http, auth, language, code, stdin=""):
    response = http.post("/execute", headers=auth,
                         json={"language": language, "source_code": code, "stdin": stdin})
    assert response.status_code == 202, response.text
    return wait(http, auth, response.json()["execution_id"])


def test_health(http):
    assert http.get("/health").json() == {"status": "ok", "database": "ok", "redis": "ok"}


def test_frontend_is_served():
    response = httpx.get(BASE + "/problems")  # SPA route falls back to index.html
    assert response.status_code == 200 and '<div id="root">' in response.text
    assert "Content-Security-Policy" in response.headers


@pytest.mark.parametrize("language,code", [
    ("python", "print(int(input()) * 2)"),
    ("javascript", "console.log(Number(require('fs').readFileSync(0,'utf8')) * 2)"),
    ("java", "import java.util.*; public class Main { public static void main(String[] a) {"
             " System.out.println(new Scanner(System.in).nextInt() * 2); } }"),
    ("cpp", "#include <iostream>\nint main(){int x; std::cin >> x; std::cout << x * 2 << std::endl;}"),
])
def test_all_languages_execute(http, auth, language, code):
    result = run(http, auth, language, code, "21")
    assert result["status"] == "COMPLETED", result
    assert result["stdout"].strip() == "42"
    assert result["execution_time"] is not None and result["memory_used"] > 0


def test_limits_and_errors(http, auth):
    assert run(http, auth, "python", "while True: pass")["status"] == "TIME_LIMIT_EXCEEDED"
    assert run(http, auth, "python", "x = bytearray(1 << 30)")["status"] == "MEMORY_LIMIT_EXCEEDED"
    rte = run(http, auth, "python", "raise SystemExit(3)")
    assert rte["status"] == "RUNTIME_ERROR"
    ce = run(http, auth, "cpp", "int main( {")
    assert ce["status"] == "COMPILATION_ERROR" and ce["compile_output"]


def test_submission_judging_and_history(http, auth):
    problem = http.get("/problems/two-sum", headers=auth).json()
    accepted = http.post("/submissions", headers=auth, json={
        "problem_id": problem["id"], "language": "python",
        "source_code": solution("two-sum", "python")}).json()
    result = wait(http, auth, accepted["execution_id"])
    assert result["status"] == "ACCEPTED", result
    assert result["passed_count"] == result["total_count"] == problem["test_case_count"]

    wrong = http.post("/submissions", headers=auth, json={
        "problem_id": problem["id"], "language": "python",
        "source_code": problem["starter_code"]["python"]}).json()
    result = wait(http, auth, wrong["execution_id"])
    assert result["status"] == "WRONG_ANSWER" and result["passed_count"] == 0
    hidden = [r for r in result["test_results"] if not r["is_sample"]]
    assert hidden and all(r.get("expected_output") is None for r in hidden)

    history = http.get("/submissions?kind=submit", headers=auth).json()
    assert {accepted["submission_id"], wrong["submission_id"]} <= {i["id"] for i in history["items"]}
    detail = http.get(f"/submissions/{accepted['submission_id']}", headers=auth).json()
    assert detail["status"] == "ACCEPTED" and detail["problem_title"] == "Two Sum"
    assert any(p["solved"] for p in http.get("/problems", headers=auth).json())


def test_isolation_between_users(http, auth):
    execution = http.post("/execute", headers=auth,
                          json={"language": "python", "source_code": "print(1)"}).json()
    wait(http, auth, execution["execution_id"])
    other = _user(http)
    assert http.get(f"/executions/{execution['execution_id']}", headers=other).status_code == 404
    assert http.get(f"/submissions/{execution['submission_id']}", headers=other).status_code == 404


def test_ai_fails_gracefully_or_answers(http, auth):
    status = http.get("/ai/status").json()
    response = http.post("/ai/assist", headers=auth, json={
        "action": "complexity", "language": "python", "source_code": "print(sum(range(10)))"})
    if status["enabled"]:
        assert response.status_code in (200, 503)
    else:
        assert response.status_code == 503 and "OPENAI_API_KEY" in response.json()["detail"]
