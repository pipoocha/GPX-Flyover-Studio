from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProfileDefinition:
    key: str
    label: str
    description: str
    rules: dict[str, dict[str, Any]]
    base_settings: dict[str, Any]


@dataclass
class ProfileMatch:
    key: str
    label: str
    score: float
    confidence: float
    reasons: list[str]
    warnings: list[str]
    proposed_settings: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "score": float(self.score),
            "confidence": float(self.confidence),
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "proposed_settings": dict(self.proposed_settings),
        }
