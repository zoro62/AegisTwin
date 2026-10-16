# API guide

All domain routes have prefix `/api/workspaces/{workspace_id}`. `/api/register` creates an account and isolated administrator workspace; `/api/login` sets the HttpOnly session cookie and returns a CSRF token; `/api/me` returns memberships and CSRF. Send `x-csrf-token` for authenticated writes. `/api/logout` revokes the session. JSON request limits: 2 MB. Standard FastAPI 422 validation errors describe contract violations.

| Method and suffix | Behaviour |
|---|---|
| GET `/records` | Immutable domain documents in this workspace |
| POST `/seed` | Idempotently import synthetic lab, scenarios and actions |
| POST `/snapshots` | Validate schema-1.0 inventory and create immutable snapshot |
| POST `/snapshots/csv` | Validate `{name,csv}` mixed-row CSV inventory |
| POST `/snapshots/{id}/corrections` | Create new snapshot with correction reason and asserted provenance |
| GET `/snapshots/{id}/elements` | Paged relational assets/services/principals/permissions/relationships/evidence queries |
| GET `/database` | Active engine and workspace-scoped domain table counts; no credentials |
| GET `/members` | Workspace member email/role list |
| GET `/audit` | Administrator-only immutable audit history |
| POST `/scenarios` | Validate references and save new scenario; clone by resubmitting edited content |
| POST `/analysis` | Queue `{scenario_id, limits?, removed?}`; returns job ID |
| POST `/plans` | Queue `{scenario_id, budget, actions, method, limits?}` |
| POST `/evaluations` | Queue analysis plus snapshot-event comparison; store exact event dataset |
| GET `/jobs` | Status, error, result reference |
| POST `/jobs/{id}/cancel` | Cancel queued/running job |
| POST `/events` | `{snapshot_id, events:[...]}`; dedupe source+ID within snapshot; conflicting payload rejected |
| POST `/lab-observations` | `{snapshot_id, observations}`; validate fixed probe output and preserve real/synthetic distinction |
| GET `/events?snapshot_id=...` | Stable ordered event stream |
| POST `/replays` | Save snapshot, source-qualified event ID order and cursor |
| GET `/reports/{id}?format=json` | Exact report data, scenario and snapshot |
| GET `/reports/{id}?format=html` | Escaped downloadable readable report |
| POST `/members` | Administrator assigns existing registered user's viewer/analyst/admin role |

Viewer reads only. Analyst creates snapshots, scenarios, events and runs. Administrator also changes other users' roles. Cross-workspace resources return 404. No API accepts a shell command, network target URL or real credentials for an attacker scenario.

The canonical contracts are `backend/contracts.py` and generated `/openapi.json`; UI-only fields are not silently accepted. Event timestamps require time zones. Event IDs are idempotent per workspace, snapshot and source. Event ingestion time is server-assigned. Correlation preserves candidate rule IDs; a synthetic event does not validate a real attack transition.
