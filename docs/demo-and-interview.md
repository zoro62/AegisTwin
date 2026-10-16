# Five-minute capstone demonstration

0:00–0:45: Explain the boundary: authorised lab, synthetic records, explicit compromise assumptions. Register, load lab, inspect inventory provenance and topology. Differentiate a network edge from permission/authentication.

0:45–1:45: Choose Excessive network exposure and run analysis. Expand canary witness. Explain that reach-admin AND a simulated admin session are both required to read. Show snapshot ID and rule evidence. No exploit ran.

1:45–2:45: Set budget 2 and run exact defence selection. Remove web→admin; compare reachable targets and preserved essential network paths. Explain estimated cost and counterfactual-only behaviour. Change to Overbroad access permission; demonstrate least privilege at cost 1.

2:45–3:30: Select Segmentation blocks access. Show absence of a transition from proxy control to app control. Explain closed-world assumptions and why not-reached is weaker than secure.

3:30–4:15: Load synthetic event, step/play timeline, inspect correlation candidates and simulation label. Explain source vs ingestion time and duplicate handling. Save replay state.

4:15–5:00: Export HTML/JSON. Open measured synthetic evaluation. If Docker observations have actually been collected, show the before/after connectivity comparison separately; otherwise explicitly say this validation is pending. Finish with model limits and remaining work.

# Interview notes

Why capability states instead of graph shortest paths? AND prerequisites must hold together; a path over independent permission/network arrows can invent an attack. State transitions preserve conjunction, monotonic accumulation and explicit evidence.

Why relational storage plus NetworkX? Snapshot-scoped entities and access control fit a relational store; small graph path constraints are in-memory. There is no workload justifying Neo4j yet.

Why exact plus greedy? Exact enumeration gives a trusted small-instance baseline. Greedy is scalable within a small catalogue but can miss synergistic action sets. Fewer path witnesses is never used as the security objective.

Why immutable documents with projections? Historical runs retain exact schema-versioned input and hash; relational projections enable indexed snapshot queries. This is simpler than reconstructing history from mutable current entities, but dedicated normalised tables and database-enforced immutability would be needed at larger scale.

Why separate lab orchestration? An application that accepts untrusted imports must not control the host Docker daemon. The user runs fixed, reviewable Compose operations locally; app and worker have no orchestration channel.

What does the evaluation prove? Only correctness on declared synthetic ground-truth cases and local measured runtimes. TCP checks prove reachability, not exploitability. Generalisation, unseen attacks, real-world breach probability and quantum advantage are not claimed.
