# CodeBox API + Celery worker image. Build context: repository root.
FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/srv

WORKDIR /srv
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/app ./app
COPY executor ./executor
COPY ai ./ai

RUN groupadd --system --gid 10002 codebox \
 && useradd --system --uid 10002 --gid 10002 --no-create-home codebox

# The API runs unprivileged. The worker overrides the user in docker-compose.yml
# because it needs the Docker socket (see README "Docker architecture").
USER codebox
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

# ---------------------------------------------------------------------------
# Test image: `docker compose --profile test run --rm tests`
FROM base AS test
USER root
COPY backend/requirements-dev.txt backend/requirements-dev.txt
RUN pip install -r backend/requirements-dev.txt
COPY tests ./tests
COPY pytest.ini ./pytest.ini
RUN sed -i 's/^pythonpath = backend ./pythonpath = . /' pytest.ini
CMD ["pytest", "-q"]
