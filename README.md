# DSA Studio

An offline-first practice platform for data structures and algorithms: a curated
problem library, an in-browser editor that actually runs your code in five
languages, sheets you can track yourself against, and a progress history.

Everything runs on your own machine. There are no CDN requests, no external auth
provider, no telemetry — the page you open is served by the same process that
compiles your solution, and the data lives in a SQLite file you own.

---

## Documentation

**[`docs/DSA-Studio-User-Guide.pdf`](docs/DSA-Studio-User-Guide.pdf)** — the complete
user manual (35 pages): what the platform is, how to use every screen, how to write
solutions in each language, how it was built, how to run and deploy it, the API, and
troubleshooting.

Regenerate it after editing the source:

```bash
weasyprint docs/DSA-Studio-User-Guide.html docs/DSA-Studio-User-Guide.pdf
```

---

## What it does

| Area | Behaviour |
| --- | --- |
| Library | 440 problems across 4 sheets, 153 starter problems with real test cases, searchable and filterable by difficulty, domain, tag and sheet |
| Editor | Python, JavaScript, C++, Java and C; samples, custom inputs, full submission against every case |
| Verdicts | accepted, wrong answer, compilation error, runtime error, time/memory limit exceeded, per-case detail with expected vs actual |
| Progress | per-problem status (untouched / attempted / solved), attempt counts, difficulty and domain breakdowns |
| Sheets | Striver A2Z, Striver Old, Love Babbar and a starter sheet, with solved/attempted markers inline |
| Offline | service worker caches the shell; the plain-textarea editor needs no network at all |
| Extras | per-case memory and timing, heuristic complexity estimate of your own code, saved code per language |

## Quick start (laptop, no Docker)

```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

./venv/bin/python manage.py migrate
./venv/bin/python manage.py seed_dsa_data      # languages + 4 sheets, idempotent
./venv/bin/python manage.py createsuperuser
./venv/bin/python manage.py runserver
```

Open <http://localhost:8000/>, register a user, and press **Run**.

Re-running `seed_dsa_data` is safe: problems and test cases are matched on a
canonical key and updated in place, so a re-import never duplicates anything or
loses your progress.

### Language toolchains

The platform ships language *rows* for all five languages, but each one needs a
toolchain on the host. Anything missing simply fails to compile in that language
until you install it:

| Language | Needs | Debian/Ubuntu |
| --- | --- | --- |
| Python | interpreter 3.11+ | `python3` |
| JavaScript | node | `nodejs` |
| C++ | g++ 9+ | `g++` |
| Java | JDK 11+ | `default-jdk-headless` |
| C | gcc + headers | `build-essential` |

Disable a language you do not have in **Admin → Languages** (uncheck *enabled*)
and it disappears from the editor and the API.

## Docker

```bash
docker compose up --build            # http://localhost:8000
```

The image installs every toolchain above and runs the app as an unprivileged
user. For stronger isolation, run submissions inside throwaway containers:

```bash
DSA_EXECUTION_BACKEND=docker docker compose up --build
```

The database lives in a named volume, so `docker compose down` keeps your data.

## How a submission is judged

1. `POST /api/run/` or `/api/submit/` with `{problem, language, code, custom_cases}`.
2. The service picks the cases (samples for *run*, everything for *submit*),
   renders the language-specific harness, compiles once, then runs each case with
   its own wall-clock and memory limit.
3. Output is compared exactly, or unordered, or by a semantic checker.
4. *Submit* stores the code, the verdict, per-case results, timings and the
   complexity estimate, and updates your progress row.

### Function mode vs stdin mode

Most problems are **function mode**: a test case is a JSON array with one item
per declared parameter, and the answer is JSON on stdout.

```json
[[2, 7, 11, 15], 9]   ->  [0, 1]
```

The harness supplies the node types (`ListNode`, `TreeNode`), the argument
conversions and the printing, so you only write the function the platform asks
for. Problems marked *stdin mode* get the raw test data instead.

### C conventions

C cannot return an array with its length, so the harness uses these conventions:

```c
/* vector in:  pointer + length, passed straight after the pointer */
int* twoSum(int* nums, int nums_len, int target);

/* vector out: return the pointer and publish the length in a global */
int twoSum_len;          /* declared by the harness */

/* matrix in:  pointer + rows + cols */
int** grid(int** board, int rows, int cols);

/* matrix out: rows in the global; each row is terminated by the typed sentinel */
int grid_rows;
int DSA_ROW_END_LONG;    /* or _INT / _DOUBLE; NULL for string rows */
```

### Semantic checkers

Some problems are checked by meaning rather than by string equality. A test case
stores a checker name (currently `n_queens`); the checker accepts one valid board
or a list of distinct valid boards, and treats an empty answer as valid only for
`n` in {2, 3}.

### Complexity estimates are heuristics

The estimate shown next to your code is a best-effort reading of the source
(loop depth, recursion, hash tables, sorts), labelled Low/Medium/High confidence.
It is never a measurement, and it is stored separately from the reference answer.

## Configuration

Copy `.env.example` to `.env` (or export the variables) — every one is optional.
The useful ones:

| Variable | Default | Meaning |
| --- | --- | --- |
| `DSA_SECRET_KEY` | random per process | pin it to keep sessions across restarts |
| `DSA_DEBUG` | `1` | set `0` for anything shared |
| `DSA_HTTPS` | `0` | `1` = secure cookies, HSTS, no DEBUG |
| `DSA_DB_ENGINE` | `sqlite` | or `postgresql` |
| `DSA_EXECUTION_BACKEND` | `subprocess` | or `docker` |
| `DSA_TIME_LIMIT` | `5` | seconds per test case |
| `DSA_BATCH_TIME_LIMIT` | `30` | seconds for a whole submission |
| `DSA_MEMORY_LIMIT_MB` | `512` | address-space/heap cap per case |
| `DSA_ALLOWED_HOSTS`, `DSA_CSRF_ORIGINS` | localhost | comma-separated |

With no `DSA_SECRET_KEY` set, a random key is generated at boot: an install never
ships a shared secret, at the cost of signing people out when the server restarts.

## Command reference

```bash
./venv/bin/python manage.py seed_dsa_data --dry-run     # validate the data
./venv/bin/python manage.py seed_dsa_data --content-only # starter sheet only
./venv/bin/python manage.py import_sheet path/to/sheet.json
./venv/bin/python manage.py test                          # full test suite
./venv/bin/python manage.py test apps.execution          # execution only
./venv/bin/python manage.py check --deploy                # deployment warnings
./venv/bin/python tools/build_sheet_data.py               # regenerate data/
```

## Layout

```
apps/
  accounts/    local auth, settings, template context
  dashboard/   landing page
  problems/    problem, test case, sheet-entry, preference models + pages
  sheets/      curated problem lists
  submissions/ submission history and per-case results
  progress/    per-user solving status
  execution/   runners, harnesses, sandboxes, checkers, JSON API
  imports/     data import/seed pipeline
config/        settings, urls, wsgi/asgi
data/          generated sheet + sample JSON
static/        css, js, icons (no CDN, no bundler)
templates/     server-rendered pages
tools/         data build scripts
```

## Safety notes

Submitted code is not trusted: it runs as a subprocess in a throwaway directory
with an address-space cap, a wall-clock timeout, an output cap and an explicit
environment. That is enough for a personal laptop and not enough for a shared
host — use `DSA_EXECUTION_BACKEND=docker` or a container-per-run setup if other
people can reach your instance.
