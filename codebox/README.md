# CodeBox: AI-Powered Docker Code Execution Sandbox

CodeBox is a self-hosted coding platform, like a small LeetCode or HackerRank. Users write code in a browser editor, run it with their own input, and submit it against hidden test cases. They can also ask an AI assistant to explain, debug or optimise their code.

Every piece of user code runs in a **fresh, locked-down Docker container** that is destroyed afterwards. User code never runs on the host or inside the application's own containers.

```
User → React (Monaco) → FastAPI → Redis → Celery worker → Docker sandbox → result → PostgreSQL → UI
```

---

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Directory structure](#directory-structure)
- [Docker architecture](#docker-architecture)
- [Sandbox and security model](#sandbox-and-security-model)
- [API](#api)
- [Environment variables](#environment-variables)
- [Quick start (Docker Compose)](#quick-start-docker-compose)
- [Windows and Docker Desktop setup](#windows-and-docker-desktop-setup)
- [Local development without Compose](#local-development-without-compose)
- [Testing](#testing)
- [Adding a new language](#adding-a-new-language)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)

---

## Features

| Area | What you get |
| --- | --- |
| **Accounts** | Registration with email checks (the domain must have a mail server, Gmail's username rules are enforced, typos like `gmal.co` get a "did you mean" suggestion, throwaway inboxes are blocked), login by username or email, JWT auth, bcrypt password hashing, per-user data isolation, rate limiting on login |
| **Editor** | Monaco editor bundled locally (no CDN), syntax highlighting, per-problem/per-language drafts, <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to run, resizable panes, responsive layout |
| **Languages** | Python 3.12, JavaScript (Node.js 22), Java 21, C++17 (GCC), each in its own image |
| **Run** | Run code with custom stdin and see stdout, stderr, compiler output, runtime and peak memory |
| **Submit** | Judge against all test cases. Shows `Passed 4/5` with ✓/✗ per case. Hidden cases never reveal their input or expected output |
| **Statuses** | `QUEUED`, `RUNNING`, `COMPLETED`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `COMPILATION_ERROR`, `RUNTIME_ERROR`, `FAILED`, plus the judged verdicts `ACCEPTED` and `WRONG_ANSWER` |
| **Problems** | 15 problems (9 Easy, 4 Medium, 2 Hard), e.g. Two Sum, Valid Parentheses, Number of Islands, Coin Change, Trapping Rain Water, Edit Distance. Each has topic tags, a statement, constraints, examples, starter code in 4 languages, and 5–8 test cases (large hidden ones included). The Problems page shows your progress per difficulty, a "next up" suggestion, search and difficulty/status/topic filters, and community acceptance rates |
| **History** | Dashboard of runs and submissions (problem, language, status, runtime, memory, time) with a detail view showing code, input, output, errors and test results |
| **AI assistant** | CodeExplainer, Debugger, ComplexityAnalyzer and Optimizer, chosen by a simple router. Works with OpenRouter (first-class) or any OpenAI-compatible API. If it isn't configured, the app keeps working and the assistant panel says so |
| **Resilience** | Clear errors, never stack traces, when Docker, PostgreSQL, Redis, the worker or the AI provider fails |

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser
        UI["React + Monaco<br/>(Vite build)"]
    end

    subgraph web["network: web"]
        FE["frontend<br/>nginx (unprivileged)<br/>static SPA + /api proxy"]
        BE["backend<br/>FastAPI (non-root)<br/>auth · problems · judge API · AI"]
    end

    subgraph data["network: data (internal, no internet)"]
        PG[("PostgreSQL")]
        RD[("Redis<br/>Celery broker")]
        WK["celery-worker<br/>(trusted, Docker API access)"]
    end

    subgraph host["Host Docker daemon"]
        SB1["sandbox container<br/>codebox-sandbox-python"]
        SB2["sandbox container<br/>codebox-sandbox-java …"]
    end

    LLM["OpenAI-compatible<br/>LLM API"]

    UI -->|HTTP| FE -->|/api| BE
    BE --> PG
    BE -->|enqueue job id| RD
    RD --> WK
    WK --> PG
    WK -->|/var/run/docker.sock| host
    host --- SB1 & SB2
    BE -.->|optional| LLM
```

### Execution flow

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser
    participant A as FastAPI
    participant D as PostgreSQL
    participant R as Redis
    participant W as Celery worker
    participant S as Sandbox container

    U->>A: POST /api/v1/execute (language, code, stdin)
    A->>A: validate language, size limits, rate limits
    A->>D: insert Submission + Execution (QUEUED)
    A->>R: enqueue codebox.run_execution(execution_id)
    A-->>U: 202 {execution_id, status: QUEUED}
    loop every 600 ms
        U->>A: GET /api/v1/executions/{id}
        A->>D: read status (only the owner's)
        A-->>U: status / result
    end
    R->>W: deliver job
    W->>D: status RUNNING
    opt compiled language (Java, C++)
        W->>S: compile container (higher limits), stream source over stdin
        S-->>W: compiler result + build artifacts
    end
    W->>S: run container, stream code/artifacts + inputs over stdin
    S-->>W: one nonce-tagged JSON line (per-test stdout, stderr, time, memory, exit status)
    W->>W: classify (TLE / MLE / RE), judge outputs vs expected (expected never enters the sandbox)
    W->>D: store result, status COMPLETED/FAILED
    Note over W,S: container is force-removed in all cases
```

Why the API is asynchronous: running code takes from milliseconds up to the time limit, plus container start-up. A queue keeps the API responsive, caps concurrency (`WORKER_CONCURRENCY`), and survives worker restarts, since Redis persists the queue and tasks are acknowledged late.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, Monaco Editor, React Router, react-markdown |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, PostgreSQL 17 (psycopg 3) |
| Queue | Redis 7, Celery 5 |
| Sandbox | Docker Engine, Docker SDK for Python |
| AI | Any OpenAI-compatible Chat Completions API, called with `httpx` |
| Infra | Docker, Docker Compose, nginx (unprivileged) |

**LangChain/LangGraph are not used.** Each assistant request is a single model call with a role-specific prompt and context, so a framework would add dependencies and nothing else. The routing is about 20 lines of plain Python (`ai/assistant.py`).

---

## Directory structure

```text
codebox/
├── frontend/                    React + TypeScript + Vite SPA
│   ├── src/
│   │   ├── api/                 typed API client + types
│   │   ├── auth/                auth context (JWT)
│   │   ├── components/          Workspace, CodeEditor (Monaco), ResultPanel, TestResults, AIAssistant, …
│   │   ├── hooks/               useExecution (submit + poll), useMediaQuery
│   │   ├── lib/                 formatting, playground templates
│   │   └── pages/               Problems, Problem workspace, Playground, Submissions, Detail, Login/Register
│   ├── nginx.conf               static hosting, /api proxy, CSP & security headers
│   └── Dockerfile
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, error handlers, startup (tables + seed)
│   │   ├── config.py            settings from environment
│   │   ├── database.py          engine/session
│   │   ├── models/              User, Problem, TestCase, Submission, Execution
│   │   ├── schemas/             Pydantic request/response models
│   │   ├── routes/              auth, problems, executions, submissions, ai, meta
│   │   ├── services/            auth (JWT/bcrypt), executions, judge, rate_limit
│   │   ├── workers/             Celery app + tasks (the only Docker user)
│   │   └── seed/                problem set (problems.py, extra_problems.py): starter code, test generators, reference solvers
│   ├── requirements.txt / requirements-dev.txt
│   └── Dockerfile               API/worker image (+ `test` stage)
├── executor/                    sandbox engine (trusted side + in-container runner)
│   ├── executor.py              DockerExecutor: creates, feeds, limits, removes containers
│   ├── languages.py             language registry (image, compile/run commands)
│   ├── status.py                status constants
│   ├── runner/runner.py         runs as PID 1 inside each sandbox (untrusted zone)
│   └── Dockerfiles/{python,javascript,java,cpp}/Dockerfile
├── ai/assistant.py              router + 4 specialised agents + OpenAI-compatible client
├── tests/                       unit, API, worker, Docker integration, end-to-end
│   └── e2e/test_stack.py        runs against a live `docker compose` stack
├── deploy/postgres/             DB init (creates the separate test database)
├── docker-compose.yml
├── pytest.ini
├── .env.example  .gitignore  .dockerignore  .gitattributes
└── README.md
```

---

## Docker architecture

| Service | Image | Role | Docker socket | Networks | Host port |
| --- | --- | --- | --- | --- | --- |
| `frontend` | `codebox-frontend` (nginx-unprivileged) | Serves the SPA, proxies `/api` | no | `web` | `127.0.0.1:8080` |
| `backend` | `codebox-backend` | FastAPI, runs as uid 10002, read-only FS | **no** | `web`, `data` | `127.0.0.1:8000` (Swagger at `/docs`) |
| `celery-worker` | `codebox-backend` | Runs jobs, drives sandboxes | **yes** | `data` only | none |
| `postgres` | `postgres:17-alpine` | Persistent storage | no | `data` | none |
| `redis` | `redis:7-alpine` | Celery broker (AOF persistence) | no | `data` | none |
| `sandbox-*` | `codebox-sandbox-<lang>` | **Build-only.** They build the language images and exit | no | none | none |
| `tests` (profile `test`) | `codebox-tests` | Runs the full test suite | yes | `data` | none |

**Trusted and untrusted containers are separate.** Only `celery-worker` has access to the Docker socket. It creates the sandbox containers as siblings on the host daemon; they are not nested inside the worker. The sandboxes:

- get **no** socket, **no** bind mounts, **no** volumes and **no** network interface (`network_mode: none`), and
- receive code only as a JSON payload over their stdin.

The `data` network is `internal`: PostgreSQL, Redis and the worker have no route to the internet and no published ports. Only the backend joins the `web` network, because it needs outbound access to the AI provider.

Language images are built with the rest of the stack (`docker compose up --build`). The worker waits (`service_completed_successfully`) until all four exist.

---

## Sandbox and security model

**Threat model:** submitted code is hostile. It may try to use CPU, memory, processes, disk or output without limit; reach the network; read or modify host or application data; escalate privileges; tamper with its own verdict; or read hidden test data.

### Controls on every sandbox container

| Control | Setting |
| --- | --- |
| Fresh container per job | Created → fed → run → **force-removed** in a `finally` block. Leftovers (e.g. after a worker crash) are removed at worker start-up by label |
| Memory | `mem_limit = MEMORY_LIMIT` (default `128m`), `memswap_limit` equal to it (no swap). OOM is detected from cgroup v2 `memory.events` |
| CPU | `nano_cpus = CPU_LIMIT` (default 0.5 core) |
| Time | Per-test wall-clock timeout (`EXECUTION_TIMEOUT`, ×2 for Java) enforced by killing the whole process group; `RLIMIT_CPU` as a backstop; an overall container deadline enforced by the worker |
| Processes | `pids_limit = 64`, so fork bombs are contained |
| Files | Read-only root filesystem. Writable `tmpfs` only at `/sandbox` (64 MB) and `/tmp` (64 MB, `noexec`); both count toward the memory limit. `RLIMIT_FSIZE` caps output files. `nofile=256` |
| Output | stdout/stderr go to files and are truncated to 1 MiB for judging; 64 KiB is stored and shown |
| User | Non-root `10001:10001`, forced at run time. Setuid/setgid bits are stripped in the image |
| Privileges | `cap_drop: ALL`, `no-new-privileges`, not privileged, Docker's default seccomp and AppArmor profiles |
| Network | `network_mode: none`. Only a loopback interface exists |
| Host access | No bind mounts, no volumes, no Docker socket, private IPC namespace |
| Leftover processes | After each test, the runner (PID 1) sends `kill(-1, SIGKILL)`, which also kills daemonised children (`setsid`), and `/tmp` is wiped between test cases |
| Result integrity | The runner marks itself non-dumpable, so the same-uid program can't read its memory or file descriptors through `/proc`. Its single result line is prefixed with a random per-job nonce |
| Hidden tests | Expected outputs never enter the sandbox; the worker judges outside it. The API never returns hidden inputs or outputs, not even to the submitter |
| Compilation | Java and C++ compile in a separate container with larger limits (`COMPILE_*`). Only the build artifacts are passed to the run container |

Every row above is covered by an integration test in `tests/test_executor_docker.py`, for example: network blocked, rootfs read-only, `CapEff=0`, `NoNewPrivs=1`, fork bomb contained, background process killed, `/proc/1` protected, containers removed, and `HostConfig` limits applied.

### Application security

- Registration rejects domains without a mail server (DNS/MX lookup), invalid Gmail usernames and known throwaway providers, and suggests fixes for typos. Addresses are not confirmed by email, so an account can use an address its owner doesn't control.
- Passwords hashed with bcrypt (cost 12) and never stored or logged in plaintext. Login timing is equalised for unknown users.
- JWT (HS256) with a required `exp`. `JWT_SECRET` has no default and must be at least 32 characters. Unsigned or forged tokens are rejected.
- Every submission and execution query is scoped to its owner. Other users' IDs return 404, not 403, so existence isn't leaked. Execution IDs are UUIDs.
- Rate limits (Redis, fixed window): login per user and per IP, registration per IP, executions per user, AI calls per user. There is also a cap on queued jobs per user.
- Input size limits: 64 KB source and 64 KB stdin.
- nginx adds a strict CSP, `X-Frame-Options: DENY`, `nosniff` and a referrer policy. Markdown (including AI output) is rendered without raw HTML.
- Secrets come only from the environment. `.env` is git-ignored and never baked into images.

### What this does **not** protect against (read this)

Containers share the host kernel. This design is a solid defence-in-depth sandbox, **not** a guarantee:

1. **Kernel exploits.** A Linux kernel or container runtime vulnerability could let code escape the container. For hostile multi-tenant use, set `SANDBOX_RUNTIME=runsc` ([gVisor](https://gvisor.dev)), or run sandboxes in microVMs (Kata Containers, Firecracker) on a dedicated host.
2. **The Docker socket equals root on the host.** The worker holds it. The worker never runs user code, has no ports and sits on an internal network, but if the worker process were compromised, the host would be too. Stronger options: [rootless Docker](https://docs.docker.com/engine/security/rootless/), a separate execution VM or host, or a restricted socket proxy.
3. **Side channels and noisy neighbours.** CPU caches and timing are shared, so measured runtimes vary with host load.
4. **Denial of service.** Limits bound each job, and `WORKER_CONCURRENCY` bounds how many run at once. A determined attacker can still keep the queue busy within the rate limits.

---

## API

Base path `/api/v1`. Interactive docs: <http://localhost:8000/docs> (Swagger UI) and `/openapi.json`. 🔒 = requires `Authorization: Bearer <token>`.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | `{username, email, password}` → `201 {access_token, user}`. 422 if the email fails the checks (no mail server, invalid Gmail username, typo, throwaway provider); 409 says whether the username or the email is taken |
| POST | `/auth/login` | `{username (or email), password}` → `{access_token, user}` |
| GET 🔒 | `/auth/me` | Current user |
| GET | `/problems` | Problem list (with `solved` flags when authenticated) |
| GET | `/problems/{slug or id}` | Statement, constraints, examples, starter code, test case count (no test data) |
| POST 🔒 | `/execute` | Run with custom input: `{language, source_code, stdin?, problem_id?}` → `202 {execution_id, submission_id, status}` |
| POST 🔒 | `/submissions` | Judge against test cases: `{problem_id, language, source_code}` → `202 {execution_id, …}` |
| GET 🔒 | `/executions/{execution_id}` | Status and result (poll until not `QUEUED`/`RUNNING`) |
| GET 🔒 | `/submissions?page=&page_size=&kind=run\|submit&problem_id=` | Your history (paginated) |
| GET 🔒 | `/submissions/{id}` | Code, input, output, errors, per-test results |
| GET | `/ai/status` | `{enabled, model}` |
| POST 🔒 | `/ai/assist` | `{action: auto\|explain\|debug\|complexity\|optimize, language, source_code, question?, error?, stdin?, stdout?, problem_id?}` → `{agent, content, model}` (503 with a clear message if AI is unavailable) |
| GET | `/languages` | Supported languages, time limits and sandbox limits |
| GET | `/health` | `{"status","database","redis"}`, 503 when degraded |

**Example:**

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"demo","email":"demo@example.com","password":"password123"}' | jq -r .access_token)

ID=$(curl -s -X POST localhost:8080/api/v1/execute -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"language":"python","source_code":"print(int(input())*2)","stdin":"21"}' | jq -r .execution_id)

curl -s localhost:8080/api/v1/executions/$ID -H "Authorization: Bearer $TOKEN"
```

```json
{
  "execution_id": "0b7d…", "status": "COMPLETED", "stdout": "42\n", "stderr": "",
  "execution_time": 24, "memory_used": 8960, "compile_output": null, "…": "…"
}
```

`execution_time` is in **milliseconds**, and `memory_used` is peak resident memory in **KB**. For judged submissions, `test_results` lists `{index, passed, status, time_ms, memory_kb, is_sample, message}`. Sample cases also include `input`, `expected_output` and `actual_output`; hidden cases never do.

Errors always look like `{"detail": "human-readable message"}`: 400 unsupported language or empty code, 401, 404, 409 duplicate user, 413 too large, 422 validation, 429 rate-limited, 503 database, queue or AI unavailable.

---

## Environment variables

Copy `.env.example` to `.env`. **Never commit `.env`.**

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `codebox` / *(required)* / `codebox` | Database container credentials |
| `DATABASE_URL` | – | SQLAlchemy URL. Its password must match `POSTGRES_PASSWORD` |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker and rate limiter |
| `JWT_SECRET` | *(required, ≥ 32 chars)* | Token signing key |
| `OPENROUTER_API_KEY` | empty | Enables the AI assistant through [OpenRouter](https://openrouter.ai/keys). Takes precedence over `OPENAI_API_KEY` |
| `OPENROUTER_MODEL` | `qwen/qwen3.8-27b:free` | Any id from <https://openrouter.ai/models>; ids ending in `:free` cost nothing but are rate-limited |
| `OPENAI_API_KEY` | empty | Used when no OpenRouter key is set. If both keys are empty, AI is disabled and everything else keeps working |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Any OpenAI-compatible endpoint (Azure OpenAI, OpenRouter, Ollama `http://host:11434/v1`, vLLM, …) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name for that endpoint |
| `EMAIL_CHECK_DELIVERABILITY` | `true` | Registration requires the email's domain to have a mail server (DNS/MX lookup) |
| `EXECUTION_TIMEOUT` | `2` | Seconds per test case (Java gets ×2 for JVM start-up) |
| `MEMORY_LIMIT` | `128m` | Memory per run container (no swap) |
| `CPU_LIMIT` | `0.5` | CPU cores per run container |
| `PIDS_LIMIT` | `64` | Max processes/threads per sandbox |
| `COMPILE_TIMEOUT` / `COMPILE_MEMORY_LIMIT` / `COMPILE_CPU_LIMIT` | `15` / `512m` / `1.0` | Limits for the separate compile container |
| `SANDBOX_RUNTIME` | empty | OCI runtime for sandboxes, e.g. `runsc` (gVisor must be installed on the host) |
| `WORKER_CONCURRENCY` | `2` | Programs executed in parallel |
| `FRONTEND_PORT` / `BACKEND_PORT` | `8080` / `8000` | Host ports (bound to 127.0.0.1) |

Other tunables (with defaults) live in `backend/app/config.py`: `MAX_SOURCE_BYTES`, `MAX_STDIN_BYTES`, `MAX_PENDING_EXECUTIONS_PER_USER`, `RATE_LIMIT_*_PER_MINUTE`, `STALE_EXECUTION_SECONDS`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `AI_TIMEOUT` and `CORS_ORIGINS`.

---

## Quick start (Docker Compose)

Requirements: Docker Engine 24+ with Compose v2 (Linux), or Docker Desktop (Windows/macOS). You need about 4 GB of free disk space for the images.

```bash
git clone <your-repo-url> codebox && cd codebox
cp .env.example .env
```

Edit `.env`:

1. Set `POSTGRES_PASSWORD`, and put the **same** password into `DATABASE_URL`.
2. Set `JWT_SECRET`. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"`.
3. Optional: set `OPENROUTER_API_KEY` (or `OPENAI_API_KEY`) to enable the AI assistant.

```bash
docker compose up --build -d      # first build takes a few minutes
docker compose ps                 # all services "running"/"healthy"; sandbox-* "exited (0)"
```

Open **<http://localhost:8080>**, create an account, choose a problem, and press **Run** or **Submit**. The API docs are at <http://localhost:8000/docs>.

Useful commands:

```bash
docker compose logs -f celery-worker    # watch jobs being executed
docker compose down                     # stop (data is kept in volumes)
docker compose down -v                  # stop and delete all data
docker compose up --build -d            # rebuild after changing code
```

On Linux, if you get `permission denied … docker.sock`, add yourself to the docker group with `sudo usermod -aG docker $USER`, then log out and back in.

---

## Windows and Docker Desktop setup

1. Install **Docker Desktop for Windows** and choose the **WSL 2 backend** when prompted (Settings → General → "Use the WSL 2 based engine"). Windows 10 22H2+ or Windows 11 is recommended.
2. In Docker Desktop, go to Settings → Resources and give it at least **4 GB RAM** and 2 CPUs.
3. Make sure Docker Desktop is running. The whale icon in the tray should say "Engine running".
4. In **PowerShell**:

   ```powershell
   git clone <your-repo-url> codebox
   cd codebox
   Copy-Item .env.example .env
   # generate a JWT secret:
   -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
   notepad .env      # set POSTGRES_PASSWORD (also inside DATABASE_URL) and JWT_SECRET
   docker compose up --build -d
   ```

5. Open <http://localhost:8080>.

Notes for Windows:

- Compose mounts `/var/run/docker.sock` into the worker. Docker Desktop provides this path to Linux containers, so no change is needed. Sandbox containers run inside Docker Desktop's WSL 2 VM, which adds an extra isolation layer between user code and Windows.
- The repository's `.gitattributes` keeps LF line endings. If you cloned before it existed, re-clone or run `git config core.autocrlf false`.
- For better file I/O performance, you can clone into the WSL filesystem (e.g. `\\wsl$\Ubuntu\home\you\codebox`) and run the same commands from a WSL shell.

---

## Local development without Compose

Run PostgreSQL and Redis as throw-away containers, and run the API, worker and frontend on the host (Python 3.10+ and Node 20.19+):

```bash
docker compose build sandbox-python sandbox-javascript sandbox-java sandbox-cpp
docker run -d --name codebox-dev-pg -p 127.0.0.1:5432:5432 -e POSTGRES_USER=codebox \
  -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=codebox postgres:17-alpine
docker run -d --name codebox-dev-redis -p 127.0.0.1:6379:6379 redis:7-alpine

python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements-dev.txt
export PYTHONPATH=backend:. JWT_SECRET=$(python -c 'import secrets;print(secrets.token_hex(32))')
export DATABASE_URL=postgresql+psycopg://codebox:devpass@localhost:5432/codebox REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload                                      # API on :8000
celery -A app.workers.celery_app:celery_app worker --loglevel=INFO # worker (needs Docker access)

cd frontend && npm install && npm run dev                          # UI on :5173, proxies /api to :8000
```

For quick experiments you can use `DATABASE_URL=sqlite:///./dev.db`.

---

## Testing

The suite has 164 tests: 154 run in the test container, plus 10 end-to-end tests against the live stack.

| File | What it covers | Needs |
| --- | --- | --- |
| `test_auth.py` | hashing, register/login, duplicate/validation errors, expired/forged/unsigned JWTs, protected routes | – |
| `test_models.py` | seed data, relationships, cascades, indexes, idempotent seeding | – |
| `test_api.py` | problems (no test data leaked), execute/submit validation, 400/404/413/429/503 paths, stale jobs, ownership isolation, history and pagination | – |
| `test_judge.py` | output normalisation, verdicts, `4/5` counting, hidden data never exposed | – |
| `test_worker.py` | task logic with a fake executor: run/submit, crashes, duplicate delivery, output capping | – |
| `test_ai.py` | router, context minimisation, OpenAI-compatible request format, provider errors, timeouts, disabled fallback via API | – |
| `test_rate_limit.py` | fixed window, fail-open, login brute force, execution spam | – |
| `test_executor_unit.py` | limit parsing, status classification, language registry, Docker unavailable or image missing | – |
| `test_executor_docker.py` | **real sandboxes**: all languages, stdin, compile/runtime errors, TLE, MLE, output flood, non-root, no caps, no network, read-only FS, no socket, `/proc/1` protection, fork bomb, background processes, `/tmp` isolation, cleanup, `HostConfig` limits, **all 60 reference solutions (15 problems × 4 languages) pass the hidden tests**, and unmodified starter code fails | Docker + images |
| `e2e/test_stack.py` | through nginx: health, all languages, limits, judging, history, cross-user isolation, AI fallback | running stack |

**Recommended: run everything in Docker (works the same on Windows):**

```bash
docker compose --profile test run --rm tests            # full suite, against PostgreSQL (codebox_test DB)
```

**End-to-end against the running stack:**

```bash
docker compose up -d --build
pip install -r backend/requirements-dev.txt
CODEBOX_E2E_URL=http://127.0.0.1:8080 pytest tests/e2e -v
```

**On the host** (SQLite, fast; Docker tests run if the daemon and images are available): `pip install -r backend/requirements-dev.txt && pytest`.

---

## Adding a new language

Example: Go.

1. **Image.** Create `executor/Dockerfiles/go/Dockerfile`. Start from an official image, install `python3` for the runner if the base image lacks it, and copy the common block from an existing Dockerfile: `sandbox` user 10001, `/sandbox`, stripped setuid bits, `COPY runner/runner.py`, `USER 10001:10001`, `ENTRYPOINT ["python3","-I","/opt/codebox/runner.py"]`.
2. **Register it** in `executor/languages.py`:

   ```python
   Language(
       key="go", display_name="Go 1.23", image="codebox-sandbox-go:latest", monaco_id="go",
       layout=lambda src: Layout("main.go", ["./main"]),
       compile_cmd=lambda fn: ["go", "build", "-o", "main", fn],
       separate_compile=True, artifacts=["main"],
   )
   ```

   Compilers that need a writable home or cache should use `/tmp` (e.g. set `GOCACHE=/tmp/go-cache` in the image `ENV`).
3. **Compose.** Add a `sandbox-go` build-only service like the others, and add it to the worker's `depends_on`.
4. **Frontend.** Add a label in `frontend/src/lib/format.ts` (`LANGUAGE_LABEL`), a template in `lib/templates.ts`, and the Monaco id in `components/CodeEditor.tsx`.
5. **Problems.** Add starter code for `go` to each problem in `backend/app/seed/problems.py`, and a reference patch in `tests/solutions.py`. The Docker tests then check that the new language passes every problem.
6. Run `docker compose up --build -d` and then `docker compose --profile test run --rm tests`.

---

## Known limitations

- **Container isolation is not VM isolation.** See [what this does not protect against](#what-this-does-not-protect-against-read-this). Use gVisor or microVMs for untrusted public deployments.
- **The worker holds the Docker socket,** which is root-equivalent. Isolate it on a dedicated host or VM in production.
- **Measurements are approximate.** Runtime is wall-clock time and is affected by host load and the CPU quota. Memory is the process's peak RSS and includes the runtime's baseline (e.g. JVM about 35 MB, Node about 45 MB).
- **Exact-output judging** after trailing-whitespace normalisation. There are no special checkers for floating-point tolerance or multiple valid answers; the problems are designed to have one answer.
- **Test cases of one submission run sequentially in the same container,** each as a fresh process with a wiped `/tmp`. Files written to `/sandbox` persist between those test cases.
- **Schema changes** use `create_all` on start-up; there are no migrations yet.
- **Auth.** JWTs can't be revoked before they expire, and the token is stored in `localStorage`, relying on the CSP to mitigate XSS. There is no email verification or password reset.
- **AI.** Code is sent to the configured third-party provider. Responses aren't streamed. Rate limits are fixed-window and fail open when Redis is down.
- **OOM detection** is most accurate on cgroup v2 hosts (all current Docker Desktop and modern Linux). On cgroup v1 it falls back to exit-signal and stderr heuristics.

## Future improvements

- gVisor (`runsc`) enabled by default, or a Firecracker-based execution tier; a dedicated execution host reached through an authenticated socket proxy
- A pool of pre-warmed sandbox containers to cut start-up latency (especially for Java)
- Alembic migrations; an admin UI for authoring problems and test cases; special checkers
- Result push over WebSockets/SSE instead of polling; streaming AI responses
- Refresh tokens with revocation, httpOnly cookies, OAuth login, email verification
- Per-language resource profiles, leaderboards, contests, and multi-file projects
- Prometheus metrics (queue depth, sandbox durations, verdict rates) and structured logs
