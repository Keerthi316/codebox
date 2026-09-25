import os
import secrets
import tempfile

import pytest

# Configure before the app (and its engine) is imported. Unit/API tests use SQLite;
# set TEST_DATABASE_URL to run them against PostgreSQL instead.
_db_dir = tempfile.mkdtemp(prefix="codebox-test-")
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL",
                                            f"sqlite:///{_db_dir}/test.db")
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
# No DNS lookups in tests (test_email_checks.py covers the mail-server check with fakes).
os.environ["EMAIL_CHECK_DELIVERABILITY"] = "false"
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:1/0")  # unreachable unless overridden

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.problems import seed_problems  # noqa: E402
from app.services import executions as execution_service  # noqa: E402


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_problems(session)
    yield session
    session.close()


@pytest.fixture
def dispatched(monkeypatch):
    """Capture enqueued execution ids instead of talking to Redis."""
    sent = []
    monkeypatch.setattr(execution_service, "dispatch", sent.append)
    return sent


@pytest.fixture
def client(db, dispatched):
    with TestClient(app) as test_client:
        yield test_client


def register(client, username="alice", password="s3cret-password", email=None):
    response = client.post("/api/v1/auth/register", json={
        "username": username, "email": email or f"{username}@example.com", "password": password})
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)
