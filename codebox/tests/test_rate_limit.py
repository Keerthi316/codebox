import pytest
import redis

from app.config import get_settings
from app.services import rate_limit
from conftest import register


class FakeRedis:
    def __init__(self):
        self.counts = {}

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, store):
        self.store, self.ops = store, []

    def incr(self, name):
        self.ops.append(name)

    def expire(self, name, seconds):
        pass

    def execute(self):
        name = self.ops[0]
        self.store.counts[name] = self.store.counts.get(name, 0) + 1
        return [self.store.counts[name], True]


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(rate_limit, "_client", fake)
    return fake


def test_hit_counts_per_window(fake_redis):
    assert all(rate_limit.hit("k", 3, 60) for _ in range(3))
    assert rate_limit.hit("k", 3, 60) is False
    assert rate_limit.hit("other", 3, 60) is True


def test_fails_open_when_redis_is_down(monkeypatch):
    class Broken:
        def pipeline(self):
            raise redis.ConnectionError("down")

    monkeypatch.setattr(rate_limit, "_client", Broken())
    assert rate_limit.hit("k", 0, 60) is True


def test_login_brute_force_is_limited(client, fake_redis):
    register(client, "victim", "right-password")
    limit = get_settings().rate_limit_login_per_minute
    codes = [client.post("/api/v1/auth/login", json={"username": "victim", "password": "wrong-pass"}).status_code
             for _ in range(limit + 1)]
    assert codes[:limit] == [401] * limit
    assert codes[-1] == 429
    # even the right password is refused until the window resets
    response = client.post("/api/v1/auth/login", json={"username": "victim", "password": "right-password"})
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"


def test_execution_rate_limit(client, fake_redis, monkeypatch):
    monkeypatch.setattr(get_settings(), "rate_limit_executions_per_minute", 2)
    monkeypatch.setattr(get_settings(), "max_pending_executions_per_user", 100)
    headers = register(client, "spammer")
    codes = [client.post("/api/v1/execute", headers=headers,
                         json={"language": "python", "source_code": "print(1)"}).status_code for _ in range(3)]
    assert codes == [202, 202, 429]
