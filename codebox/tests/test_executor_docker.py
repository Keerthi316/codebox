"""Integration tests against a real Docker daemon and the built sandbox images.

Skipped automatically when Docker or the images are unavailable.
Build images first:  docker compose build   (or see README)
"""

from types import SimpleNamespace

import pytest

from app.seed.problems import PROBLEMS, all_tests
from app.services.judge import judge
from executor.executor import SANDBOX_LABEL, DockerExecutor, ExecutorConfig
from executor.languages import LANGUAGES
from executor.status import Status
from solutions import solution

pytestmark = pytest.mark.docker


def _docker_ready():
    try:
        import docker

        client = docker.from_env(timeout=5)
        client.ping()
        return all(_has_image(client, lang.image) for lang in LANGUAGES.values())
    except Exception:  # noqa: BLE001
        return False


def _has_image(client, image):
    try:
        client.images.get(image)
        return True
    except Exception:  # noqa: BLE001
        return False


if not _docker_ready():
    pytest.skip("Docker daemon or sandbox images unavailable", allow_module_level=True)


@pytest.fixture(scope="module")
def executor():
    return DockerExecutor(ExecutorConfig(timeout=2, memory_limit="128m", cpu_limit=0.5))


def run1(executor, language, code, stdin=""):
    outcome = executor.execute(language, code, [stdin])
    return outcome, (outcome.runs[0] if outcome.runs else None)


HELLO = {
    "python": "import sys\nname = sys.stdin.read().strip()\nprint(f'Hello, {name}!')",
    "javascript": "const n = require('fs').readFileSync(0, 'utf8').trim();\nconsole.log(`Hello, ${n}!`);",
    "java": "import java.util.*;\npublic class Main { public static void main(String[] a) {\n"
            "  String n = new Scanner(System.in).nextLine().trim();\n"
            "  System.out.println(\"Hello, \" + n + \"!\"); } }",
    "cpp": "#include <iostream>\n#include <string>\nint main(){ std::string n; std::getline(std::cin, n);"
           " std::cout << \"Hello, \" << n << \"!\" << std::endl; }",
}


# ------------------------------------------------------------------ basics

@pytest.mark.parametrize("language", sorted(LANGUAGES))
def test_hello_world_with_stdin(executor, language):
    outcome, run = run1(executor, language, HELLO[language], "CodeBox\n")
    assert outcome.status == Status.COMPLETED, (outcome, run)
    assert run.stdout.strip() == "Hello, CodeBox!"
    assert run.time_ms > 0 and run.memory_kb > 0


def test_multiple_inputs_reuse_one_build(executor):
    outcome = executor.execute("cpp", "#include <iostream>\nint main(){int a,b;std::cin>>a>>b;std::cout<<a*b;}",
                               ["2 3", "4 5", "-1 9"])
    assert [r.stdout for r in outcome.runs] == ["6", "20", "-9"]


# ------------------------------------------------------------------ failures

@pytest.mark.parametrize("language,code", [
    ("python", "def broken(:\n  pass"),
    ("javascript", "function (){"),
    ("java", "public class Main { void f() { int x = } }"),
    ("cpp", "int main() { return undefined_symbol; }"),
])
def test_compilation_errors(executor, language, code):
    outcome = executor.execute(language, code, [""])
    assert outcome.status == Status.COMPILATION_ERROR
    assert outcome.compile_output


@pytest.mark.parametrize("language,code", [
    ("python", "print(1 // 0)"),
    ("javascript", "null.x"),
    ("java", "public class Main { public static void main(String[] a) { int[] x = new int[1]; x[5] = 1; } }"),
    ("cpp", "#include <cstdlib>\nint main(){ std::abort(); }"),
])
def test_runtime_errors(executor, language, code):
    outcome, run = run1(executor, language, code)
    assert outcome.status == Status.RUNTIME_ERROR
    assert run.exit_code != 0


@pytest.mark.parametrize("language,code", [
    ("python", "while True:\n    pass"),
    ("javascript", "while (true) {}"),
    ("java", "public class Main { public static void main(String[] a) { while (true) {} } }"),
    ("cpp", "int main(){ volatile int x = 0; while (true) { x++; } }"),
    ("python", "import time\ntime.sleep(30)"),  # wall-clock, not just CPU
])
def test_time_limit(executor, language, code):
    outcome, run = run1(executor, language, code)
    assert outcome.status == Status.TIME_LIMIT_EXCEEDED
    assert run.time_ms < 8000


