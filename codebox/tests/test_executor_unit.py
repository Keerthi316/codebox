"""Executor logic that doesn't need Docker."""

import pytest
from docker.errors import DockerException, ImageNotFound

from executor.executor import (DockerExecutor, ExecutorConfig, ExecutorError, classify_run,
                               parse_memory)
from executor.languages import LANGUAGES, get_language
from executor.status import Status

MB = 1 << 20


def _raw(**kw):
    base = {"exit_code": 0, "signal": None, "timed_out": False, "oom_killed": False,
            "time_ms": 5, "memory_kb": 1000, "stdout": "ok", "stderr": "",
            "output_truncated": False, "file_size_exceeded": False, "launch_error": None}
    base.update(kw)
    return base


@pytest.mark.parametrize("value,expected", [
    ("128m", 128 * MB), ("1g", 1 << 30), ("512k", 512 * 1024), ("64MB", 64 * MB), ("1000", 1000)])
def test_parse_memory(value, expected):
    assert parse_memory(value) == expected


def test_parse_memory_rejects_garbage():
    with pytest.raises(ValueError):
        parse_memory("lots")


@pytest.mark.parametrize("raw,status", [
    (_raw(), Status.COMPLETED),
    (_raw(exit_code=1, stderr="Traceback"), Status.RUNTIME_ERROR),
    (_raw(exit_code=None, signal=11), Status.RUNTIME_ERROR),
    (_raw(exit_code=None, signal=9, timed_out=True), Status.TIME_LIMIT_EXCEEDED),
    (_raw(exit_code=None, signal=9, oom_killed=True), Status.MEMORY_LIMIT_EXCEEDED),
    (_raw(exit_code=1, stderr="MemoryError"), Status.MEMORY_LIMIT_EXCEEDED),
    (_raw(exit_code=1, stderr="Exception in thread \"main\" java.lang.OutOfMemoryError"), Status.MEMORY_LIMIT_EXCEEDED),
    (_raw(exit_code=134, stderr="terminate called after throwing an instance of 'std::bad_alloc'"), Status.MEMORY_LIMIT_EXCEEDED),
    (_raw(exit_code=None, signal=25, file_size_exceeded=True), Status.RUNTIME_ERROR),
    (_raw(exit_code=None, launch_error="ENOENT"), Status.RUNTIME_ERROR),
    (_raw(memory_kb=200 * 1024), Status.MEMORY_LIMIT_EXCEEDED),
])
def test_classify_run(raw, status):
    assert classify_run(raw, 128 * MB).status == status


def test_classify_run_messages():
    assert classify_run(_raw(exit_code=None, signal=25, file_size_exceeded=True), 128 * MB).message == "Output limit exceeded"
    assert "truncated" in classify_run(_raw(output_truncated=True), 128 * MB).message
    # printing "MemoryError" in a successful program is not an MLE
    assert classify_run(_raw(stderr="MemoryError"), 128 * MB).status == Status.COMPLETED


def test_language_registry():
    assert set(LANGUAGES) == {"python", "javascript", "java", "cpp"}
    assert get_language("CPP").key == "cpp"
    assert get_language("cobol") is None and get_language(None) is None
    for lang in LANGUAGES.values():
        assert lang.image.startswith("codebox-sandbox-")


def test_java_layout_follows_public_class():
    java = get_language("java")
    assert java.layout("public class Solution { }").filename == "Solution.java"
    assert java.layout("public final class Foo {}").run_cmd[-1] == "Foo"
    assert java.layout("class Main {}").filename == "Main.java"


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("EXECUTION_TIMEOUT", "3.5")
    monkeypatch.setenv("MEMORY_LIMIT", "256m")
    monkeypatch.setenv("CPU_LIMIT", "1")
    monkeypatch.setenv("SANDBOX_RUNTIME", "runsc")
    config = ExecutorConfig.from_env()
    assert (config.timeout, config.memory_limit, config.cpu_limit, config.runtime) == (3.5, "256m", 1.0, "runsc")


def test_unsupported_language_fails_cleanly():
    outcome = DockerExecutor(ExecutorConfig(), client=object()).execute("cobol", "x", [""])
    assert outcome.status == Status.FAILED and "Unsupported" in outcome.message


class _BrokenApi:
    def create_host_config(self, **kwargs):
        return kwargs

    def create_container(self, *args, **kwargs):
        raise self.error


def test_missing_image_and_docker_failure_are_reported():
    api = _BrokenApi()
    client = type("C", (), {"api": api})()
    executor = DockerExecutor(ExecutorConfig(), client=client)
    api.error = ImageNotFound("nope")
    outcome = executor.execute("python", "print(1)", [""])
    assert outcome.status == Status.FAILED and "image" in outcome.message
    api.error = DockerException("daemon gone")
    outcome = executor.execute("python", "print(1)", [""])
    assert outcome.status == Status.FAILED and outcome.message == "Execution service error"


def test_unreachable_docker(monkeypatch):
    import docker

    def boom(**_kw):
        raise DockerException("no socket")

    monkeypatch.setattr(docker, "from_env", boom)
    executor = DockerExecutor(ExecutorConfig())
    with pytest.raises(ExecutorError):
        _ = executor.client
    assert executor.execute("python", "print(1)", [""]).status == Status.FAILED
    assert executor.ping() is False
