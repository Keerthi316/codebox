# CodeBox sandbox: C++. Build context: executor/
FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends g++ libc6-dev python3 \
 && rm -rf /var/lib/apt/lists/*

# Unprivileged sandbox user; the worker also forces --user 10001:10001 at run time.
RUN groupadd --system --gid 10001 sandbox \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin sandbox \
 && mkdir -p /sandbox /opt/codebox \
 && chown sandbox:sandbox /sandbox \
 && find / -xdev -perm /6000 -type f -exec chmod a-s {} + 2>/dev/null || true

COPY runner/runner.py /opt/codebox/runner.py
WORKDIR /sandbox
USER 10001:10001
ENTRYPOINT ["python3", "-I", "/opt/codebox/runner.py"]