@pytest.mark.parametrize("language,code", [
    ("python", "x = bytearray(512 * 1024 * 1024)\nprint(len(x))"),
    ("python", "chunks = []\nwhile True:\n    chunks.append(bytearray(8 * 1024 * 1024))"),
    ("javascript", "const a = []; while (true) a.push(new Array(1e6).fill(1.5));"),
    ("java", "import java.util.*;\npublic class Main { public static void main(String[] a) {"
             " List<long[]> l = new ArrayList<>(); while (true) l.add(new long[1_000_000]); } }"),
    ("cpp", "#include <vector>\n#include <cstring>\nint main(){ std::vector<char*> v;"
            " while(true){ char* p = new char[16<<20]; std::memset(p, 1, 16<<20); v.push_back(p);} }"),
])
def test_memory_limit(executor, language, code):
    outcome, _ = run1(executor, language, code)
    assert outcome.status == Status.MEMORY_LIMIT_EXCEEDED


def test_output_flood_is_limited(executor):
    outcome, run = run1(executor, "python", "while True:\n    print('A' * 1000)")
    assert outcome.status in (Status.RUNTIME_ERROR, Status.TIME_LIMIT_EXCEEDED)
    assert len(run.stdout) <= executor.config.output_limit_bytes


# ------------------------------------------------------------------ isolation

def test_runs_as_non_root_without_capabilities(executor):
    code = ("import os\nprint(os.getuid(), os.getgid())\n"
            "print([l for l in open('/proc/self/status') if l.startswith('CapEff')][0].split()[1])\n"
            "print([l for l in open('/proc/self/status') if l.startswith('NoNewPrivs')][0].split()[1])")
    _, run = run1(executor, "python", code)
    uid_gid, cap_eff, no_new_privs = run.stdout.split("\n")[:3]
    assert uid_gid == "10001 10001"
    assert int(cap_eff, 16) == 0
    assert no_new_privs == "1"


def test_no_network(executor):
    code = ("import socket\ntry:\n    socket.create_connection(('1.1.1.1', 53), timeout=1)\n    print('CONNECTED')\n"
            "except OSError as e:\n    print('BLOCKED')\n"
            "import os\nprint(sorted(os.listdir('/sys/class/net')))")
    _, run = run1(executor, "python", code)
    lines = run.stdout.split()
    assert lines[0] == "BLOCKED"
    assert "eth0" not in run.stdout


def test_read_only_root_and_writable_tmp(executor):
    code = ("import os\nfor p in ['/etc/x', '/usr/x', '/opt/codebox/runner.py', '/x']:\n"
            "    try:\n        open(p, 'w'); print('WROTE', p)\n    except OSError:\n        print('DENIED')\n"
            "open('/tmp/scratch', 'w').write('ok'); print(open('/tmp/scratch').read())")
    _, run = run1(executor, "python", code)
    assert run.stdout.split() == ["DENIED"] * 4 + ["ok"]


def test_no_docker_socket_or_host_files(executor):
    code = ("import os\nprint(os.path.exists('/var/run/docker.sock'), os.path.exists('/run/docker.sock'))\n"
            "print(sorted(os.listdir('/sandbox')))")
    _, run = run1(executor, "python", code)
    first, second = run.stdout.split("\n")[:2]
    assert first == "False False"
    # only the submitted code (plus the syntax check's bytecode cache)
    assert second in ("['main.py']", "['__pycache__', 'main.py']")


def test_runner_process_is_protected(executor):
    """The user program cannot read the runner's memory/fds (PR_SET_DUMPABLE=0)."""
    code = ("import os\nfor p in ['/proc/1/environ', '/proc/1/fd/1']:\n"
            "    try:\n        open(p, 'rb').read(1); print('OPEN')\n    except OSError:\n        print('DENIED')")
    _, run = run1(executor, "python", code)
    assert run.stdout.split() == ["DENIED", "DENIED"]


