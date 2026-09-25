from typing import Literal, Optional

from pydantic import BaseModel, Field

AIAction = Literal["auto", "explain", "debug", "complexity", "optimize"]


class AIRequest(BaseModel):
    action: AIAction = "auto"
    language: str
    source_code: str = Field(min_length=1, max_length=64 * 1024)
    question: Optional[str] = Field(default=None, max_length=2000)
    error: Optional[str] = Field(default=None, max_length=16 * 1024)
    stdin: Optional[str] = Field(default=None, max_length=8 * 1024)
    stdout: Optional[str] = Field(default=None, max_length=8 * 1024)
    problem_id: Optional[int] = None


class AIResponse(BaseModel):
    agent: str
    content: str
    model: str


class AIStatus(BaseModel):
    enabled: bool
    model: Optional[str]
    provider: Optional[str] = None
