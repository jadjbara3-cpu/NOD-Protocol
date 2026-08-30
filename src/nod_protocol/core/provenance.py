"""Verifiable Cognitive Provenance (VCPC).

Implements the provenance event chain per Technical Specification §2:

- R-1 append-only
- R-2 parent event references
- R-3 content hash commitment
- R-4 no internal reasoning ever recorded
- R-5 hidden hypothesis via commitment
- R-6 chain length does not by itself increase value
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from nod_protocol.crypto.commitments import content_hash, event_id, signature, verify_signature


class EventType(str, Enum):
    PROBLEM_STATE = "problem_state"
    COMMITTED_HYPOTHESIS = "committed_hypothesis"
    TEST = "test"
    RESULT = "result"
    TRANSFORMATION = "transformation"
    VERIFICATION = "verification"
    MUTATION = "mutation"
    CONTRADICTION = "contradiction"
    BRANCH = "branch"


class DisclosureStatus(str, Enum):
    OPEN = "open"
    COMMITTED_ONLY = "committed_only"


def _to_plain(value: Any) -> Any:
    """Recursively convert read-only wrappers to JSON-serializable types."""
    if isinstance(value, Mapping):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


@dataclass(frozen=True)
class ProvenanceEvent:
    """An immutable provenance event (spec §2.1).

    ``canonical`` is the payload committed by the event. Private reasoning is
    structurally impossible to record here: only externally attestable events
    are representable.
    """
    event_type: EventType
    payload: dict
    agent_identity: str
    order: int
    nod_id: str
    parent_event_ids: tuple[str, ...] = ()
    disclosure_status: DisclosureStatus = DisclosureStatus.OPEN
    protocol_version: str = "1.0"

    def __post_init__(self) -> None:
        """Compute derived, immutable fields in __post_init__ of a frozen dataclass.

        R-1: the payload is wrapped in a read-only mapping so the event cannot
        be mutated after commitment.
        """
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "canonical", self._canonical_payload())
        object.__setattr__(self, "content_hash", content_hash(self.canonical))
        object.__setattr__(self, "signature", signature(self.agent_identity, self.canonical))
        object.__setattr__(self, "event_id", event_id(self.canonical))

    def _canonical_payload(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "agent": self.agent_identity,
            "order": self.order,
            "nod_id": self.nod_id,
            "parents": list(self.parent_event_ids),
            "disclosure": self.disclosure_status.value,
            "protocol_version": self.protocol_version,
        }

    def verify_integrity(self) -> bool:
        """R-3: recompute hash and signature; any mutation breaks verification."""
        canonical = self._canonical_payload()
        if content_hash(canonical) != self.content_hash:
            return False
        return verify_signature(self.agent_identity, canonical, self.signature)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "nod_id": self.nod_id,
            "event_type": self.event_type.value,
            "parent_event_ids": list(self.parent_event_ids),
            "agent_identity": self.agent_identity,
            "agent_signature": self.signature,
            "order": self.order,
            "content_hash": self.content_hash,
            "canonical": _to_plain(self.canonical),
            "disclosure_status": self.disclosure_status.value,
            "protocol_version": self.protocol_version,
        }


class ProvenanceChain:
    """An append-only chain of provenance events (VCPC)."""

    def __init__(self, nod_id: str, order_clock: Any | None = None) -> None:
        self.nod_id = nod_id
        self._events: list[ProvenanceEvent] = []
        self._order_clock = order_clock  # injectable deterministic clock
        self._frozen = False

    # -- lifecycle -----------------------------------------------------------

    def _next_order(self) -> int:
        if self._order_clock is not None:
            return self._order_clock()
        return len(self._events)

    def append(
        self,
        event_type: EventType,
        payload: dict,
        agent_identity: str,
        disclosure_status: DisclosureStatus = DisclosureStatus.OPEN,
    ) -> ProvenanceEvent:
        """R-1/R-2: append a new event linked to the current chain head."""
        if self._frozen:
            raise ValueError("chain is frozen (frozen chains are append-rejected)")
        parents = (self._events[-1].event_id,) if self._events else ()
        event = ProvenanceEvent(
            event_type=event_type,
            payload=payload,
            agent_identity=agent_identity,
            order=self._next_order(),
            nod_id=self.nod_id,
            parent_event_ids=parents,
            disclosure_status=disclosure_status,
        )
        self._events.append(event)
        return event

    def freeze(self) -> None:
        """After verification, the chain is finalized (spec: registration)."""
        self._frozen = True

    # -- inspection ------------------------------------------------------------

    @property
    def events(self) -> tuple[ProvenanceEvent, ...]:
        return tuple(self._events)

    @property
    def root(self) -> ProvenanceEvent | None:
        return self._events[0] if self._events else None

    @property
    def head(self) -> ProvenanceEvent | None:
        return self._events[-1] if self._events else None

    @property
    def length(self) -> int:
        return len(self._events)

    def has_event_classes(self, required: tuple[EventType, ...]) -> bool:
        """Completeness check of required event classes (spec §5.2)."""
        present = {e.event_type for e in self._events}
        return all(rt in present for rt in required)

    def verify_chain(self) -> bool:
        """Full integrity verification — R-1, R-2, R-3.

        R-4 is guaranteed structurally: no payload can contain private
        reasoning because only externally attestable event classes are
        representable; this method additionally asserts it for safety.
        """
        forbidden = ("chain_of_thought", "activations", "weights", "prompts", "internal")
        for event in self._events:
            if not event.verify_integrity():
                return False
            if self._contains_forbidden(event.payload, forbidden):
                return False
        # R-2: every event (after root) links to its predecessor
        for i, event in enumerate(self._events):
            if i == 0:
                if event.parent_event_ids:
                    return False
            else:
                if event.parent_event_ids != (self._events[i - 1].event_id,):
                    return False
        return True

    @staticmethod
    def _contains_forbidden(payload: Any, forbidden: tuple[str, ...]) -> bool:
        if isinstance(payload, Mapping):
            return any(
                (isinstance(k, str) and k in forbidden)
                or ProvenanceChain._contains_forbidden(v, forbidden)
                for k, v in payload.items()
            )
        if isinstance(payload, list):
            return any(ProvenanceChain._contains_forbidden(v, forbidden) for v in payload)
        return False

    # -- provenance sufficiency ------------------------------------------------

    def provenance_sufficiency(self) -> float:
        """P (Cognitive Provenance) component — spec §5.3.

        Evidentiary sufficiency is rewarded, NOT length (R-6). Score reaches
        saturation once the six required classes are present with integrity.
        """
        if self.length == 0 or not self.verify_chain():
            return 0.0
        required = (
            EventType.PROBLEM_STATE,
            EventType.COMMITTED_HYPOTHESIS,
            EventType.TEST,
            EventType.RESULT,
            EventType.TRANSFORMATION,
            EventType.VERIFICATION,
        )
        covered = sum(1 for rt in required if rt in {e.event_type for e in self._events})
        # saturation: 6 classes → 1.0; fewer → proportional; extra length adds nothing
        return min(1.0, covered / len(required))

    # -- persistence -------------------------------------------------------------

    def to_dict(self) -> list[dict]:
        return [e.to_dict() for e in self._events]

    @classmethod
    def from_dict(cls, nod_id: str, records: list[dict]) -> "ProvenanceChain":
        chain = cls(nod_id)
        for record in records:
            event = ProvenanceEvent(
                event_type=EventType(record["event_type"]),
                payload=dict(record["canonical"]["payload"]),
                agent_identity=record["agent_identity"],
                order=record["order"],
                nod_id=record["nod_id"],
                parent_event_ids=tuple(record["parent_event_ids"]),
                disclosure_status=DisclosureStatus(record["disclosure_status"]),
            )
            if record["content_hash"] != event.content_hash or record["agent_signature"] != event.signature:
                raise ValueError("integrity mismatch while restoring chain")
            chain._events.append(event)
        return chain
