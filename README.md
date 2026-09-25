# CodeBox: AI-Powered Docker Code Execution Sandbox

CodeBox is a self-hosted coding practice platform, like a small LeetCode or HackerRank. You sign in, pick a problem, write a solution in the browser in Python, JavaScript, Java or C++, and submit it against hidden test cases. An AI assistant can explain, debug or optimise your code.

Every piece of submitted code runs in a **fresh, locked-down Docker container** that is destroyed afterwards. User code never runs on the host or inside the application's own containers.

```
Browser (React + Monaco) → nginx → FastAPI → Redis → Celery worker → Docker sandbox → PostgreSQL → Browser
```

---

## Contents

- [Features](#features)
- [Using the app](#using-the-app)
- [Quick start](#quick-start)
- [Windows and Docker Desktop](#windows-and-docker-desktop)
- [Enabling the AI assistant](#enabling-the-ai-assistant)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Docker architecture](#docker-architecture)
- [Sandbox and security model](#sandbox-and-security-model)
- [API](#api)
- [Environment variables](#environment-variables)
- [Managing data](#managing-data)
- [Local development without Compose](#local-development-without-compose)
- [Testing](#testing)
- [Adding a new language](#adding-a-new-language)
- [Known limitations](#known-limitations)
- [Future improvements](#future-improvements)

---

## Features

| Area | What you get |
| --- | --- |
| **Accounts** | Every page requires signing in. Split-screen login and registration pages with a password strength meter and show/hide toggle. Registration checks the email: the domain must have a mail server, Gmail's username rules are enforced, typos such as `gmal.co` get a "Did you mean …@gmail.com?" suggestion, and throwaway inboxes are blocked. Sign in with username or email. JWT auth, bcrypt password hashing, per-user data isolation, login rate limiting |
| **Problems** | 15 problems: 9 Easy, 4 Medium and 2 Hard, from Two Sum to Trapping Rain Water and Edit Distance. Each has topic tags, a statement, constraints, examples, starter code in 4 languages, and 5–8 test cases, including large hidden ones that catch slow solutions |
| **Problems page** | Greeting with a "pick up where you left off" suggestion and a random-pick button, a progress ring with a bar per difficulty, search, difficulty/status/topic filters (kept in the URL), a per-problem status (solved / attempted / not started), and a community acceptance rate calculated from real submissions |
| **Editor** | Monaco (the VS Code editor), bundled locally. Syntax highlighting, drafts saved per problem and language, <kbd>Ctrl</kbd>+<kbd>Enter</kbd> to run, resizable panes, responsive layout |
| **Languages** | Python 3.12, JavaScript (Node.js 22), Java 21, C++17 (GCC), each in its own sandbox image |
| **Run** | Run with custom input and see stdout, stderr, compiler output, runtime and peak memory |
| **Submit** | Judge against every test case. Shows `Passed 4/5` with ✓/✗ per case. Hidden cases never reveal their input or expected output |
| **Statuses** | `QUEUED`, `RUNNING`, `COMPLETED`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `COMPILATION_ERROR`, `RUNTIME_ERROR`, `FAILED`, plus the judged verdicts `ACCEPTED` and `WRONG_ANSWER` |
| **History** | All your runs and submissions (problem, language, status, runtime, memory, time), with a detail page showing code, input, output, errors and test results |
| **AI assistant** | CodeExplainer, Debugger, ComplexityAnalyzer and Optimizer, chosen by a simple router. Uses OpenRouter (free models available) or any OpenAI-compatible API. Answers render as Markdown, including tables. Without an API key the rest of the app works normally |
| **Resilience** | Clear error messages, never stack traces, when Docker, PostgreSQL, Redis, the worker or the AI provider fails |

---

## Using the app

1. **Sign in or create an account** at <http://localhost:8080>. Any page you open while signed out sends you to the login page, and you return to that page afterwards.
2. **Problems** is the home page. Filter by difficulty, status or topic, search by name, use **Continue** to resume a problem you attempted, or click **Random**.
3. **Open a problem** to get the workspace:
   - the left panel has **Description** (statement, examples, tags, acceptance rate), **Submissions** (your attempts at this problem) and **✦ AI Assistant**
   - the editor is on the right, with a language selector, **Reset**, **▶ Run** and **Submit**
   - below the editor, **Custom input** holds the stdin used by Run, and **Result** shows the output or the per-test verdicts
4. **Playground** runs any program in any of the four languages, without a problem attached.
5. **Submissions** lists your full history; click a row for the details.
6. **AI Assistant**: click **Explain**, **Debug**, **Complexity** or **Optimize**, or type a question. After a run, the assistant also sees the error and input/output.

---

## Quick start

**Requirements:** Docker Engine 24+ with Compose v2 on Linux, or Docker Desktop on Windows/macOS; about 4 GB of free disk space.

```bash
git clone https://github.com/Keerthi316/codebox.git
cd codebox/codebox          # the application lives in the codebox/ folder
cp .env.example .env
```

Edit `.env`:

1. Set `POSTGRES_PASSWORD`, and put the **same** password into `DATABASE_URL`.
2. Set `JWT_SECRET` to at least 32 random characters: `python3 -c "import secrets; print(secrets.token_hex(32))"`.
3. Optional: set `OPENROUTER_API_KEY` to enable the AI assistant (see [below](#enabling-the-ai-assistant)).

```bash
docker compose up --build -d      # the first build takes a few minutes
docker compose ps                 # services "running"/"healthy"; the four sandbox-* entries "exited (0)"
```

Open **<http://localhost:8080>** and create an account. Use a real email address; see [Features](#features) for the checks. The API documentation is at <http://localhost:8000/docs>.

Useful commands:

```bash
docker compose logs -f celery-worker    # watch code being executed
docker compose up --build -d            # rebuild after changing code
docker compose down                     # stop (data is kept)
docker compose down -v                  # stop and delete all data
```

On Linux, if `docker` says `permission denied … docker.sock`, run `sudo usermod -aG docker $USER`, then log out and back in.

---

## Windows and Docker Desktop

1. Install **Docker Desktop for Windows** with the **WSL 2 backend** (Settings → General → "Use the WSL 2 based engine"). Windows 10 22H2+ or Windows 11 is recommended.
2. In Docker Desktop, go to Settings → Resources and give it at least **4 GB RAM** and 2 CPUs.
3. Start Docker Desktop and wait until it shows "Engine running".
4. In **PowerShell**:

   ```powershell
   git clone https://github.com/Keerthi316/codebox.git
   cd codebox\codebox
   Copy-Item .env.example .env
   # generate a JWT secret:
   -join ((1..64) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
   notepad .env      # set POSTGRES_PASSWORD (also inside DATABASE_URL) and JWT_SECRET
   docker compose up --build -d
   ```

5. Open <http://localhost:8080>.

Notes:

- Compose mounts `/var/run/docker.sock` into the worker. Docker Desktop provides this path to Linux containers, so nothing needs changing. Sandboxes run inside Docker Desktop's WSL 2 VM, which adds an extra isolation layer between user code and Windows.
- `.gitattributes` keeps LF line endings, which the Linux containers need. If files were checked out with CRLF, run `git config core.autocrlf false` and clone again.
- For faster file access, clone into the WSL filesystem (e.g. `\\wsl$\Ubuntu\home\you`) and run the commands from a WSL shell.

---

## Enabling the AI assistant

The assistant works with [OpenRouter](https://openrouter.ai) out of the box, and with any OpenAI-compatible API.

1. Create a key at <https://openrouter.ai/keys>.
2. In `.env`, set:

   ```env
   OPENROUTER_API_KEY=sk-or-...
   OPENROUTER_MODEL=cohere/north-mini-code:free
   ```

   Any id from <https://openrouter.ai/models> works. Ids ending in `:free` cost nothing, but they are shared and can be rate-limited at busy times; if the assistant reports rate limiting, try another model.
3. Apply it: `docker compose up -d --force-recreate backend`.
4. Check it: `curl http://localhost:8080/api/v1/ai/status` should return `"enabled":true`.

To use OpenAI or another compatible provider instead, leave `OPENROUTER_API_KEY` empty and set `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `OPENAI_MODEL`.

The assistant receives only the code, the language, the problem statement and, after a run, that run's error and input/output. It never sees user details, other submissions or hidden test data.

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
        RD[("Redis<br/>queue + rate limits")]
        WK["celery-worker<br/>(trusted, Docker API access)"]
    end

    subgraph host["Host Docker daemon"]
        SB1["sandbox container<br/>codebox-sandbox-python"]
        SB2["sandbox container<br/>codebox-sandbox-java …"]
    end

    LLM["OpenRouter /<br/>OpenAI-compatible API"]

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
    A->>A: check login, language, size and rate limits
    A->>D: insert Submission + Execution (QUEUED)
    A->>R: enqueue codebox.run_execution(execution_id)
    A-->>U: 202 {execution_id, status: QUEUED}
    loop every 600 ms
        U->>A: GET /api/v1/executions/{id}
        A->>D: read status (owner only)
        A-->>U: status / result
    end
    R->>W: deliver job
    W->>D: status RUNNING
    opt compiled language (Java, C++)
        W->>S: compile container (higher limits), source streamed over stdin
        S-->>W: compiler result + build artifacts
    end
    W->>S: run container, code/artifacts + inputs streamed over stdin
    S-->>W: one nonce-tagged JSON line (per-test stdout, stderr, time, memory, exit status)
    W->>W: classify (TLE / MLE / RE), compare with expected outputs (these never enter the sandbox)
    W->>D: store result, status COMPLETED/FAILED
    Note over W,S: the container is force-removed in every case
```

The API is asynchronous because a run takes anywhere from milliseconds to the time limit, plus container start-up. The queue keeps the API responsive, limits how many programs run at once (`WORKER_CONCURRENCY`), and survives worker restarts, because Redis persists the queue and tasks are acknowledged only after they finish.

---

## Tech stack

| Layer | Technology | Used for |
| --- | --- | --- |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4, React Router 7 | The single-page app |
| | Monaco Editor | The code editor (bundled, no CDN) |
| | react-markdown + remark-gfm | Problem statements and AI answers, including tables, without raw HTML |
| Web server | nginx (unprivileged) | Serves the app, proxies `/api`, security and cache headers |
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic v2 | REST API and request validation |
| | SQLAlchemy 2, psycopg 3, PostgreSQL 17 | Persistent storage |
| | bcrypt, PyJWT | Password hashing, login tokens |
| | email-validator (+ dnspython) | Email syntax and mail-server (MX) checks |
| Queue | Redis 7, Celery 5 | Background execution jobs; Redis also backs the rate limiter |
| Sandbox | Docker Engine, Docker SDK for Python | One throw-away container per job |
| AI | OpenRouter / any OpenAI-compatible API via `httpx` | The assistant |
| Infra | Docker Compose | Runs and connects all services |
| Tests | pytest, httpx2 | 245 automated tests |

**LangChain/LangGraph are not used.** Each assistant request is a single model call with a role-specific prompt, so a framework would add dependencies and nothing else. The router is about 20 lines of plain Python in `ai/assistant.py`.

---

## Repository layout

```text
.
├── README.md
└── codebox/                         the application (run all commands from here)
    ├── frontend/                    React + TypeScript + Vite
    │   ├── src/
    │   │   ├── api/                 typed API client and types
    │   │   ├── auth/                sign-in state (JWT)
    │   │   ├── components/          Workspace, CodeEditor, ResultPanel, TestResults, AIAssistant, Header, …
    │   │   ├── hooks/               useExecution (submit + poll), useMediaQuery
    │   │   ├── lib/                 formatting, playground templates, safe post-login redirects
    │   │   └── pages/               Login/Register, Problems, problem workspace, Playground, Submissions
    │   ├── nginx.conf               hosting, /api proxy, CSP, cache headers
    │   └── Dockerfile
    ├── backend/
    │   ├── app/
    │   │   ├── main.py              FastAPI app, error handlers, start-up (tables + problems)
    │   │   ├── config.py            settings from the environment
    │   │   ├── database.py          engine, sessions, small schema upgrades
    │   │   ├── models/              User, Problem, TestCase, Submission, Execution
    │   │   ├── schemas/             request/response models
    │   │   ├── routes/              auth, problems, executions, submissions, ai, meta
    │   │   ├── services/            auth, email_checks, executions, judge, rate_limit
    │   │   ├── workers/             Celery app and tasks (the only Docker user)
    │   │   └── seed/                problems.py + extra_problems.py: statements, starter code,
    │   │                            test generators, reference solvers
    │   ├── requirements.txt, requirements-dev.txt
    │   └── Dockerfile               API/worker image, plus a `test` stage
    ├── executor/                    the sandbox engine
    │   ├── executor.py              DockerExecutor: creates, feeds, limits and removes containers
    │   ├── languages.py             language registry (image, compile/run commands)
    │   ├── status.py                status constants
    │   ├── runner/runner.py         runs as PID 1 inside each sandbox
    │   └── Dockerfiles/{python,javascript,java,cpp}/Dockerfile
    ├── ai/assistant.py              router, 4 specialised prompts, OpenAI-compatible client
    ├── tests/                       unit, API, worker, Docker sandbox and end-to-end tests
    ├── deploy/postgres/             creates the separate test database
    ├── docker-compose.yml
    ├── pytest.ini
    └── .env.example, .gitignore, .dockerignore, .gitattributes
```

---

## Docker architecture

| Service | Image | Role | Docker socket | Networks | Host port |
| --- | --- | --- | --- | --- | --- |
| `frontend` | `codebox-frontend` (nginx-unprivileged) | Serves the app, proxies `/api` | no | `web` | `127.0.0.1:8080` |
| `backend` | `codebox-backend` | FastAPI; uid 10002, read-only filesystem | **no** | `web`, `data` | `127.0.0.1:8000` (Swagger at `/docs`) |
| `celery-worker` | `codebox-backend` | Runs jobs, drives sandboxes | **yes** | `data` only | none |
| `postgres` | `postgres:17-alpine` | Persistent storage | no | `data` | none |
| `redis` | `redis:7-alpine` | Job queue (persisted) and rate limits | no | `data` | none |
| `sandbox-*` | `codebox-sandbox-<lang>` | **Build-only**: they build the language images and exit | no | none | none |
| `tests` (profile `test`) | `codebox-tests` | Runs the test suite | yes | `data` | none |

**Trusted and untrusted containers are separate.** Only `celery-worker` can use the Docker socket. It creates sandbox containers as siblings on the host daemon, not nested inside itself. Sandboxes get no socket, no bind mounts, no volumes and no network interface, and receive code only as a JSON payload over their stdin.

The `data` network is `internal`: PostgreSQL, Redis and the worker have no route to the internet and no published ports. Only the backend joins the `web` network, because it needs outbound access to the AI provider and for email DNS checks. Host ports bind to `127.0.0.1`, so they aren't reachable from other machines.

The language images are built with the rest of the stack, and the worker waits (`service_completed_successfully`) until all four exist.

---

## Sandbox and security model

**Threat model:** submitted code is hostile. It may try to use unlimited CPU, memory, processes, disk or output; reach the network; read or change host or application data; escalate privileges; tamper with its own verdict; or read hidden test data.

### Controls on every sandbox container

| Control | Setting |
| --- | --- |
| Fresh container per job | Created → fed → run → **force-removed** in a `finally` block. Leftovers (e.g. after a worker crash) are removed at worker start-up, found by label |
| Memory | `MEMORY_LIMIT` (default `128m`), no swap. Out-of-memory is detected from cgroup v2 `memory.events` |
| CPU | `CPU_LIMIT` (default 0.5 core) |
| Time | Per-test wall-clock limit (`EXECUTION_TIMEOUT`, ×2 for Java), enforced by killing the process group; `RLIMIT_CPU` as a backstop; an overall container deadline enforced by the worker |
| Processes | `pids_limit = 64`, so fork bombs are contained |
| Files | Read-only root filesystem. Writable `tmpfs` only at `/sandbox` and `/tmp` (64 MB each, `/tmp` is `noexec`), counted against the memory limit. `RLIMIT_FSIZE` caps output files; `nofile=256` |
| Output | stdout/stderr go to files, truncated to 1 MiB for judging; up to 64 KiB is stored and shown |
| User | Non-root `10001:10001`, forced at run time; setuid/setgid bits stripped from the images |
| Privileges | `cap_drop: ALL`, `no-new-privileges`, not privileged, Docker's default seccomp and AppArmor profiles |
| Network | `network_mode: none`: only a loopback interface exists |
| Host access | No bind mounts, no volumes, no Docker socket, private IPC namespace |
| Leftover processes | After each test the runner (PID 1) sends `kill(-1, SIGKILL)`, which also catches daemonised children, and `/tmp` is wiped between test cases |
| Result integrity | The runner marks itself non-dumpable, so the program can't read its memory or file descriptors through `/proc`; its result line carries a random per-job nonce |
| Hidden tests | Expected outputs never enter the sandbox; the worker judges outside it. The API never returns hidden inputs or outputs, even to the submitter |
| Compilation | Java and C++ compile in a separate container with larger limits (`COMPILE_*`); only the build artifacts reach the run container |

Each control above is covered by integration tests in `tests/test_executor_docker.py`, for example: network blocked, read-only filesystem, no capabilities, `NoNewPrivs=1`, fork bomb contained, background processes killed, `/proc/1` protected, containers removed, and the container limits actually applied.

### Application security

- **Login required everywhere.** The API rejects every problem, execution, submission and AI request without a valid token, and the frontend redirects to the login page. After login it returns only to real app pages, never to arbitrary or stale addresses.
- **Passwords** are hashed with bcrypt (cost 12), never stored or logged in plaintext. Login timing is equalised for unknown users, and login failures don't reveal whether a username exists.
- **Tokens**: JWT (HS256) with a required expiry. `JWT_SECRET` has no default and must be at least 32 characters; unsigned or forged tokens are rejected.
- **Isolation**: every submission and execution query is scoped to its owner; other users' IDs return 404, not 403. Execution IDs are UUIDs.
- **Email checks**: registration rejects domains without a mail server (DNS/MX lookup), invalid Gmail usernames and throwaway providers, and suggests fixes for typos. Addresses aren't confirmed by email, so an account can use an address its owner doesn't control.
- **Rate limits** (Redis, fixed window): login per user and per IP, registration per IP, executions per user, AI calls per user, plus a cap on queued jobs per user.
- **Input limits**: 64 KB of source code and 64 KB of input.
- **Browser hardening**: nginx sends a strict Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff` and a referrer policy. Markdown, including AI output, is rendered without raw HTML. Pages are always revalidated, so updates reach users immediately; hashed JS/CSS files are cached long-term.
- **Secrets** come only from the environment. `.env` is git-ignored and never baked into images.

### What this does **not** protect against

Containers share the host kernel. This is a solid defence-in-depth sandbox, **not** a guarantee:

1. **Kernel exploits.** A Linux kernel or container runtime vulnerability could let code escape. For hostile multi-tenant use, set `SANDBOX_RUNTIME=runsc` ([gVisor](https://gvisor.dev)) or run sandboxes in microVMs (Kata Containers, Firecracker) on a dedicated host.
2. **The Docker socket equals root on the host.** The worker holds it. It never runs user code, has no ports and sits on an internal network, but a compromised worker would mean a compromised host. Stronger options: [rootless Docker](https://docs.docker.com/engine/security/rootless/), a separate execution VM or host, or a restricted socket proxy.
3. **Side channels and noisy neighbours.** CPU caches and timing are shared, so measured runtimes vary with host load.
4. **Denial of service.** Limits bound each job and `WORKER_CONCURRENCY` bounds parallelism, but a determined user can still keep the queue busy within the rate limits.

---

## API

Base path `/api/v1`. Interactive docs: <http://localhost:8000/docs> (Swagger UI) and `/openapi.json`.
🔒 = requires `Authorization: Bearer <token>`.

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/register` | `{username, email, password}` → `201 {access_token, user}`. 422 if the email fails the checks (with a reason or a "Did you mean" suggestion); 409 says whether the username or the email is taken |
| POST | `/auth/login` | `{username (or email), password}` → `{access_token, user}` |
| GET 🔒 | `/auth/me` | The current user |
| GET 🔒 | `/problems` | All problems: `{id, slug, title, difficulty, tags, solved, attempted, submissions, acceptance_rate}` |
| GET 🔒 | `/problems/{slug or id}` | The above plus statement, constraints, examples, starter code and test case count (never the tests themselves) |
| POST 🔒 | `/execute` | Run with custom input: `{language, source_code, stdin?, problem_id?}` → `202 {execution_id, submission_id, status}` |
| POST 🔒 | `/submissions` | Judge against the test cases: `{problem_id, language, source_code}` → `202 {execution_id, …}` |
| GET 🔒 | `/executions/{execution_id}` | Status and result; poll until it is no longer `QUEUED`/`RUNNING` |
| GET 🔒 | `/submissions?page=&page_size=&kind=run\|submit&problem_id=` | Your history, paginated |
| GET 🔒 | `/submissions/{id}` | Code, input, output, errors, per-test results |
| GET | `/ai/status` | `{enabled, model, provider}` |
| POST 🔒 | `/ai/assist` | `{action: auto\|explain\|debug\|complexity\|optimize, language, source_code, question?, error?, stdin?, stdout?, problem_id?}` → `{agent, content, model}`; 503 with a clear message if AI is unavailable |
| GET | `/languages` | Supported languages, time limits and sandbox limits |
| GET | `/health` | `{"status", "database", "redis"}`; 503 when degraded |

`acceptance_rate` is accepted ÷ judged submissions for that problem across all users (0–1), or `null` if nobody has submitted yet. Only **Submit** attempts count; runs and server-side failures don't.

**Example:**

```bash
TOKEN=$(curl -s -X POST localhost:8080/api/v1/auth/register -H 'Content-Type: application/json' \
  -d '{"username":"demo","email":"codebox.demo@gmail.com","password":"password123"}' | jq -r .access_token)

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

`execution_time` is in **milliseconds** and `memory_used` is peak memory in **KB**. For judged submissions, `test_results` lists `{index, passed, status, time_ms, memory_kb, is_sample, message}`; only the sample case also includes `input`, `expected_output` and `actual_output`.

Errors always look like `{"detail": "human-readable message"}`: 400 unsupported language or empty code, 401 not signed in, 404, 409 username/email taken, 413 too large, 422 validation, 429 rate-limited, 503 database, queue or AI unavailable.

---

## Environment variables

Copy `.env.example` to `.env`. **Never commit `.env`.**

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `codebox` / *(required)* / `codebox` | Database credentials |
| `DATABASE_URL` | – | SQLAlchemy URL; its password must match `POSTGRES_PASSWORD` |
| `REDIS_URL` | `redis://redis:6379/0` | Job queue and rate limiter |
| `JWT_SECRET` | *(required, ≥ 32 chars)* | Token signing key |
| `OPENROUTER_API_KEY` | empty | Enables the AI assistant through [OpenRouter](https://openrouter.ai/keys); takes precedence over `OPENAI_API_KEY` |
| `OPENROUTER_MODEL` | `qwen/qwen3.8-27b:free` | Any id from <https://openrouter.ai/models> |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` | empty / `https://api.openai.com/v1` / `gpt-4o-mini` | Used when no OpenRouter key is set; works with any OpenAI-compatible API (Azure OpenAI, Groq, Ollama `http://host:11434/v1`, vLLM, …). With both keys empty, AI is off and everything else works |
| `EMAIL_CHECK_DELIVERABILITY` | `true` | Registration requires the email's domain to have a mail server (DNS/MX lookup) |
| `EXECUTION_TIMEOUT` | `2` | Seconds per test case (Java gets ×2 for JVM start-up) |
| `MEMORY_LIMIT` | `128m` | Memory per run container (no swap) |
| `CPU_LIMIT` | `0.5` | CPU cores per run container |
| `PIDS_LIMIT` | `64` | Max processes/threads per sandbox |
| `COMPILE_TIMEOUT` / `COMPILE_MEMORY_LIMIT` / `COMPILE_CPU_LIMIT` | `15` / `512m` / `1.0` | Limits for the separate compile container |
| `SANDBOX_RUNTIME` | empty | OCI runtime for sandboxes, e.g. `runsc` (gVisor must be installed on the host) |
| `WORKER_CONCURRENCY` | `2` | Programs executed in parallel |
| `FRONTEND_PORT` / `BACKEND_PORT` | `8080` / `8000` | Host ports (bound to 127.0.0.1) |

Other settings with sensible defaults live in `codebox/backend/app/config.py`: `MAX_SOURCE_BYTES`, `MAX_STDIN_BYTES`, `MAX_PENDING_EXECUTIONS_PER_USER`, `RATE_LIMIT_LOGIN_PER_MINUTE`, `RATE_LIMIT_EXECUTIONS_PER_MINUTE`, `RATE_LIMIT_AI_PER_MINUTE`, `STALE_EXECUTION_SECONDS`, `ACCESS_TOKEN_EXPIRE_MINUTES` (default 12 hours), `AI_TIMEOUT` and `CORS_ORIGINS`.

After changing `.env`, apply it with `docker compose up -d --force-recreate backend celery-worker`.

---

## Managing data

All data lives in PostgreSQL, in the Docker volume `codebox_pgdata`. The database isn't exposed outside Docker. Run these from the `codebox/` folder.

| Task | Command |
| --- | --- |
| SQL shell | `docker compose exec postgres psql -U codebox -d codebox` (then `\dt`, `SELECT username, email FROM users;`, `\q`) |
| Back up | `docker compose exec -T postgres pg_dump -U codebox codebox > backup.sql` |
| Restore | `docker compose exec -T postgres psql -U codebox -d codebox < backup.sql` |
| Delete all users and submissions, keep the problems | `docker compose exec postgres psql -U codebox -d codebox -c "TRUNCATE users, submissions, executions RESTART IDENTITY CASCADE;"` |
| Delete everything | `docker compose down -v && docker compose up -d` (the problems are recreated at start-up) |

Tables: `users`, `problems`, `test_cases` (hidden tests included), `submissions`, `executions`. Only bcrypt password hashes are stored. The `codebox_test` database is used by the test suite and is wiped on every run.

The problems are defined in code (`backend/app/seed/`) and synchronised into the database at every start-up, so edits made directly in the database are overwritten; change the seed files instead.

For a browser-based viewer, you can temporarily run [Adminer](https://www.adminer.org) on the internal network:

```bash
docker run -d --name codebox-adminer -p 127.0.0.1:8081:8080 --network codebox_web adminer
docker network connect codebox_data codebox-adminer
# open http://localhost:8081 — System: PostgreSQL, Server: postgres, User: codebox, Database: codebox
docker rm -f codebox-adminer   # when done
```

---

## Local development without Compose

Run PostgreSQL and Redis as throw-away containers, and the API, worker and frontend on the host (Python 3.10+, Node 20.19+), from the `codebox/` folder:

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

The suite has **245 tests**: 234 run by `pytest` (98 of them against real Docker sandboxes), plus 11 end-to-end tests that drive the running stack.

| File | Tests | What it covers | Needs |
| --- | --- | --- | --- |
| `test_auth.py` | 8 | Hashing, register/login, validation errors, expired/forged/unsigned tokens, protected routes | – |
| `test_email_checks.py` | 35 | Gmail username rules, typo suggestions, missing mail server, non-existent domains, throwaway providers, clear conflict messages | – |
| `test_api.py` | 21 | Login required for problems, no test data leaked, tags/solved/attempted/acceptance stats, execute/submit validation, 400/404/413/429/503 paths, stale jobs, cross-user isolation, history and pagination | – |
| `test_models.py` | 5 | Seed data (15 problems), relationships, cascades, indexes, idempotent seeding | – |
| `test_judge.py` | 6 | Output normalisation, verdicts, `4/5` counting, hidden data never exposed | – |
| `test_worker.py` | 7 | Job logic with a fake executor: run/submit, crashes, duplicate delivery, output capping | – |
| `test_ai.py` | 26 | Routing, minimal context, OpenRouter/OpenAI request format and headers, provider errors (401/402/429/5xx), timeouts, disabled fallback | – |
| `test_rate_limit.py` | 4 | Fixed window, fail-open, login brute force, execution spam | – |
| `test_executor_unit.py` | 24 | Limit parsing, status classification, language registry, Docker unavailable or image missing | – |
| `test_executor_docker.py` | 98 | **Real sandboxes**: every language, compile/runtime errors, TLE, MLE, output flood, non-root, no capabilities, no network, read-only FS, no socket, `/proc/1` protection, fork bomb, background processes, cleanup, container limits, and **all 60 reference solutions (15 problems × 4 languages) passing the hidden tests** | Docker + images |
| `e2e/test_stack.py` | 11 | Through nginx: health, all languages, limits, judging, history, cross-user isolation, email checks, AI fallback | Running stack |

**Recommended: run everything in Docker** (works the same on Windows):

```bash
docker compose --profile test run --rm tests       # runs against PostgreSQL (codebox_test database)
```

**End-to-end against the running stack:**

```bash
docker compose up -d --build
pip install -r backend/requirements-dev.txt
CODEBOX_E2E_URL=http://127.0.0.1:8080 pytest tests/e2e -v
```

**On the host** (SQLite; the Docker tests run if Docker and the images are available): `pip install -r backend/requirements-dev.txt && pytest`.

---

## Adding a new language

Example: Go.

1. **Image.** Create `executor/Dockerfiles/go/Dockerfile` from an official image. Install `python3` for the runner if the image lacks it, and copy the common block from an existing Dockerfile: the `sandbox` user 10001, `/sandbox`, stripped setuid bits, `COPY runner/runner.py`, `USER 10001:10001`, and `ENTRYPOINT ["python3","-I","/opt/codebox/runner.py"]`.
2. **Register it** in `executor/languages.py`:

   ```python
   Language(
       key="go", display_name="Go 1.23", image="codebox-sandbox-go:latest", monaco_id="go",
       layout=lambda src: Layout("main.go", ["./main"]),
       compile_cmd=lambda fn: ["go", "build", "-o", "main", fn],
       separate_compile=True, artifacts=["main"],
   )
   ```

   Compilers that need a writable cache should use `/tmp` (e.g. `ENV GOCACHE=/tmp/go-cache` in the image).
3. **Compose.** Add a `sandbox-go` build-only service like the others, and add it to the worker's `depends_on`.
4. **Frontend.** Add a label in `frontend/src/lib/format.ts` (`LANGUAGE_LABEL`), a template in `lib/templates.ts`, and the Monaco id in `components/CodeEditor.tsx`.
5. **Problems.** Add `go` starter code to every problem in `backend/app/seed/problems.py` and `extra_problems.py`, and a reference solution patch in `tests/solutions.py`. The Docker tests then check that Go passes every problem.
6. Run `docker compose up --build -d`, then `docker compose --profile test run --rm tests`.

---

## Known limitations

- **Container isolation is not VM isolation.** See [what this does not protect against](#what-this-does-not-protect-against). Use gVisor or microVMs for untrusted public deployments.
- **The worker holds the Docker socket**, which is equivalent to root on the host. Isolate it on a dedicated host or VM in production.
- **Email addresses aren't confirmed.** Registration checks that an address *could* exist, but can't prove a specific inbox exists or belongs to the user; only an emailed code could, and that isn't implemented. There is also no password reset.
- **Measurements are approximate.** Runtime is wall-clock time and depends on host load and the CPU quota. Memory is the process's peak and includes the runtime's baseline (JVM about 35 MB, Node about 45 MB).
- **Exact-output judging** after trailing-whitespace normalisation. There are no special checkers for floating-point tolerance or multiple valid answers; every problem has exactly one correct output.
- **Test cases of one submission share a container.** Each runs as a fresh process with a wiped `/tmp`, but files written to `/sandbox` persist between them.
- **Schema changes** use `create_all` plus a few idempotent `ALTER` statements at start-up; there are no migrations yet.
- **Sessions.** JWTs can't be revoked before they expire (12 hours) and are stored in `localStorage`, relying on the CSP to mitigate XSS.
- **AI.** Code is sent to the configured third-party provider; answers aren't streamed; free OpenRouter models can be rate-limited.
- **Rate limits** are fixed-window and fail open when Redis is down.
- **OOM detection** is most accurate on cgroup v2 hosts (current Docker Desktop and modern Linux); on cgroup v1 it falls back to exit-signal and stderr heuristics.

## Future improvements

- gVisor (`runsc`) by default, or a Firecracker-based execution tier; a dedicated execution host behind an authenticated socket proxy
- Pre-warmed sandbox containers to cut start-up time (especially for Java)
- Password reset and optional email confirmation; refresh tokens with revocation; httpOnly cookies; OAuth login
- Alembic migrations; an admin UI for writing problems and test cases; special checkers
- Results pushed over WebSockets/SSE instead of polling; streaming AI responses
- Leaderboards, contests, streaks, per-language resource profiles, multi-file projects
- CI (GitHub Actions) running the containerised test suite and building images on every push
- Prometheus metrics (queue depth, sandbox durations, verdict rates) and structured logs
