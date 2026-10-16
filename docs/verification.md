# Executed verification - 2026-10-16

Environment: Windows, Python 3.12.4, PostgreSQL 18, Node 25.8.1. Original workspace empty. The user installed dependencies, Chromium, PostgreSQL and Docker Desktop after the initial restricted setup.

## Automated checks

- `python -m pytest -q`: **15 passed**, one upstream Starlette/AnyIO deprecation warning. Covers AND/OR rules, cycles, evidence policies, bounds, optimisation constraints, evidence-time reproducibility, invalid imports, CSV, tenant/role isolation, jobs, events, corrections, reports and migrated database guards.
- `ruff check backend tests scripts migrations lab`: passed.
- `python -m pip check`: no broken requirements.
- `python -m compileall -q backend scripts tests lab migrations`: passed.
- `python -m alembic upgrade head`: SQLite migrations executed here; PostgreSQL migrations executed successfully by the user.
- `python -m alembic check`: PostgreSQL at **0003**, no pending schema operations.
- `python -m scripts.verify_postgres`: restricted application role verified; direct SQL history update and cross-workspace foreign key rejected. Verification rows rolled back. Artifact: `evaluation/postgres-verification.json`.
- `npm run build`: TypeScript and Vite production build passed; vendor chunks split without an oversized-chunk warning.
- `npm run test:e2e`: **2 Chromium tests passed** against the PostgreSQL-backed API and worker. The desktop flow covers registration, scenario save, analysis, evidence, limited-search run comparison, defence, replay/restoration, real probe import, evaluation, graph, settings, reports, correction, asset inspection/CSV export and evidence desk. The mobile flow checks inventory/evidence usability and no page overflow at 390 pixels.
- `npm run lint`: strict TypeScript checking with unused-local/parameter checks passed after cleanup.
- Live frontend/API smoke checks: `/api/health` and `/openapi.json` returned 200 on loopback port 8017.

Initial browser runs found a locator ambiguity, a replay loading race and display separator encoding; these were corrected and subsequent runs passed. Browser-generated test accounts/workspaces remain isolated so their immutable results are reproducible. They are separate from the user's own account.

## Measured experiments

- `python -m scripts.evaluate`: **3/3 declared synthetic cases matched**, actual timings/state counts/allocation peaks and solver outcomes in `evaluation/results.json`. Fixture correctness is not real-world attack accuracy.
- `python -m scripts.benchmark`: **6 seeded small size/branching cases**, none truncated. Permission/topology and uncertain-evidence ablations in `evaluation/benchmark.json`.
- `python -m scripts.compare_lab evaluation/lab-before.json --output evaluation/comparison-before.json`: **3 real TCP observations, 0 connectivity discrepancies**. Web connected to API, database canary and admin canary. The user executed the probe inside Docker; its output was inspected and compared here.
- SQLite online backup and integrity check succeeded. PostgreSQL pg_dump tooling is implemented but has not been executed in this session.

## Docker and validation boundaries

The user built and started all six lab services. Proxy initially failed on an unwritable PID path; custom PID/temp paths were moved to /tmp and a web dependency added. The supplied subsequent listing showed all six running. Docker commands remain unavailable from the restricted agent environment; orchestration was user-executed.

TCP checks do not validate authentication or compromise. Real permission enforcement, canary interaction telemetry, after-segmentation observations, full application Compose deployment and automatic lab orchestration are **not verified**. No exploit was performed. Optional quantum/AI and most advanced research features remain outside this release.
