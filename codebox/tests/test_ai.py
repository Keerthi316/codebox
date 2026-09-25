import json

import httpx
import pytest

from ai import AGENTS, AIAssistant, AIConfig, AIUnavailableError, AssistRequest, route
from app.main import app
from app.routes.ai import get_assistant


def _req(**kw):
    return AssistRequest(language="python", source_code="print(1/0)", **kw)


@pytest.mark.parametrize("kwargs,agent", [
    ({"action": "explain"}, "CodeExplainer"),
    ({"action": "debug"}, "Debugger"),
    ({"action": "complexity"}, "ComplexityAnalyzer"),
    ({"action": "optimize"}, "Optimizer"),
    ({"question": "What is the time complexity?"}, "ComplexityAnalyzer"),
    ({"question": "What's the Big-O here"}, "ComplexityAnalyzer"),
    ({"question": "How can I make this faster?"}, "Optimizer"),
    ({"question": "Why does this crash?"}, "Debugger"),
    ({"question": "Explain this to me"}, "CodeExplainer"),
    ({"error": "ZeroDivisionError: division by zero"}, "Debugger"),
    ({}, "CodeExplainer"),
])
def test_routing(kwargs, agent):
    assert route(_req(**kwargs)).name == agent


def test_context_contains_only_relevant_information():
    req = _req(error="ZeroDivisionError", stdin="42", stdout="partial", problem="Two Sum")
    debug_ctx = AGENTS["debug"].build_context(req)
    assert all(s in debug_ctx for s in ("print(1/0)", "ZeroDivisionError", "42", "partial", "Two Sum"))
    complexity_ctx = AGENTS["complexity"].build_context(req)
    assert "ZeroDivisionError" not in complexity_ctx and "42" not in complexity_ctx
    long_ctx = AGENTS["explain"].build_context(AssistRequest("python", "x" * 100_000))
    assert len(long_ctx) < 30_000


def _assistant(handler):
    return AIAssistant(AIConfig(api_key="sk-test", base_url="https://llm.example/v1", model="m"),
                       transport=httpx.MockTransport(handler))


def test_successful_completion_sends_openai_compatible_request():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "  It divides by zero. "}}]})

    result = _assistant(handler).assist(_req(action="debug", error="ZeroDivisionError"))
    assert (result.agent, result.content, result.model) == ("Debugger", "It divides by zero.", "m")
    assert seen["url"] == "https://llm.example/v1/chat/completions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "m"
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize("response,fragment", [
    (httpx.Response(401, json={}), "rejected the API key"),
    (httpx.Response(429, json={}), "rate limiting"),
    (httpx.Response(402, json={}), "out of credits"),
    (httpx.Response(500, text="oops"), r"error \(500\)"),
    (httpx.Response(200, json={"unexpected": True}), "unexpected response"),
    (httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}), "empty answer"),
])
def test_provider_errors_are_user_safe(response, fragment):
    with pytest.raises(AIUnavailableError, match=fragment):
        _assistant(lambda _r: response).assist(_req())


def test_timeouts_and_network_errors():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(AIUnavailableError, match="timed out"):
        _assistant(timeout).assist(_req())
    with pytest.raises(AIUnavailableError, match="could not be reached"):
        _assistant(refused).assist(_req())


def test_disabled_without_api_key():
    with pytest.raises(AIUnavailableError, match="not configured"):
        AIAssistant(AIConfig(api_key="")).assist(_req())


# ------------------------------------------------------------------ API layer

def test_api_graceful_fallback_without_key(client, auth):
    assert client.get("/api/v1/ai/status").json() == {"enabled": False, "model": None, "provider": None}
    response = client.post("/api/v1/ai/assist", headers=auth,
                           json={"language": "python", "source_code": "print(1)"})
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_api_with_mock_provider(client, auth):
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "O(n) time"}}]})

    app.dependency_overrides[get_assistant] = lambda: _assistant(handler)
    try:
        problem_id = client.get("/api/v1/problems/two-sum", headers=auth).json()["id"]
        response = client.post("/api/v1/ai/assist", headers=auth, json={
            "action": "optimize", "language": "python", "source_code": "print(1)",
            "problem_id": problem_id})
        assert client.get("/api/v1/ai/status").json()["enabled"] is True
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"agent": "Optimizer", "content": "O(n) time", "model": "m"}
    assert "Two Sum" in captured["body"]["messages"][1]["content"]


def test_api_validates_action(client, auth):
    response = client.post("/api/v1/ai/assist", headers=auth,
                           json={"action": "hack", "language": "python", "source_code": "x"})
    assert response.status_code == 422


def test_openrouter_is_preferred_when_key_is_set(monkeypatch):
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-test")
    monkeypatch.setattr(settings, "openai_api_key", "sk-openai")
    assistant = get_assistant()
    assert assistant.config.provider == "openrouter"
    assert assistant.config.base_url == "https://openrouter.ai/api/v1"
    assert assistant.config.model == settings.openrouter_model

    seen = {}

    def handler(request):
        seen.update(url=str(request.url), auth=request.headers["authorization"],
                    title=request.headers.get("x-title"), referer=request.headers.get("http-referer"))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    AIAssistant(assistant.config, transport=httpx.MockTransport(handler)).assist(_req())
    assert seen == {"url": "https://openrouter.ai/api/v1/chat/completions", "auth": "Bearer sk-or-test",
                    "title": "CodeBox", "referer": settings.public_url}


def test_openai_used_without_openrouter_key(monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "openai_api_key", "sk-openai")
    assert get_assistant().config.provider == "openai"
