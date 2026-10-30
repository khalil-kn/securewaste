"""True PDF redaction with verification (FR-25 → FR-27, ADR-0009). Owner: Milestone 4."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RedactionTarget:
    """Exists in memory only during one redaction request — it holds the raw value."""

    finding_id: str
    page_number: int
    value: str


@dataclass
class RedactionResult:
    status: str  # verified / incomplete / failed
    redacted: list[str] = field(default_factory=list)  # finding ids
    unmappable: list[str] = field(default_factory=list)
    still_present: list[str] = field(default_factory=list)


def redact(src: Path, dst: Path, targets: list[RedactionTarget]) -> RedactionResult:
    """search_for → add_redact_annot → apply_redactions, scrub metadata, save to dst, then verify."""
    raise NotImplementedError("Milestone 4")
