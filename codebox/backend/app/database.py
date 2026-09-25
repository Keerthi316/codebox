from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_engine(url: str):
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=10)


engine = _make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401 - register tables

    Base.metadata.create_all(bind=engine)
    # Email-code verification was removed; drop its leftovers from older databases.
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS email_verifications"))
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS email_verified"))
            # create_all never alters existing tables; add columns introduced later.
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS tags JSON NOT NULL DEFAULT '[]'"))
