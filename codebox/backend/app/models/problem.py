from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)  # Markdown
    difficulty: Mapped[str] = mapped_column(String(10))  # Easy | Medium | Hard
    tags: Mapped[list] = mapped_column(JSON, default=list)  # topics, e.g. ["Array", "Hash Table"]
    constraints: Mapped[str] = mapped_column(Text, default="")
    examples: Mapped[list] = mapped_column(JSON, default=list)
    starter_code: Mapped[dict] = mapped_column(JSON, default=dict)  # language -> code
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    test_cases = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan",
                              order_by="TestCase.position")


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False  # not a pytest class

    id: Mapped[int] = mapped_column(primary_key=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    input: Mapped[str] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text)
    # Sample cases are also shown in the problem statement; everything else is hidden.
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False)

    problem = relationship("Problem", back_populates="test_cases")
