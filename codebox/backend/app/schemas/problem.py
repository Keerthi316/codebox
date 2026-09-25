from pydantic import BaseModel, ConfigDict


class ProblemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    difficulty: str
    tags: list[str] = []
    solved: bool = False
    attempted: bool = False  # submitted at least once but not solved yet
    submissions: int = 0  # judged submissions by all users
    acceptance_rate: float | None = None  # accepted / submissions, 0..1


class Example(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class ProblemDetail(ProblemSummary):
    description: str
    constraints: str
    examples: list[Example]
    starter_code: dict[str, str]
    test_case_count: int
