"""In-sandbox runner. Baked into every language image as /opt/codebox/runner.py.

It runs as PID 1 of an untrusted, network-less, read-only container, as an
unprivileged user. The trusted worker streams a single JSON payload over the
container's stdin:

    {
      "nonce": "<random hex>",          # echoed back to authenticate the result line
      "files": {"main.py": "<text>"},   # source files written into the work dir
      "archive": "<base64 tar.gz>",     # optional prebuilt artifacts (from a compile container)
      "compile": {"cmd": [...], "timeout": 10},       # optional; failure => compile error
      "run": {"cmd": [...], "timeout": 2.0},          # optional
      "inputs": ["stdin for test 1", ...],            # program is run once per input
      "collect": ["*.class"],                         # optional; globs returned as base64 tar.gz
      "memory_limit_bytes": 134217728,
      "output_limit_bytes": 65536,
      "file_size_limit_bytes": 1048576
    }

It prints exactly one line to stdout: "<nonce><json result>". Nothing produced by
the untrusted program is ever written to the runner's own stdout; program output
goes to files on the tmpfs and is read back (truncated) by the runner.

Expected outputs never enter the sandbox; the trusted worker does all judging.
Standard library only, Python 3.9+ compatible.
"""

import base64
import ctypes
import glob
import io
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time

WORK_DIR = "/sandbox"
CGROUP_EVENTS = "/sys/fs/cgroup/memory.events"
CHILD_ENV = {
    # PATH comes from the (trusted) image, e.g. the JDK lives in /opt/java/openjdk/bin
    "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
    "HOME": "/tmp",
    "TMPDIR": "/tmp",
    "LANG": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONUNBUFFERED": "1",
    "PYTHONHASHSEED": "0",
}


def make_non_dumpable():
    """Hide /proc/1/* (fds, environ, memory) from the same-uid user program."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE = 4
    except Exception:
        pass


def oom_kills():
    try:
        with open(CGROUP_EVENTS) as f:
            for line in f:
                key, _, value = line.partition(" ")
                if key == "oom_kill":
                    return int(value)
    except (OSError, ValueError):
        pass
    return 0


def status_kb(pid, field):
    """Read a kB field (VmRSS, VmHWM) from /proc/<pid>/status; 0 if unavailable."""
    try:
        with open("/proc/%s/status" % pid) as f:
            for line in f:
                if line.startswith(field + ":"):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return 0


class PeakMemoryMonitor(threading.Thread):
    """Polls the program's VmHWM. Needed because ru_maxrss also counts the
    runner's memory that the child inherited from fork() before exec()."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.pid = pid
        self.peak_kb = 0
        self.stop = threading.Event()

    def run(self):
        while True:
            self.peak_kb = max(self.peak_kb, status_kb(self.pid, "VmHWM"))
            if self.stop.wait(0.01):
                break


def read_capped(path, limit):
    try:
        with open(path, "rb") as f:
            data = f.read(limit + 1)
    except OSError:
        return "", False
    truncated = len(data) > limit
    return data[:limit].decode("utf-8", errors="replace"), truncated


def run_process(cmd, stdin_data, timeout, cpu_seconds, fsize, output_limit, tag):
    """Run one command with rlimits and a wall-clock timeout. Never raises."""
    in_path = os.path.join("/tmp", tag + ".in")
    out_path = os.path.join("/tmp", tag + ".out")
    err_path = os.path.join("/tmp", tag + ".err")
    with open(in_path, "wb") as f:
        f.write(stdin_data.encode("utf-8"))

    def preexec():
        os.setsid()
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
        try:  # make the user program the OOM killer's preferred victim
            with open("/proc/self/oom_score_adj", "w") as f:
                f.write("1000")
        except OSError:
            pass

    oom_before = oom_kills()
    runner_rss_kb = status_kb("self", "VmRSS")
    timed_out = threading.Event()
    with open(in_path, "rb") as fin, open(out_path, "wb") as fout, open(err_path, "wb") as ferr:
        start = time.monotonic()
        try:
            proc = subprocess.Popen(
                cmd, stdin=fin, stdout=fout, stderr=ferr, cwd=WORK_DIR,
                env=CHILD_ENV, close_fds=True, preexec_fn=preexec,
            )
        except OSError as exc:
            return {"exit_code": None, "signal": None, "timed_out": False, "oom_killed": False,
                    "time_ms": 0, "memory_kb": 0, "stdout": "", "stderr": "",
                    "output_truncated": False, "file_size_exceeded": False,
                    "launch_error": str(exc)}

        def kill():
            timed_out.set()
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass

        timer = threading.Timer(timeout, kill)
        timer.start()
        monitor = PeakMemoryMonitor(proc.pid)
        monitor.peak_kb = status_kb(proc.pid, "VmHWM")  # sample very short programs too
        monitor.start()
        try:
            _, status, usage = os.wait4(proc.pid, 0)
        finally:
            timer.cancel()
            monitor.stop.set()
            monitor.join()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        kill_leftovers(proc.pid)

    stdout, out_trunc = read_capped(out_path, output_limit)
    stderr, err_trunc = read_capped(err_path, output_limit)
    sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
    return {
        "exit_code": os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
        "signal": sig,
        "timed_out": timed_out.is_set() or sig == signal.SIGXCPU,
        "oom_killed": oom_kills() > oom_before,
        "time_ms": elapsed_ms,
        # ru_maxrss is exact once it exceeds what fork() inherited from the runner
        "memory_kb": int(usage.ru_maxrss) if usage.ru_maxrss > runner_rss_kb * 1.05
        else monitor.peak_kb or int(usage.ru_maxrss),
        "stdout": stdout,
        "stderr": stderr,
        "output_truncated": out_trunc or err_trunc,
        "file_size_exceeded": sig == signal.SIGXFSZ,
        "launch_error": None,
    }


