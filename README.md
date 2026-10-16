# AegisTwin — attack-aware network defence lab

A working research core for a cybersecurity capstone. Models finite, evidence-backed transitions in an authorised synthetic network. It does **not** predict all attacks, infer vulnerabilities from ports, or estimate breach probabilities.

This checkout was empty at inspection. Names use `v2` for Compose projects and the local database to avoid collisions with a previous installation. Existing projects elsewhere are untouched.

## Run locally (Windows Command Prompt)

Python 3.12 and Node 22+ are required. Open Command Prompt in this folder:

```bat
cd /d C:\AegisTwin
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m alembic upgrade head
cd frontend
npm install
npm run build
cd ..
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8017
```

Keep that terminal running. In a **second** Command Prompt:

```bat
cd /d C:\AegisTwin
.venv\Scripts\python.exe -m backend.worker
```

Open http://127.0.0.1:8017. Register a local account (password at least 12 characters). Click **Load bundled lab**. No default credentials or AI key are needed. Local mode uses SQLite; Compose uses PostgreSQL. Run only one worker. A worker restart requeues interrupted jobs; cancelled jobs remain cancelled. Do not run the worker recovery command while another worker is active.

For UI development use `npm run dev` inside `frontend`; Vite proxies `/api` to port 8017. The production server serves the compiled frontend; rebuild and restart the API after frontend changes.

## Main scenario

1. Load the bundled lab on Overview.
2. Select **Excessive network exposure**. Open Attack analysis → Run deterministic analysis.
3. The initial `control:web` and `session:admin` are simulated assumptions. The model reaches `read:canary` through the exposed admin service. Expand the supporting chain to inspect prerequisites and evidence.
4. Open Defence planner. Choose budget 2 and exact search. The expected plan removes `web-admin`, blocks the canary target, and preserves proxy→web→API→database network connectivity.
5. Select **Overbroad access permission**. A test identity plus API reachability permits canary read. Budget 1 removes `user-read`.
6. **Segmentation blocks access** begins with control of the proxy, without assuming control of the app. No rule grants that capability, so the target is not reached. This is a closed-world model assumption, not proof of real security.
7. Event replay → Load labelled synthetic event → Step → Save replay session.
8. Reports → download JSON or HTML. Exports embed the exact snapshot, scenario, evidence and algorithm configuration.

## Docker application

Install Docker Desktop with WSL 2. Create `.env` containing a URL-safe, strong password, e.g. `POSTGRES_PASSWORD=` followed by your own generated value. This secret is never sent to the browser. Then:

```bat
docker compose up --build -d
docker compose logs app worker
```

Application: http://127.0.0.1:8017. PostgreSQL is not published to the host. Migration must succeed before app/worker start. The application network has no lab attachment. No Docker socket, host networking, privileged containers, or arbitrary command endpoint exists. Docker images are version-tagged, not digest-locked. `SECURE_COOKIES=false` is only for loopback HTTP; configure HTTPS and secure cookies before remote hosting. Internet deployment is outside this release's verified boundary.

## Isolated canary lab and actual observations

The bundled lab uses harmless HTTP canary services, including a synthetic record store rather than a full SQL target. All networks are Docker-internal. Only the reverse proxy is published, on loopback port 8097. Application storage PostgreSQL is separate from this lab.

```bat
docker compose -f lab\compose.yaml up --build -d
docker compose -f lab\compose.yaml exec -T web python probe.py > evaluation\lab-before.json
.venv\Scripts\python.exe -m scripts.compare_lab evaluation\lab-before.json --output evaluation\comparison-before.json
```

To test a predefined segmentation change, manually review it first: `lab/compose.segmented.yaml` removes web's data and management network attachments. Applying it is an actual configuration change. Only do this when you intend to modify this bundled lab:

```bat
docker compose -f lab\compose.yaml -f lab\compose.segmented.yaml up -d
docker compose -f lab\compose.yaml -f lab\compose.segmented.yaml exec -T web python probe.py > evaluation\lab-after.json
.venv\Scripts\python.exe -m scripts.compare_lab evaluation\lab-after.json --segmented --output evaluation\comparison-after.json
```

Requires Compose 2.24.4+ for `!override`. Restore the exposed baseline with `docker compose -f lab\compose.yaml up -d`. These fixed commands are run by the user locally; the web app cannot execute them. The probe only connects to three fixed bundled targets, validates resolved private IPs before connecting, uses one-second timeouts and serial rate-limited execution, and sends no exploit payload. Successful TCP connection validates connectivity only. Failed DNS/connectivity is preserved with its diagnostic context. No real lab observations are bundled as measured results until these commands run.

## Tests and reproducible evaluation

```bat
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\ruff.exe check backend tests scripts migrations lab
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m scripts.evaluate
.venv\Scripts\python.exe -m scripts.benchmark
cd frontend
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests require the API serving the production build and the worker in separate terminals. They register an isolated test workspace and exercise scenario cloning, analysis, evidence, optimisation, replay and report download. Unit/API tests use a temporary SQLite database. Evaluation writes real local timings and peak Python allocation measurements to `evaluation/results.json`; these are synthetic fixture results, not attack coverage or real-world accuracy. See `docs/verification.md` for what was actually executed in this session.

## API and data

Interactive OpenAPI documentation: http://127.0.0.1:8017/docs (its external Swagger UI assets require internet). Machine-readable schema: `/openapi.json`. See `docs/API.md`, `docs/architecture.md`, `docs/formal-model.md`, `docs/threat-model.md`, `docs/status.md`, and `docs/demo-and-interview.md`.

JSON and mixed-row CSV inventory imports are implemented. Use the exported snapshot's `data` object as the JSON inventory import format; preserve `schema_version: "1.0"`. CSV uses `row_type` values `asset`, `relationship` and `evidence`; its allowed columns are documented in `backend/imports.py`. Evidence lists use semicolons and booleans use `true`/`false`. Identity principals are assets of kind `principal`; permission, membership and authentication are separate typed relationship records. Versioned scenario/action/event contracts live in `backend/contracts.py`. There are no real credentials in lab scenarios.

## PostgreSQL without Docker

If PostgreSQL is installed locally, use the dedicated setup described in [database operations](docs/database.md):

```bat
.venv\Scripts\python.exe -m scripts.setup_postgres
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.check_database
```

Enter the administrator password only at the script's hidden local prompt. It creates a separate database and restricted application account and saves generated app credentials in ignored `.env.local`. Database selection is automatic for both API and worker. Settings shows the active engine and tenant-scoped domain table counts. Existing SQLite data remains untouched; it is not automatically transferred between database engines.
