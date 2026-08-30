"""NØD-Sync — cognitive state resolution.

The critical property that distinguishes NØD from blockchain-style systems:

    blockchain:  Chain A OR Chain B   (a fork is a failure)
    NØD:         Chain A AND Chain B  (competing interpretations coexist)

Coexisting states are resolved by *protocol recognition* — verification
strength, independence, utility — not by timestamp. The Current State
Pointer advances only when the protocol's confidence function says so.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nod_protocol.sync.state import StateEvent, GlobalState

# confidence weights for resolution (v = verification, s = independence,
# u = downstream utility, a = adoption)
DEFAULT_WEIGHTS = {"v": 0.5, "s": 0.25, "u": 0.15, "a": 0.10}


@dataclass
class Resolution:
    """Result of resolving competing candidate states."""

    accepted: list[StateEvent] = field(default_factory=list)
    pointer: str = ""                      # chosen current state nod id
    coexisting: list[str] = field(default_factory=list)  # all valid states kept
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "accepted": [e.event_hash for e in self.accepted],
            "pointer": self.pointer,
            "coexisting": self.coexisting,
            "note": self.note,
        }


def confidence(event: StateEvent, weights: dict | None = None) -> float:
    w = weights or DEFAULT_WEIGHTS
    return (
        w["v"] * event.verification_strength
        + w["s"] * event.independent_support
        + w["u"] * event.payload.get("utility", 0.0)
        + w["a"] * event.payload.get("adoption", 0.0)
    )


def resolve_fork(candidates: list[StateEvent], weights: dict | None = None) -> Resolution:
    """Resolve competing branches WITHOUT destroying either.

    - Every candidate that passes validity is *accepted* (AND semantics).
    - A single pointer is chosen by confidence (the "latest valid state").
    - All valid states remain in the co-existing set, preserving full
      lineage. If no candidate meets validity, nothing is accepted.
    """
    w = weights or DEFAULT_WEIGHTS
    valid = [e for e in candidates if e.is_valid_proposal()]
    resolution = Resolution(coexisting=[e.nod_id for e in valid])

    if not valid:
        resolution.note = "no valid candidate; state unchanged"
        return resolution

    resolution.accepted = valid
    best = max(valid, key=lambda e: confidence(e, w))
    resolution.pointer = best.nod_id
    resolution.note = (
        f"fork preserved: {len(valid)} coexisting states; "
        f"pointer = highest-confidence state ({best.nod_id}, conf={confidence(best, w):.3f})"
    )
    return resolution


def latest_valid_pointer(state: GlobalState, weights: dict | None = None) -> str:
    """The protocol-recognized pointer for a state — never the raw clock."""
    active = list(state.events.values())
    if not active:
        return state.head_nod
    best = max(active, key=lambda e: confidence(e, weights))
    return best.nod_id
