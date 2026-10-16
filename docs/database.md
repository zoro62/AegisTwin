# Database implementation and operations

The application supports SQLite for a self-contained local run and PostgreSQL for the full server deployment. PostgreSQL 18 was found already installed and listening on localhost in this environment; Docker is unnecessary for using that server. Its administrator password is not known to the application or this session.

## Configure existing local PostgreSQL (Command Prompt)

```bat
cd /d C:\AegisTwin
.venv\Scripts\python.exe -m scripts.setup_postgres
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.check_database
```

The setup script prompts for the local administrator's credentials using hidden input; it does not save them. It creates only a new `aegistwin_v2` database and `aegistwin_v2_app` login with no superuser, role-creation or database-creation privileges. If either name already exists it stops without altering existing data. A generated application password is stored in ignored `.env.local`. Back up that file securely. Do not paste it into chat or commit it. Setting `DATABASE_URL` in the terminal overrides `.env.local`; Compose supplies its own URL. SQLite data is preserved when selecting PostgreSQL, but is not automatically copied across engines. Import existing inventory JSON and recreate scenarios if migrating a populated local SQLite workspace.

## Schema

`users`, `workspaces`, `memberships`, `sessions`: account/workspace control. `records`: canonical immutable, SHA-256-addressed versioned domain documents. `snapshot_elements`: generic indexed snapshot projection, retained for compatibility. `events`: idempotent source events with ingestion timestamps. `jobs`: mutable durable queue state.

Seventeen named relational projection tables persist the domain: `inventory_snapshots`, `assets`, `services`, `principals`, `permissions`, `relationships`, `evidence_records`, `scenario_definitions`, `initial_capabilities`, `transition_rules`, `critical_targets`, `defensive_actions`, `analysis_runs`, `optimisation_runs`, `replay_sessions`, `evaluation_datasets`, `evaluation_results`.

The projections contain typed query fields plus complete JSON payloads, not fully normalised decompositions of every rule clause and evidence list. Each row references its canonical record by workspace and record ID. Snapshot-scoped rows also reference the exact snapshot record. Rules belong to an immutable scenario version. API validation checks the semantic kinds/references; database foreign keys additionally prevent cross-workspace snapshot references. Source and target external asset identifiers are validated by the inventory contract rather than individual SQL foreign keys.

Record creation and every projection insert share one database transaction. A validation error or failed insert rolls back the complete import. Migration 0002 backfills projections for historical records. Migration 0003 installs SQL triggers preventing UPDATE/DELETE of history, events and projections even through raw SQL. Jobs, sessions and memberships remain mutable. A database owner can disable/drop triggers; append-only history is an application/database integrity control, not tamper-proof attestation against the owner.

## Migrations and checks

0001 is frozen initial DDL. 0002 adds indexes, foreign keys and domain projections with a frozen backfill adapter. 0003 adds append-only triggers on SQLite/PostgreSQL. No migration imports current application ORM metadata. 0002 requires an online migration because it reflects and backfills existing records; downgrade intentionally refuses data-destructive schema rollback. Take a backup first, then restore it to a separate database if rollback is needed.

```bat
.venv\Scripts\python.exe -m alembic current
.venv\Scripts\python.exe -m alembic check
.venv\Scripts\python.exe -m scripts.backup_database
```

SQLite backup uses the online backup API and verifies database integrity. PostgreSQL uses installed `pg_dump` custom format; the password is passed through the child process environment rather than command-line arguments. Backups contain sensitive account/workspace data and are ignored by version control. Restore PostgreSQL into a **new empty database** with `pg_restore`; never overwrite a live database casually. Application credentials own this dedicated database to support migrations; a future production deployment should separate a schema-owner migration role from a narrower runtime role.

## Verification boundary

SQLite tests migrate an actual database from revision 0001, insert a historical inventory, upgrade/backfill, verify row counts, reject cross-workspace foreign keys and reject direct SQL history updates/deletes. API tests check tenant-scoped table counts and paged snapshot queries. PostgreSQL is configured at migration 0003. Live browser workflows and rolled-back SQL guard checks passed; see evaluation/postgres-verification.json. To run the migration test on PostgreSQL, set `TEST_DATABASE_URL` to a freshly created dedicated empty disposable database and run `python -m pytest tests/test_database.py -q`; never use the application database for this test.