def kill_leftovers(pgid):
    """Kill everything the program left behind, including processes that escaped
    its session via setsid(). As PID 1 of the container's PID namespace,
    kill(-1) reaches every other process there while sparing the runner."""
    if os.getpid() == 1:
        try:
            os.kill(-1, signal.SIGKILL)
        except OSError:
            pass
    try:
        os.killpg(pgid, signal.SIGKILL)
    except OSError:
        pass
    while True:  # reap zombies re-parented to us
        try:
            if os.waitpid(-1, os.WNOHANG) == (0, 0):
                break
        except ChildProcessError:
            break


def wipe_tmp():
    """Give every test case a clean /tmp so runs cannot pass state to each other."""
    for name in os.listdir("/tmp"):
        path = os.path.join("/tmp", name)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                os.unlink(path)
        except OSError:
            pass


def collect_archive(patterns):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for pattern in patterns:
            for path in sorted(glob.glob(os.path.join(WORK_DIR, pattern))):
                if os.path.isfile(path) and not os.path.islink(path):
                    tar.add(path, arcname=os.path.relpath(path, WORK_DIR))
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_archive(data):
    with tarfile.open(fileobj=io.BytesIO(base64.b64decode(data)), mode="r:gz") as tar:
        for member in tar.getmembers():
            # only plain files/dirs with safe relative names
            if member.name.startswith("/") or ".." in member.name.split("/"):
                continue
            if not (member.isfile() or member.isdir()):
                continue
            tar.extract(member, WORK_DIR)


def main():
    make_non_dumpable()
    raw = sys.stdin.buffer.read()
    payload = json.loads(raw.decode("utf-8"))
    nonce = payload["nonce"]
    result = {"compile": None, "runs": [], "archive": None, "error": None}
    try:
        os.chdir(WORK_DIR)
        for name, content in (payload.get("files") or {}).items():
            if "/" in name or name.startswith("."):
                raise ValueError("invalid file name")
            with open(os.path.join(WORK_DIR, name), "w", encoding="utf-8") as f:
                f.write(content)
        if payload.get("archive"):
            extract_archive(payload["archive"])

        fsize = int(payload.get("file_size_limit_bytes", 1 << 20))
        out_limit = int(payload.get("output_limit_bytes", 1 << 16))

        step = payload.get("compile")
        if step:
            timeout = float(step["timeout"])
            res = run_process(step["cmd"], "", timeout, int(timeout) + 1,
                              max(fsize, 64 << 20), out_limit, "compile")
            result["compile"] = res
            if res["exit_code"] != 0:
                raise SystemExit  # compile failed; skip run/collect

        if payload.get("collect"):
            result["archive"] = collect_archive(payload["collect"])

        step = payload.get("run")
        if step:
            timeout = float(step["timeout"])
            for i, stdin_data in enumerate(payload.get("inputs") or [""]):
                wipe_tmp()
                result["runs"].append(run_process(
                    step["cmd"], stdin_data, timeout, int(timeout) + 1,
                    fsize, out_limit, "run%d" % i))
    except SystemExit:
        pass
    except Exception as exc:  # report infrastructure problems, never crash silently
        result["error"] = "%s: %s" % (type(exc).__name__, exc)

    sys.stdout.write(nonce + json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
