"""Convert only the fixed bundled probe format into provenance-preserving events."""

from datetime import datetime, timezone
from typing import Literal
from pydantic import Field, model_validator, field_validator
from .contracts import Contract, Event

DESTINATIONS = {
    "web-api": ("api", "api"),
    "web-db": ("database", "db"),
    "web-admin": ("admin", "admin"),
}


class ProbeResult(Contract):
    relationship_id: Literal["web-api", "web-db", "web-admin"]
    destination: Literal["api", "database", "admin"]
    port: Literal[8080]
    success: bool
    error: str | None = Field(default=None, max_length=2000)
    runtime_ms: float = Field(ge=0, le=60000, allow_inf_nan=False)

    @model_validator(mode="after")
    def fixed_destination(self):
        if DESTINATIONS[self.relationship_id][0] != self.destination:
            raise ValueError("destination does not match bundled probe relationship")
        return self


class ProbeObservations(Contract):
    schema_version: Literal["1.0"]
    source: Literal["bundled-web-probe"]
    observed_at: datetime
    simulation: Literal[False]
    dimension: Literal["connectivity"]
    results: list[ProbeResult] = Field(min_length=3, max_length=3)
    limitation: str = Field(max_length=1800)

    @field_validator("observed_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("observation timestamp requires timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def complete_fixed_checks(self):
        if {r.relationship_id for r in self.results} != set(DESTINATIONS):
            raise ValueError("probe must include each fixed relationship exactly once")
        return self

    def events(self):
        stamp = self.observed_at.strftime("%Y%m%dT%H%M%S%fZ")
        return [
            Event(
                id=stamp + ":" + r.relationship_id,
                source=self.source,
                source_timestamp=self.observed_at,
                asset_id=DESTINATIONS[r.relationship_id][1],
                event_type="connectivity",
                simulation=False,
                fields={
                    "relationship_id": r.relationship_id,
                    "success": r.success,
                    "error": r.error or "",
                    "runtime_microseconds": round(r.runtime_ms * 1000),
                },
                provenance="User-uploaded output from fixed bundled TCP checks. No cryptographic collector attestation. "
                + self.limitation,
            )
            for r in self.results
        ]


class ProbeImport(Contract):
    snapshot_id: str
    observations: ProbeObservations
