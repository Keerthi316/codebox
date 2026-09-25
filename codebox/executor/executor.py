"""Trusted side of the sandbox: launches one throw-away container per job.

This module runs inside the Celery worker (which has Docker API access). It never
executes user code itself. Every untrusted container is created with:

* no network, read-only root filesystem, small tmpfs work dirs
* non-root user, all capabilities dropped, no-new-privileges, default seccomp
* memory (no swap), CPU, PID and open-file limits
* no bind mounts, no Docker socket, no host paths

Code and inputs are streamed over the container's stdin; the in-container runner
(executor/runner/runner.py) reports a single nonce-prefixed JSON line on stdout.
"""

import json
import logging
import os
import re
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional

import docker
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from docker.types import LogConfig, Ulimit
from docker.utils.socket import frames_iter

from .languages import Language, get_language
from .status import Status

log = logging.getLogger(__name__)

SANDBOX_LABEL = "codebox.sandbox"
SANDBOX_UID = "10001:10001"
MAX_RUNNER_OUTPUT = 32 * 1024 * 1024


class ExecutorError(Exception):
    """Infrastructure failure (Docker unavailable, image missing, sandbox crash).
    The message is safe to show to users."""


def parse_memory(value: str) -> int:
    """'128m' -> bytes. Accepts b/k/m/g suffixes (Docker style)."""
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([bkmg]?)b?\s*", str(value).lower())
    if not match:
        raise ValueError(f"invalid memory size: {value!r}")
    number, unit = match.groups()
    return int(float(number) * {"": 1, "b": 1, "k": 1 << 10, "m": 1 << 20, "g": 1 << 30}[unit])


@dataclass
class ExecutorConfig:
    timeout: float = 2.0
    memory_limit: str = "128m"
    cpu_limit: float = 0.5
    pids_limit: int = 64
    compile_timeout: float = 15.0
    compile_memory_limit: str = "512m"
    compile_cpu_limit: float = 1.0
    output_limit_bytes: int = 1024 * 1024
    file_size_limit_bytes: int = 2 * 1024 * 1024
    runtime: Optional[str] = None  # e.g. "runsc" for gVisor

    @classmethod
    def from_env(cls) -> "ExecutorConfig":
        env = os.environ.get
        return cls(
            timeout=float(env("EXECUTION_TIMEOUT", "2")),
            memory_limit=env("MEMORY_LIMIT", "128m"),
            cpu_limit=float(env("CPU_LIMIT", "0.5")),
            pids_limit=int(env("PIDS_LIMIT", "64")),
            compile_timeout=float(env("COMPILE_TIMEOUT", "15")),
            compile_memory_limit=env("COMPILE_MEMORY_LIMIT", "512m"),
            compile_cpu_limit=float(env("COMPILE_CPU_LIMIT", "1.0")),
            runtime=env("SANDBOX_RUNTIME") or None,
        )


@dataclass
class RunResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    time_ms: int = 0
    memory_kb: int = 0
    message: Optional[str] = None


@dataclass
class ExecutionOutcome:
    status: str
    runs: List[RunResult] = field(default_factory=list)
    compile_output: str = ""
    message: Optional[str] = None


_MLE_MARKERS = ("MemoryError", "java.lang.OutOfMemoryError",
                "JavaScript heap out of memory", "std::bad_alloc")


def classify_run(raw: dict, memory_limit_bytes: int) -> RunResult:
    stderr = raw.get("stderr", "")
    result = RunResult(
        status=Status.COMPLETED,
        stdout=raw.get("stdout", ""),
        stderr=stderr,
        exit_code=raw.get("exit_code"),
        time_ms=int(raw.get("time_ms") or 0),
        memory_kb=int(raw.get("memory_kb") or 0),
    )
    failed = result.exit_code != 0
    if raw.get("launch_error"):
        result.status, result.message = Status.RUNTIME_ERROR, "Program could not be started"
    elif raw.get("oom_killed") or (failed and any(m in stderr for m in _MLE_MARKERS)) \
            or result.memory_kb * 1024 > memory_limit_bytes:
        result.status, result.message = Status.MEMORY_LIMIT_EXCEEDED, "Memory limit exceeded"
    elif raw.get("timed_out"):
        result.status, result.message = Status.TIME_LIMIT_EXCEEDED, "Time limit exceeded"
    elif raw.get("file_size_exceeded"):
        result.status, result.message = Status.RUNTIME_ERROR, "Output limit exceeded"
    elif failed:
        result.status = Status.RUNTIME_ERROR
        if raw.get("signal"):
            result.message = f"Program terminated by signal {raw['signal']}"
        else:
            result.message = f"Program exited with code {result.exit_code}"
    if raw.get("output_truncated"):
        result.message = (result.message + "; " if result.message else "") + "output truncated"
    return result


