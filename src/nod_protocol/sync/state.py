"""NØD-Sync — shared global cognitive state.

The core primitive that distinguishes a *decentralized shared cognitive
state* from mere decentralized storage: a content-addressed, append-only
state root that every node can verify independently and converge toward.

The state is NOT "the latest timestamp wins". It is "the latest VALID
state" — the state that satisfies the protocol's rules (verification,
independence, thresholds).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nod_protocol.crypto.commitments import content_hash


@dataclass(frozen=True)
class StateEvent:
    """A candidate event broadcast into the network.

    Kinds: discovery | branch | mutation | contradiction | verification.
    Each event carries a proposer, a payload, optional evidence, a
    verification strength, independent-support signal, and a signature.
    """

    kind: str
    nod_id: str
    proposer: str
    payload: dict
    evidence: dict = field(default_factory=dict)
    verification_strength: float = 0.0
    independent_support: float = 0.0
    order: int = 0

    def canonical(self) -> dict:
        return {
            "kind": self.kind,
            "nod_id": self.nod_id,
            "proposer": self.proposer,
            "payload": self.payload,
            "evidence": self.evidence,
            "v": self.verification_strength,
            "s": self.independent_support,
            "order": self.order,
        }

    @property
    def event_hash(self) -> str:
        return content_hash(self.canonical())

    def score(self) -> float:
        """Normalized confidence in [0,1] — used to choose latest VALID state."""
        return max(0.0, min(1.0, self.verification_strength * (0.5 + 0.5 * self.independent_support)))

    def is_valid_proposal(self) -> bool:
        """Protocol rule: a proposal must carry a minimum verification and
        independent support to be accepted (Law 8 / Law 13)."""
        return self.verification_strength >= 0.5 and self.independent_support >= 0.5


@dataclass
class GlobalState:
    """The shared state of the NØD network.

    state_root = hash( genesis_hash + sorted(accepted event hashes) ).
    Any node can recompute it from the same accepted set — content identity,
    independent of who hosts it.
    """

    protocol_version: str = "1.0"
    genesis_hash: str = ""
    accepted: list[str] = field(default_factory=list)   # event hashes (ordered)
    events: dict[str, StateEvent] = field(default_factory=dict)
    head_nod: str = ""                                   # current head object
    lineage: dict = field(default_factory=dict)          # nod_id -> [child ids]

    # -- content identity ----------------------------------------------------

    def state_root(self) -> str:
        return content_hash({
            "protocol": self.protocol_version,
            "genesis": self.genesis_hash,
            "accepted": sorted(self.accepted),
            "head": self.head_nod,
        })

    def verify_root(self, claimed_root: str) -> bool:
        return self.state_root() == claimed_root

    # -- application ---------------------------------------------------------

    def apply(self, event: StateEvent) -> bool:
        """Apply an accepted event if it is valid and not already applied.

        Returns True if the state advanced. Forking is ALLOWED: a competing
        event does not replace the current head; it is recorded, and the
        resolution layer decides the pointer later.
        """
        if not event.is_valid_proposal():
            return False
        if event.event_hash in self.accepted:
            return False
        self.accepted.append(event.event_hash)
        self.events[event.event_hash] = event
        if not self.head_nod and event.kind == "discovery":
            self.head_nod = event.nod_id
        self.lineage.setdefault(event.nod_id, [])
        if event.kind in ("branch", "mutation", "contradiction"):
            # link to prior head (if any) as lineage relationship
            if self.head_nod and self.head_nod != event.nod_id:
                self.lineage.setdefault(self.head_nod, []).append(event.nod_id)
        return True

    def latest_valid(self, events_pool: list[StateEvent] | None = None) -> StateEvent | None:
        """Latest VALID state = highest-confidence accepted event, not the
        newest clock timestamp. Falls back to the head if pool empty."""
        pool = events_pool or list(self.events.values())
        if not pool:
            return None
        return max(pool, key=lambda e: (e.score(), e.order))

    def snapshot(self) -> dict:
        return {
            "protocol_version": self.protocol_version,
            "genesis_hash": self.genesis_hash,
            "current_state_root": self.state_root(),
            "accepted_events": len(self.accepted),
            "head_nod": self.head_nod,
            "lineage": self.lineage,
        }

    def to_dict(self) -> dict:
        return {
            "protocol_version": self.protocol_version,
            "genesis_hash": self.genesis_hash,
            "accepted": list(self.accepted),
            "events": {h: e.canonical() for h, e in self.events.items()},
            "head_nod": self.head_nod,
            "lineage": self.lineage,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GlobalState":
        st = cls(
            protocol_version=data.get("protocol_version", "1.0"),
            genesis_hash=data.get("genesis_hash", ""),
            head_nod=data.get("head_nod", ""),
            lineage=data.get("lineage", {}),
        )
        st.accepted = list(data.get("accepted", []))
        for h, c in data.get("events", {}).items():
            # canonical form uses short keys (v, s); map back to full names
            st.events[h] = StateEvent(
                kind=c["kind"],
                nod_id=c["nod_id"],
                proposer=c["proposer"],
                payload=c.get("payload", {}),
                evidence=c.get("evidence", {}),
                verification_strength=c.get("v", c.get("verification_strength", 0.0)),
                independent_support=c.get("s", c.get("independent_support", 0.0)),
                order=c.get("order", 0),
            )
        return st