def test_fork_bomb_is_contained(executor):
    code = "import os\nwhile True:\n    try:\n        os.fork()\n    except OSError:\n        pass"
    outcome, _ = run1(executor, "python", code)
    assert outcome.status in (Status.TIME_LIMIT_EXCEEDED, Status.RUNTIME_ERROR,
                              Status.MEMORY_LIMIT_EXCEEDED)
    # the executor is still healthy afterwards
    assert executor.execute("python", "print(42)", [""]).runs[0].stdout == "42\n"


def test_background_process_cannot_outlive_its_test(executor):
    """A daemonised child (setsid) is killed when the program exits."""
    code = ("import os, sys, time\n"
            "if sys.stdin.read().strip() == '1':\n"
            "    if os.fork() == 0:\n        os.setsid()\n        time.sleep(0.5)\n"
            "        open('/sandbox/leak', 'w').write('x')\n        os._exit(0)\n"
            "    print('spawned')\n"
            "else:\n    time.sleep(1)\n    print(os.path.exists('/sandbox/leak'))")
    outcome = executor.execute("python", code, ["1", "2"])
    assert [r.stdout.strip() for r in outcome.runs] == ["spawned", "False"]


def test_tmp_is_wiped_between_test_cases(executor):
    code = ("import os, sys\nif sys.stdin.read().strip() == '1':\n"
            "    open('/tmp/state', 'w').write('x')\n"
            "print(os.path.exists('/tmp/state'))")
    outcome = executor.execute("python", code, ["1", "2"])
    assert [r.stdout.strip() for r in outcome.runs] == ["True", "False"]


def test_containers_are_removed(executor):
    executor.execute("python", "print(1)", [""])
    executor.execute("python", "while True: pass", [""])
    leftovers = executor.client.containers.list(all=True, filters={"label": f"{SANDBOX_LABEL}=1"})
    assert leftovers == []


def test_resource_limits_applied(executor, monkeypatch):
    captured = {}
    original = executor._create_container

    def spy(image, memory, cpus, pids):
        container_id = original(image, memory, cpus, pids)
        captured.update(executor.client.api.inspect_container(container_id)["HostConfig"])
        return container_id

    monkeypatch.setattr(executor, "_create_container", spy)
    executor.execute("python", "print(1)", [""])
    assert captured["Memory"] == 128 * 1024 * 1024
    assert captured["MemorySwap"] == captured["Memory"]
    assert captured["NanoCpus"] == 500_000_000
    assert captured["PidsLimit"] == 64
    assert captured["ReadonlyRootfs"] is True
    assert captured["NetworkMode"] == "none"
    assert captured["Privileged"] is False
    assert captured["CapDrop"] == ["ALL"]
    assert "no-new-privileges:true" in captured["SecurityOpt"]
    assert not captured.get("Binds") and not captured.get("Mounts")


# ------------------------------------------------------------------ judge E2E

@pytest.mark.parametrize("language", sorted(LANGUAGES))
@pytest.mark.parametrize("slug", [p["slug"] for p in PROBLEMS])
def test_reference_solutions_pass_hidden_tests(executor, slug, language):
    spec = next(p for p in PROBLEMS if p["slug"] == slug)
    tests = [SimpleNamespace(input=i, expected_output=spec["solver"](i) + "\n", is_sample=n == 0)
             for n, i in enumerate(all_tests()[slug])]
    outcome = executor.execute(language, solution(slug, language), [t.input for t in tests])
    verdict = judge(outcome, tests)
    assert verdict.status == Status.ACCEPTED, (verdict, outcome.compile_output, outcome.message)
    assert verdict.passed == verdict.total == len(tests)


@pytest.mark.parametrize("language", sorted(LANGUAGES))
def test_unmodified_starter_code_compiles_and_fails(executor, language):
    from app.seed.problems import STARTER_CODE

    spec = PROBLEMS[0]
    tests = [SimpleNamespace(input=i, expected_output=spec["solver"](i) + "\n", is_sample=False)
             for i in all_tests()[spec["slug"]]]
    outcome = executor.execute(language, STARTER_CODE[spec["slug"]][language], [t.input for t in tests])
    assert judge(outcome, tests).status == Status.WRONG_ANSWER
