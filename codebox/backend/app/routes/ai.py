from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ai import AIAssistant, AIConfig, AIUnavailableError, AssistRequest

from ..config import get_settings
from ..database import get_db
from ..models import Problem, User
from ..schemas import AIRequest, AIResponse, AIStatus
from ..services.auth import get_current_user
from ..services.rate_limit import enforce

router = APIRouter(prefix="/ai", tags=["ai"])


def get_assistant() -> AIAssistant:
    s = get_settings()
    if s.openrouter_api_key.strip():
        return AIAssistant(AIConfig(
            api_key=s.openrouter_api_key, base_url=s.openrouter_base_url,
            model=s.openrouter_model, timeout=s.ai_timeout, provider="openrouter",
            # optional OpenRouter attribution headers
            extra_headers={"HTTP-Referer": s.public_url, "X-Title": s.app_name}))
    return AIAssistant(AIConfig(api_key=s.openai_api_key, base_url=s.openai_base_url,
                                model=s.openai_model, timeout=s.ai_timeout))


@router.get("/status", response_model=AIStatus)
def ai_status(assistant: AIAssistant = Depends(get_assistant)):
    enabled = assistant.config.enabled
    return AIStatus(enabled=enabled, model=assistant.config.model if enabled else None,
                    provider=assistant.config.provider if enabled else None)


@router.post("/assist", response_model=AIResponse)
def assist(body: AIRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user),
           assistant: AIAssistant = Depends(get_assistant)):
    if assistant.config.enabled:
        enforce(f"ai:{user.id}", get_settings().rate_limit_ai_per_minute)
    problem_text = None
    if body.problem_id is not None:
        problem = db.get(Problem, body.problem_id)
        if problem is not None:
            problem_text = f"{problem.title}\n\n{problem.description}"
    request = AssistRequest(language=body.language, source_code=body.source_code,
                            action=body.action, question=body.question, error=body.error,
                            stdin=body.stdin, stdout=body.stdout, problem=problem_text)
    try:
        result = assistant.assist(request)
    except AIUnavailableError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))
    return AIResponse(agent=result.agent, content=result.content, model=result.model)
