"""Cognitive Lens — Law 15: transferable reusable method of thinking."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nod_protocol.crypto.commitments import content_hash


class LicenseState(str, Enum):
    FREE = "free"
    LICENSED = "licensed"
    EXCLUSIVE = "exclusive"
    COMBINED = "combined"


@dataclass
class CognitiveLens:
    """A reusable, verifiable method abstracted from a specific discovery."""

    lens_id: str
    origin_nod_id: str
    method_signature: dict
    abstraction_level: float  # 0..1, how far from the specific discovery
    creator: str
    license_state: LicenseState = LicenseState.FREE
    holders: list[str] = field(default_factory=list)

    @classmethod
    def derive(cls, origin_nod_id: str, method_signature: dict, creator: str, abstraction_level: float) -> "CognitiveLens":
        """Law 15: representable when structure is sufficiently abstracted."""
        if abstraction_level < 0.5:
            raise ValueError("insufficient abstraction: method still bound to its discovery")
        lens_id = "LENS-" + content_hash({"origin": origin_nod_id, "sig": method_signature})[:16]
        return cls(lens_id=lens_id, origin_nod_id=origin_nod_id,
                   method_signature=method_signature, abstraction_level=abstraction_level, creator=creator)

    def license_to(self, agent: str, exclusive: bool = False) -> None:
        if self.license_state == LicenseState.EXCLUSIVE and self.holders:
            raise ValueError("exclusive lens already licensed")
        self.license_state = LicenseState.EXCLUSIVE if exclusive else LicenseState.LICENSED
        if agent not in self.holders:
            self.holders.append(agent)

    def combine(self, other: "CognitiveLens", operator: str, creator: str) -> "CognitiveLens":
        """Combine two lenses into a new lens asset."""
        combined = {
            "kind": "combination",
            "operator": operator,
            "left": self.lens_id,
            "right": other.lens_id,
        }
        return CognitiveLens(
            lens_id="LENS-" + content_hash(combined)[:16],
            origin_nod_id=self.origin_nod_id,
            method_signature={"combined": [self.method_signature, other.method_signature], "op": operator},
            abstraction_level=min(1.0, (self.abstraction_level + other.abstraction_level) / 2 + 0.1),
            creator=creator,
            license_state=LicenseState.COMBINED,
        )

    def to_dict(self) -> dict:
        return {
            "lens_id": self.lens_id,
            "origin_nod_id": self.origin_nod_id,
            "method_signature": self.method_signature,
            "abstraction_level": self.abstraction_level,
            "creator": self.creator,
            "license_state": self.license_state.value,
            "holders": self.holders,
        }
