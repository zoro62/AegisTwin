# Feature status and next acceptance criteria

Status is per release, not a claim that the entire requested roadmap is complete. “Tested” below refers to executed Python checks; browser/container checks are separately recorded in verification.md.

| Capability | Status | Evidence / remaining work |
|---|---|---|
| JSON/CSV inventory, typed assets/identity/relationships, provenance | Implemented; Python tested | Mixed-row CSV adapter; duplicate/dangling import checks |
| Immutable snapshots, relational tables, migrations | Implemented; SQLite/PostgreSQL tested | 17 projections, backfill, foreign keys, SQL history protection and restricted PostgreSQL role verified |
| Authentication, roles, workspace isolation, CSRF | Implemented; API tested | Remote hardening and complete audit coverage pending |
| Topology, identity and transition views | Implemented; browser smoke tested | Filters, display cap, neighbourhood focus and uncertainty styling; broader large-graph UX testing pending |
| Inventory register and evidence desk | Implemented; desktop/mobile browser tested | Search/filter/sort, asset/relationship inspector, filtered CSV export, evidence freshness and rule linkage |
| Saved analysis comparison | Implemented; browser tested | Asset/capability outcomes, provenance, input mismatch warning and explicit unknown state for limited searches |
| Scenario cloning and structured editing | Implemented; browser tested | Initial asset, capabilities, name and assumptions forms plus full JSON rule editing |
| AND/OR monotonic engine, bounded witnesses, evidence policy | Implemented; tested | More adversarial and scale tests needed |
| Defence actions, greedy and exact selection | Implemented; tested | Catalogue models relationship removal; executable actions excluded |
| Before/after saved plans and reports | Implemented; API/browser tested | Select actions, override costs, save named plans; readable HTML/JSON exports |
| Event import, deduplication, ordering, replay sessions | Implemented; API/browser tested | Replay and saved-state restoration; no enrolled live collector yet |
| Durable jobs, cancellation and restart | Implemented; API tested | One worker only; leases/multiworker support planned |
| Reproducible isolated canary lab | Implemented; user executed | Six services running per supplied output; data target is a canary HTTP store, not a SQL target |
| Fixed allowlisted connectivity probes | Implemented; baseline measured | Three real TCP checks matched baseline; post-defence observations pending |
| Synthetic evaluation with measured runtime/allocation | Implemented; executed | Three ground truth cases; broader scale/ablation curves planned |
| Model-vs-lab comparison CLI | Implemented; baseline evaluated | Three TCP checks, zero discrepancies; permission enforcement untested |
| Experiment UI and stored evaluation datasets | Implemented; API/browser tested | Real probe output imported and saved separately from synthetic transitions |
| Continuous updates / temporal access | Planned | Snapshot diff basics exist; expiry within runs and automatic affected reanalysis absent |
| Partial observability | Partial | Evidence strict/optimistic policy exists; full three-valued conditions and sensitivity UI absent |
| Deception | Partial | Harmless canary fixtures; instrumented interaction evidence/placement evaluation absent |
| Service preservation | Partial | Directed essential network paths enforced; end-to-end functional constraints absent |
| Multiple budgets / robust optimisation | Planned | Require measured cost-coverage curves and multi-scenario constraints |
| Collaborative reviews and approvals | Planned | Roles exist; comments/review decision history absent |
| Seeded scale generator | Partial; executed | Six small 4/8/12-node size/branching sweeps and evidence/permission ablations; larger representative workloads pending |
| Quantum research module | Planned / intentionally isolated | Define faithful simplified problem, exhaustive baseline and maintained simulator before implementation |
| Optional AI | Not implemented | Core requires no external API and transmits no evidence to AI |

## Phase acceptance gates

A: runnable on local PostgreSQL with browser verification and baseline Docker observations. Full application Compose deployment and a real SQL lab target remain unverified. B: finite rule engine and bounded analysis tested; broader independent ground truth remains desirable. C: counterfactual planning works end to end; richer functional service constraints and executable lab changes remain future work. D: replay and saved evaluations work with real baseline TCP observations; independent permission enforcement and after-defence connectivity are still required for full lab validation. Advanced phase E and quantum research are not claimed complete.
