"""Versioned, bounded, closed-world input contracts. No imported executable code."""

from datetime import datetime, timezone
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def now():
    return datetime.now(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Entity(Contract):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.:-]{0,95}$")
    label: str = Field(min_length=1, max_length=160)
    kind: Literal[
        "host", "service", "database", "admin", "principal", "resource", "segment"
    ]
    segment: str = Field(default="lab", max_length=80)
    critical: bool = False


class Evidence(Contract):
    id: str = Field(pattern=r"^[a-z0-9_.:-]{1,96}$")
    source: str = Field(min_length=1, max_length=200)
    collected_at: datetime
    expires_at: datetime | None = None
    confidence: Literal["confirmed", "candidate", "uncertain", "conflicting"]
    method: Literal["imported", "observed", "asserted"]
    note: str = Field(max_length=2000)

    @field_validator("collected_at", "expires_at")
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamps require timezone")
        return value.astimezone(timezone.utc) if value else None


class Relationship(Contract):
    id: str = Field(pattern=r"^[a-z0-9_.:-]{1,96}$")
    source: str
    target: str
    kind: Literal[
        "network",
        "exposure",
        "authentication",
        "membership",
        "permission",
        "dependency",
        "communication",
    ]
    evidence: list[str] = Field(min_length=1, max_length=50)
    essential: bool = False


class Inventory(Contract):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1, max_length=160)
    assets: list[Entity] = Field(min_length=1, max_length=2000)
    evidence: list[Evidence] = Field(max_length=10000)
    relationships: list[Relationship] = Field(max_length=10000)

    @model_validator(mode="after")
    def references(self):
        for values in (self.assets, self.evidence, self.relationships):
            if len({v.id for v in values}) != len(values):
                raise ValueError(
                    "duplicate identifiers; correct ambiguous records before import"
                )
        assets = {a.id for a in self.assets}
        evidence = {e.id for e in self.evidence}
        for edge in self.relationships:
            if (
                edge.source not in assets
                or edge.target not in assets
                or not set(edge.evidence) <= evidence
            ):
                raise ValueError(f"dangling reference: {edge.id}")
        return self


class Rule(Contract):
    id: str = Field(pattern=r"^[a-z0-9_.:-]{1,96}$")
    version: Literal["1.0"] = "1.0"
    label: str = Field(max_length=160)
    # OR of AND clauses; each clause must be satisfied in ONE reachable state.
    requires_any: list[list[str]] = Field(min_length=1, max_length=20)
    relationships: list[str] = Field(default_factory=list, max_length=30)
    effects: list[str] = Field(min_length=1, max_length=20)
    evidence: list[str] = Field(min_length=1, max_length=30)
    assumptions: str = Field(min_length=1, max_length=2000)

    @field_validator("requires_any")
    @classmethod
    def nonempty_clauses(cls, value):
        if any(not c or len(c) > 30 for c in value):
            raise ValueError("AND clauses must contain 1..30 capabilities")
        return value


class Target(Contract):
    asset_id: str
    capability: str = Field(min_length=1, max_length=160)
    weight: int = Field(default=1, ge=1, le=100)


class Scenario(Contract):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1, max_length=160)
    snapshot_id: str
    initial: list[str] = Field(min_length=1, max_length=100)
    assumptions: str = Field(min_length=1, max_length=4000)
    targets: list[Target] = Field(min_length=1, max_length=50)
    rules: list[Rule] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_rules(self):
        if len({r.id for r in self.rules}) != len(self.rules):
            raise ValueError("duplicate rule identifiers")
        return self


class Limits(Contract):
    evidence_at: datetime | None = None
    max_depth: int = Field(default=12, ge=1, le=30)
    max_states: int = Field(default=5000, ge=1, le=20000)
    time_ms: int = Field(default=2000, ge=1, le=5000)
    top_k: int = Field(default=3, ge=1, le=10)
    evidence_policy: Literal["confirmed", "optimistic"] = "confirmed"

    @field_validator("evidence_at")
    @classmethod
    def aware(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("evidence_at requires timezone")
        return value.astimezone(timezone.utc) if value else None


class Action(Contract):
    id: str = Field(pattern=r"^[a-z0-9_.:-]{1,96}$")
    label: str = Field(min_length=1, max_length=160)
    remove_relationships: list[str] = Field(min_length=1, max_length=30)
    cost: int = Field(ge=0, le=100000)
    cost_basis: Literal["estimated", "measured", "user-specified"] = "estimated"
    impact: str = Field(min_length=1, max_length=1000)
    conflicts: list[str] = Field(default_factory=list, max_length=30)
    rollback: str = Field(min_length=1, max_length=1000)


class AnalysisRequest(Contract):
    scenario_id: str
    limits: Limits = Field(default_factory=Limits)
    removed: list[str] = Field(default_factory=list, max_length=100)


class PlanRequest(Contract):
    scenario_id: str
    name: str = Field(default="Defence plan", max_length=160)
    budget: int = Field(default=3, ge=0, le=100000)
    actions: list[Action] = Field(min_length=1, max_length=16)
    method: Literal["exact", "greedy"] = "exact"
    limits: Limits = Field(default_factory=Limits)

    @model_validator(mode="after")
    def unique(self):
        if len({a.id for a in self.actions}) != len(self.actions):
            raise ValueError("duplicate actions")
        ids = {a.id for a in self.actions}
        if any(not set(a.conflicts) <= ids for a in self.actions):
            raise ValueError("unknown conflict action")
        return self


class Event(Contract):
    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(pattern=r"^[a-zA-Z0-9_.:-]{1,96}$")
    source: str = Field(min_length=1, max_length=160)
    source_timestamp: datetime
    asset_id: str
    principal_id: str | None = None
    event_type: Literal["connectivity", "permission", "synthetic_transition", "canary"]
    fields: dict[str, str | bool | int] = Field(max_length=30)
    simulation: bool
    provenance: str = Field(min_length=1, max_length=2000)

    @field_validator("source_timestamp")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("timestamp requires timezone")
        return value.astimezone(timezone.utc)


def validate_scenario(scenario: Scenario, inventory: Inventory):
    assets = {a.id for a in inventory.assets}
    edges = {e.id for e in inventory.relationships}
    evidence = {e.id for e in inventory.evidence}
    if any(t.asset_id not in assets for t in scenario.targets):
        raise ValueError("unknown critical target")
    capabilities = scenario.initial + [t.capability for t in scenario.targets]
    for rule in scenario.rules:
        if not set(rule.relationships) <= edges or not set(rule.evidence) <= evidence:
            raise ValueError(f"unknown rule evidence or relationship: {rule.id}")
        capabilities.extend(
            rule.effects + [c for clause in rule.requires_any for c in clause]
        )
    if any(not re.fullmatch(r"[a-z0-9_.:-]{1,160}", cap) for cap in capabilities):
        raise ValueError(
            "capability identifiers must be canonical and contain no secrets"
        )
