# CodeBox sandbox: Java. Build context: executor/
FROM eclipse-temurin:21-jdk-noble

# python3 is needed only for the sandbox runner, not for user code
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 \
 && rm -rf /var/lib/apt/lists/*

# Class data sharing archive speeds up JVM start-up under tight CPU limits
RUN java -Xshare:dump >/dev/null 2>&1 || true

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
