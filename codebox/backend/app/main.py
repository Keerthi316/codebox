import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from .config import get_settings
from .database import SessionLocal, init_db
from .routes import ai, auth, executions, meta, problems, submissions
from .seed.problems import seed_problems

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("codebox")


def _init_with_retry(attempts: int = 30, delay: float = 2.0) -> None:
    """Create tables and seed problems, waiting for PostgreSQL to come up."""
    for attempt in range(1, attempts + 1):
        try:
            init_db()
            with SessionLocal() as db:
                seed_problems(db)
            return
        except OperationalError:
            if attempt == attempts:
                raise
            log.warning("Database not ready (attempt %d/%d); retrying", attempt, attempts)
            time.sleep(delay)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _init_with_retry()
    yield


settings = get_settings()
app = FastAPI(
    title="CodeBox API",
    version="1.0.0",
    description="Secure, Docker-sandboxed code execution with judging and an AI assistant.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(SQLAlchemyError)
async def database_error(_request: Request, exc: SQLAlchemyError):
    log.error("Database error: %s", exc)
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        content={"detail": "Database is unavailable; please try again shortly"})


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        content={"detail": "Internal server error"})


for router in (auth.router, problems.router, executions.router, submissions.router,
               ai.router, meta.router):
    app.include_router(router, prefix="/api/v1")
