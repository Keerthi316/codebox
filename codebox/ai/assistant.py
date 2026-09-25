"""AI coding assistant.

A deliberately small design: four specialised "agents" that differ only in their
system prompt and in which context they receive, plus a rule-based router. Each
request is a single Chat Completions call to any OpenAI-compatible endpoint, so
no agent framework is needed. Only the code, language and directly relevant
run data (error, input, output) are sent to the model — never user identity,
other submissions or hidden test data.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

import httpx

log = logging.getLogger(__name__)

MAX_CODE_CHARS = 24_000
MAX_CONTEXT_CHARS = 4_000


class AIUnavailableError(Exception):
    """AI is not configured or the provider failed. Message is user-safe."""


@dataclass
class AIConfig:
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout: float = 45.0
    provider: str = "openai"
    extra_headers: dict = field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())


@dataclass
class AssistRequest:
    language: str
    source_code: str
    action: str = "auto"  # auto | explain | debug | complexity | optimize
    question: Optional[str] = None
    error: Optional[str] = None
    stdin: Optional[str] = None
    stdout: Optional[str] = None
    problem: Optional[str] = None  # problem title + statement, if any


@dataclass
class AssistResponse:
    agent: str
    content: str
    model: str


def _clip(text: Optional[str], limit: int = MAX_CONTEXT_CHARS) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "\n...[truncated]"


def _code_block(req: AssistRequest) -> str:
    return f"Language: {req.language}\n\n```{req.language}\n{_clip(req.source_code, MAX_CODE_CHARS)}\n```"


def _problem(req: AssistRequest) -> str:
    return f"\n\nProblem statement:\n{_clip(req.problem, 2000)}" if req.problem else ""


def _question(req: AssistRequest) -> str:
    return f"\n\nUser question: {_clip(req.question, 2000)}" if req.question else ""


@dataclass(frozen=True)
class Agent:
    name: str
    system_prompt: str
    build_context: Callable[[AssistRequest], str]


_STYLE = (" Answer in concise Markdown. Use short sections and code blocks where helpful. "
          "Do not invent program output you were not given.")

AGENTS = {
    "explain": Agent(
        "CodeExplainer",
        "You are CodeExplainer, a patient programming tutor. Explain what the given code "
        "does, step by step, highlighting the key idea and any non-obvious lines." + _STYLE,
        lambda r: _code_block(r) + _problem(r) + _question(r),
    ),
    "debug": Agent(
        "Debugger",
        "You are Debugger, an expert at finding bugs. Identify the most likely root cause "
        "of the failure, point to the exact line(s), explain the error message in plain "
        "language, and show a minimal fix. Mention edge cases the code misses." + _STYLE,
        lambda r: (_code_block(r)
                   + (f"\n\nError / stderr:\n```\n{_clip(r.error)}\n```" if r.error else "")
                   + (f"\n\nInput:\n```\n{_clip(r.stdin, 1500)}\n```" if r.stdin else "")
                   + (f"\n\nProgram output:\n```\n{_clip(r.stdout, 1500)}\n```" if r.stdout else "")
                   + _problem(r) + _question(r)),
    ),
    "complexity": Agent(
        "ComplexityAnalyzer",
        "You are ComplexityAnalyzer. Determine the time and space complexity of the code "
        "in Big-O notation. Justify each bound by pointing at the loops, recursion and data "
        "structures responsible, and state best/worst cases when they differ." + _STYLE,
        lambda r: _code_block(r) + _question(r),
    ),
    "optimize": Agent(
        "Optimizer",
        "You are Optimizer, a senior engineer. Suggest concrete improvements to the code's "
        "performance, readability and robustness. If a better algorithm exists, explain it "
        "with its complexity and provide the improved code." + _STYLE,
        lambda r: _code_block(r) + _problem(r) + _question(r),
    ),
}

_KEYWORDS = [
    ("complexity", re.compile(r"\b(complexity|big[- ]?o|o\(|time|space|memory usage)\b", re.I)),
    ("optimize", re.compile(r"\b(optimi[sz]e|faster|speed ?up|improve|efficient|refactor|clean)", re.I)),
    ("debug", re.compile(r"\b(bug|error|fix|wrong|fail|crash|exception|why (doesn|does not|isn))", re.I)),
    ("explain", re.compile(r"\b(explain|what does|how does|walk me through|understand)", re.I)),
]


def route(req: AssistRequest) -> Agent:
    """Pick an agent: explicit action wins, then the question's intent, then the
    presence of an error, then plain explanation."""
    if req.action in AGENTS:
        return AGENTS[req.action]
    if req.question:
        for key, pattern in _KEYWORDS:
            if pattern.search(req.question):
                return AGENTS[key]
    if req.error and req.error.strip():
        return AGENTS["debug"]
    return AGENTS["explain"]


class AIAssistant:
    def __init__(self, config: AIConfig, transport: Optional[httpx.BaseTransport] = None):
        self.config = config
        self._transport = transport

    def assist(self, req: AssistRequest) -> AssistResponse:
        if not self.config.enabled:
            raise AIUnavailableError(
                "The AI assistant is not configured. Set OPENROUTER_API_KEY "
                "(or OPENAI_API_KEY) to enable it.")
        agent = route(req)
        messages = [
            {"role": "system", "content": agent.system_prompt},
            {"role": "user", "content": agent.build_context(req)},
        ]
        return AssistResponse(agent=agent.name, content=self._chat(messages), model=self.config.model)

    def _chat(self, messages: list) -> str:
        url = self.config.base_url.rstrip("/") + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", **self.config.extra_headers}
        body = {"model": self.config.model, "messages": messages, "temperature": 0.2}
        try:
            with httpx.Client(timeout=self.config.timeout, transport=self._transport) as client:
                response = client.post(url, json=body, headers=headers)
        except httpx.TimeoutException as exc:
            raise AIUnavailableError("The AI provider timed out. Please try again.") from exc
        except httpx.HTTPError as exc:
            log.warning("AI provider unreachable: %s", exc)
            raise AIUnavailableError("The AI provider could not be reached.") from exc

        if response.status_code in (401, 403):
            raise AIUnavailableError("The AI provider rejected the API key.")
        if response.status_code == 402:
            raise AIUnavailableError("The AI provider account is out of credits.")
        if response.status_code == 429:
            raise AIUnavailableError("The AI provider is rate limiting requests. Try again later.")
        if response.status_code >= 400:
            log.warning("AI provider error %s: %s", response.status_code, response.text[:500])
            raise AIUnavailableError(f"The AI provider returned an error ({response.status_code}).")
        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIUnavailableError("The AI provider returned an unexpected response.") from exc
        if not content or not content.strip():
            raise AIUnavailableError("The AI provider returned an empty answer.")
        return content.strip()