class DockerExecutor:
    def __init__(self, config: Optional[ExecutorConfig] = None, client=None):
        self.config = config or ExecutorConfig.from_env()
        self._client = client

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = docker.from_env(timeout=30)
            except DockerException as exc:
                log.error("Docker unavailable: %s", exc)
                raise ExecutorError("Execution service unavailable: cannot reach Docker") from exc
        return self._client

    # ------------------------------------------------------------------ public

    def execute(self, language_key: str, source: str, inputs: List[str]) -> ExecutionOutcome:
        """Compile (if needed) and run `source` once per entry in `inputs`."""
        language = get_language(language_key)
        if language is None:
            return ExecutionOutcome(Status.FAILED, message=f"Unsupported language: {language_key}")
        inputs = list(inputs) or [""]
        layout = language.layout(source)
        files = {layout.filename: source}
        archive = None
        run_timeout = round(self.config.timeout * language.time_factor, 3)
        memory_bytes = parse_memory(self.config.memory_limit)

        try:
            if language.compile_cmd and language.separate_compile:
                compiled = self._run_container(
                    language,
                    payload={"files": files,
                             "compile": {"cmd": language.compile_cmd(layout.filename),
                                         "timeout": self.config.compile_timeout},
                             "collect": language.artifacts},
                    memory=self.config.compile_memory_limit,
                    cpus=self.config.compile_cpu_limit,
                    pids=max(self.config.pids_limit, 128),
                    deadline=self.config.compile_timeout + 20,
                )
                failure = self._compile_failure(compiled)
                if failure:
                    return failure
                files, archive = {}, compiled["archive"]
                payload = {"archive": archive}
            else:
                payload = {"files": files}
                if language.compile_cmd:
                    payload["compile"] = {"cmd": language.compile_cmd(layout.filename),
                                          "timeout": self.config.compile_timeout}

            payload.update({"run": {"cmd": layout.run_cmd, "timeout": run_timeout},
                            "inputs": inputs})
            result = self._run_container(
                language, payload=payload,
                memory=self.config.memory_limit, cpus=self.config.cpu_limit,
                pids=self.config.pids_limit,
                deadline=self.config.compile_timeout + len(inputs) * (run_timeout + 1) + 20,
            )
            failure = self._compile_failure(result)
            if failure:
                return failure
        except ExecutorError as exc:
            return ExecutionOutcome(Status.FAILED, message=str(exc))

        if result.get("oom_container"):
            return ExecutionOutcome(Status.MEMORY_LIMIT_EXCEEDED,
                                    runs=[RunResult(Status.MEMORY_LIMIT_EXCEEDED,
                                                    message="Memory limit exceeded")],
                                    message="Memory limit exceeded")
        runs = [classify_run(raw, memory_bytes) for raw in result.get("runs", [])]
        if len(runs) != len(inputs):
            return ExecutionOutcome(Status.FAILED, runs=runs,
                                    message="Sandbox did not report all results")
        worst = next((r.status for r in runs if r.status != Status.COMPLETED), Status.COMPLETED)
        return ExecutionOutcome(worst, runs=runs)

    def cleanup_stale_containers(self) -> int:
        """Remove sandbox containers left behind by a crashed worker."""
        removed = 0
        try:
            for container in self.client.containers.list(
                    all=True, filters={"label": f"{SANDBOX_LABEL}=1"}):
                try:
                    container.remove(force=True)
                    removed += 1
                except (APIError, NotFound):
                    pass
        except (DockerException, ExecutorError) as exc:
            log.warning("Stale sandbox cleanup failed: %s", exc)
        return removed

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except (DockerException, ExecutorError):
            return False

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _compile_failure(result: dict) -> Optional[ExecutionOutcome]:
        compiled = result.get("compile")
        if result.get("oom_container") and not result.get("runs"):
            return ExecutionOutcome(Status.COMPILATION_ERROR,
                                    message="Compiler ran out of memory")
        if not compiled or compiled.get("exit_code") == 0:
            return None
        if compiled.get("launch_error"):
            log.error("Compiler could not start: %s", compiled["launch_error"])
            return ExecutionOutcome(Status.FAILED, message="Compiler is not available")
        output = (compiled.get("stderr") or "") + (compiled.get("stdout") or "")
        if compiled.get("timed_out"):
            message = "Compilation timed out"
        elif compiled.get("oom_killed"):
            message = "Compiler ran out of memory"
        else:
            message = "Compilation failed"
        return ExecutionOutcome(Status.COMPILATION_ERROR, compile_output=output.strip(),
                                message=message)

    def _create_container(self, image: str, memory: str, cpus: float, pids: int) -> str:
        api = self.client.api
        host_config = api.create_host_config(
            network_mode="none",
            read_only=True,
            tmpfs={
                "/sandbox": "rw,exec,nosuid,nodev,size=64m,uid=10001,gid=10001,mode=0700",
                "/tmp": "rw,noexec,nosuid,nodev,size=64m,uid=10001,gid=10001,mode=0700",
            },
            mem_limit=memory,
            memswap_limit=memory,  # no swap
            nano_cpus=int(cpus * 1e9),
            pids_limit=pids,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            ulimits=[Ulimit(name="nofile", soft=256, hard=256)],
            ipc_mode="private",
            privileged=False,
            log_config=LogConfig(type="none"),
            runtime=self.config.runtime,
        )
        created = api.create_container(
            image,
            user=SANDBOX_UID,
            hostname="sandbox",
            labels={SANDBOX_LABEL: "1"},
            network_disabled=True,
            stdin_open=True,  # with detach=False docker-py also sets StdinOnce,
            detach=False,     # so the runner sees EOF once the payload is sent
            host_config=host_config,
        )
        return created["Id"]

    def _run_container(self, language: Language, payload: dict, memory: str,
                       cpus: float, pids: int, deadline: float) -> dict:
        nonce = secrets.token_hex(16)
        body = dict(payload, nonce=nonce,
                    memory_limit_bytes=parse_memory(memory),
                    output_limit_bytes=self.config.output_limit_bytes,
                    file_size_limit_bytes=self.config.file_size_limit_bytes)
        data = json.dumps(body).encode("utf-8")

        api = self.client.api
        container = None
        try:
            try:
                container = self._create_container(language.image, memory, cpus, pids)
            except ImageNotFound as exc:
                raise ExecutorError(
                    f"Sandbox image {language.image} is missing; build the sandbox images") from exc

            sock = api.attach_socket(
                container, params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1})
            raw_sock = getattr(sock, "_sock", sock)
            killer = threading.Timer(deadline, self._kill, args=(container,))
            try:
                api.start(container)
                killer.start()
                raw_sock.settimeout(deadline + 5)
                raw_sock.sendall(data)
                raw_sock.shutdown(socket.SHUT_WR)
                stdout = bytearray()
                runner_stderr = bytearray()
                for stream, chunk in frames_iter(sock, tty=False):
                    if stream == 1 and len(stdout) < MAX_RUNNER_OUTPUT:
                        stdout.extend(chunk)
                    elif stream == 2 and len(runner_stderr) < 65536:
                        runner_stderr.extend(chunk)
            finally:
                killer.cancel()
                try:
                    sock.close()
                except OSError:
                    pass

            state = self._wait(api, container)
            text = stdout.decode("utf-8", errors="replace")
            marker = text.rfind(nonce)
            if marker != -1:
                result = json.loads(text[marker + len(nonce):].splitlines()[0])
                if result.get("error"):
                    log.error("Sandbox runner error: %s", result["error"])
                    raise ExecutorError("Sandbox error while preparing the program")
                return result
            if state.get("OOMKilled"):
                return {"oom_container": True, "runs": []}
            log.error("Sandbox produced no result (state=%s, stderr=%s)",
                      state, runner_stderr[:2000].decode("utf-8", "replace"))
            raise ExecutorError("Sandbox terminated unexpectedly")
        except (socket.timeout, TimeoutError) as exc:
            raise ExecutorError("Sandbox did not respond in time") from exc
        except (APIError, DockerException, OSError, ValueError) as exc:
            log.exception("Sandbox execution failed")
            raise ExecutorError("Execution service error") from exc
        finally:
            if container is not None:
                try:
                    api.remove_container(container, force=True)
                except (APIError, NotFound, DockerException):
                    log.warning("Failed to remove sandbox container %s", container)

    def _kill(self, container: str) -> None:
        try:
            self.client.api.kill(container)
        except (APIError, NotFound):
            pass

    @staticmethod
    def _wait(api, container: str) -> dict:
        try:
            api.wait(container, timeout=10)
            return api.inspect_container(container).get("State", {})
        except Exception:  # noqa: BLE001 - state is best-effort diagnostics
            return {}
