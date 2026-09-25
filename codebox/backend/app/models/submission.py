import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base, utcnow


class Submission(Base):
    """A piece of code sent by a user, either a custom run (kind="run") or a
    judged submission against a problem's test cases (kind="submit")."""

    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    problem_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("problems.id", ondelete="SET NULL"), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(10), default="run")
    language: Mapped[str] = mapped_column(String(20))
    source_code: Mapped[str] = mapped_column(Text)
    stdin: Mapped[str] = mapped_column(Text, default="")
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compile_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True)
    execution_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # ms
    memory_used: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # KB
    passed_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_results: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem")
    execution = relationship("Execution", back_populates="submission", uselist=False,
                             cascade="all, delete-orphan")


class Execution(Base):
    """Lifecycle of the asynchronous job that runs a submission."""

    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True,
                                    default=lambda: str(uuid.uuid4()))
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submission = relationship("Submission", back_populates="execution")
