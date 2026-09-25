from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.config import get_settings
from app.models import User
from app.services.auth import hash_password, verify_password
from conftest import register


def test_password_hashing_is_salted_and_verifiable():
    first, second = hash_password("correct horse"), hash_password("correct horse")
    assert first != second and "correct horse" not in first
    assert verify_password("correct horse", first)
    assert not verify_password("wrong", first)
    assert not verify_password("x", "not-a-bcrypt-hash")


def test_register_stores_hash_not_plaintext(client, db):
    register(client, "bob", "super-secret-1")
    user = db.scalar(select(User).where(User.username == "bob"))
    assert user.password_hash != "super-secret-1"
    assert user.password_hash.startswith("$2")


def test_register_rejects_duplicates_and_bad_input(client):
    register(client, "carol")
    dup = client.post("/api/v1/auth/register", json={
        "username": "carol", "email": "other@example.com", "password": "password123"})
    assert dup.status_code == 409
    dup_email = client.post("/api/v1/auth/register", json={
        "username": "carol2", "email": "CAROL@example.com", "password": "password123"})
    assert dup_email.status_code == 409
    for body in [
        {"username": "x", "email": "x@example.com", "password": "password123"},
        {"username": "dave", "email": "not-an-email", "password": "password123"},
        {"username": "dave", "email": "d@example.com", "password": "short"},
        {"username": "bad name!", "email": "d@example.com", "password": "password123"},
        {"username": "dave", "email": "d@example.com", "password": "é" * 40},  # > 72 bytes
    ]:
        assert client.post("/api/v1/auth/register", json=body).status_code == 422


def test_login_with_username_or_email(client):
    register(client, "erin", "password-erin")
    for ident in ("erin", "erin@example.com"):
        response = client.post("/api/v1/auth/login", json={"username": ident, "password": "password-erin"})
        assert response.status_code == 200
        assert response.json()["user"]["username"] == "erin"


def test_login_failures_are_generic(client):
    register(client, "frank", "password-frank")
    wrong = client.post("/api/v1/auth/login", json={"username": "frank", "password": "nope-nope"})
    missing = client.post("/api/v1/auth/login", json={"username": "ghost", "password": "nope-nope"})
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json()


def test_me_requires_valid_token(client):
    headers = register(client, "gina")
    assert client.get("/api/v1/auth/me", headers=headers).json()["username"] == "gina"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_expired_and_forged_tokens_are_rejected(client, db):
    register(client, "hank")
    user_id = db.scalar(select(User.id).where(User.username == "hank"))
    settings = get_settings()
    expired = jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         settings.jwt_secret, algorithm="HS256")
    forged = jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        "some-other-secret-that-is-long-enough!!", algorithm="HS256")
    unsigned = jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                          None, algorithm="none")
    for token in (expired, forged, unsigned):
        assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_protected_routes_require_auth(client):
    for method, path in [("post", "/api/v1/execute"), ("post", "/api/v1/submissions"),
                         ("get", "/api/v1/submissions"), ("get", "/api/v1/executions/abc"),
                         ("post", "/api/v1/ai/assist")]:
        assert client.request(method.upper(), path, json={}).status_code == 401, path
