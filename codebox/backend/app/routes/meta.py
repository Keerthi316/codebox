from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from executor.languages import LANGUAGES

from ..config import get_settings
from ..database import get_db

router = APIRouter(tags=["meta"])


@router.get("/languages")
def languages():
    settings = get_settings()
    return {
        "languages": [
            {"key": lang.key, "name": lang.display_name, "monaco": lang.monaco_id,
             "time_limit_seconds": round(settings.execution_timeout * lang.time_factor, 2)}
            for lang in LANGUAGES.values()
        ],
        "limits": {"memory": settings.memory_limit, "cpus": settings.cpu_limit,
                   "timeout_seconds": settings.execution_timeout},
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    checks = {"database": "ok", "redis": "ok"}
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        checks["database"] = "unavailable"
    try:
        import redis

        redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=2).ping()
    except Exception:  # noqa: BLE001
        checks["redis"] = "unavailable"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse({"status": "ok" if healthy else "degraded", **checks},
                        status_code=200 if healthy else 503)
