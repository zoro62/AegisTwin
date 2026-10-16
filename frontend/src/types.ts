export type Asset = {
    id: string;
    label: string;
    kind: string;
    segment: string;
    critical: boolean;
};
export type Edge = {
    id: string;
    source: string;
    target: string;
    kind: string;
    evidence: string[];
    essential: boolean;
};
export type Evidence = {
    id: string;
    source: string;
    confidence: string;
    expires_at: string | null;
    collected_at?: string;
    method?: string;
    note: string;
};
export type Inventory = {
    name: string;
    assets: Asset[];
    relationships: Edge[];
    evidence: Evidence[];
};
export type Rule = {
    id: string;
    label: string;
    requires_any: string[][];
    effects: string[];
    relationships: string[];
    evidence: string[];
    assumptions: string;
};
export type Scenario = {
    name: string;
    snapshot_id: string;
    initial: string[];
    assumptions: string;
    rules: Rule[];
    targets: {
        asset_id: string;
        capability: string;
    }[];
};
export type Target = {
    asset_id: string;
    capability?: string;
    weight?: number;
    reachable: boolean;
    chains: string[][];
};
export type Result = {
    limits?: Record<string, unknown>;
    engine_version?: string;
    targets: Target[];
    truncated: boolean;
    warnings: string[];
    runtime_ms: number;
    states_explored: number;
    blocked: unknown[];
};
export type DefenceAction = {
    id: string;
    label: string;
    remove_relationships: string[];
    cost: number;
    cost_basis: string;
    impact: string;
    conflicts: string[];
    rollback: string;
};
export type Plan = {
    before: Result;
    after: Result;
    selected_actions: {
        id: string;
        label: string;
        impact: string;
    }[];
    cost: number;
    budget: number;
    optimality: string;
    connectivity: {
        relationship: string;
        preserved: boolean;
    }[];
    warnings: string[];
};
export type DomainRecord = {
    id: string;
    kind: string;
    created_at: string;
    content_hash: string;
    data: Record<string, unknown>;
};
export type LabEvent = {
    record_id: string;
    id: string;
    source: string;
    source_timestamp: string;
    asset_id: string;
    event_type: string;
    simulation: boolean;
    fields: Record<string, unknown>;
};
export type Job = {
    id: string;
    kind: string;
    status: string;
    error: string | null;
};
export type Evaluation = {
    validation: {
        dimensions: Record<string, {
            events: number;
            compared: number;
            discrepancies: number;
            real_observations: number;
            status: string;
        }>;
        comparisons: unknown[];
        limitations: string;
    };
    dataset: unknown[];
};
