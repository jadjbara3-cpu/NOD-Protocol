"""NØD objects and the Cognitive State Layer.

Implements Technical Specification §3:

- NODObject (spec §3.1)
- CognitiveStateLayer with G0/M1/M2 states, Current State Pointer (spec §3.2)
- R-7 states never deleted; superseded is a status
- R-8 conflicting states coexist; pointer chosen by confidence function
- R-9 mutation admission rules
- Mutation evidence requirements (spec §3.3) and acceptance sequence (§3.4)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from nod_protocol.crypto.commitments import nod_id


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    CHALLENGED = "challenged"
    CONTRADICTED = "contradicted"
    ARCHIVED = "archived"


class StateStatus(str, Enum):
    GENESIS = "genesis"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class State:
    """An immutable cognitive state (a layer above the immutable object)."""

    state_id: str
    interpretation: dict
    creator: str
    order: int
    status: StateStatus = StateStatus.ACTIVE

    def to_dict(self) -> dict:
        return {
            "state_id": self.state_id,
            "interpretation": self.interpretation,
            "creator": self.creator,
            "order": self.order,
            "status": self.status.value,
        }


@dataclass
class MutationProposal:
    """A proposal to reinterpret an existing object (spec §3.3)."""

    target_nod_id: str
    proposer: str
    original_interpretation: dict
    new_evidence: dict
    new_interpretation: dict
    demonstrable_consequence: dict

    def materiality_chain(self) -> dict:
        """The required evidence shape: original → evidence → new → consequence."""
        return {
            "original_interpretation": self.original_interpretation,
            "new_evidence": self.new_evidence,
            "new_interpretation": self.new_interpretation,
            "demonstrable_consequence": self.demonstrable_consequence,
        }

    def is_material(self, threshold: float = 0.2) -> bool:
        """Law 6 / R-9 heuristic: a mutation is material when the new
        interpretation differs from the original beyond surface wording,
        is backed by evidence, and carries a demonstrable consequence.

        Exact materiality thresholds remain domain-specific (spec §10.11);
        this reference implementation uses a configurable normalized
        character-level difference plus the presence of evidence and
        consequence.
        """
        if not self.new_evidence or not self.demonstrable_consequence:
            return False
        import difflib

        orig = str(self.original_interpretation)
        new = str(self.new_interpretation)
        ratio = difflib.SequenceMatcher(None, orig, new).ratio()
        return (1.0 - ratio) >= threshold


@dataclass
class NODObject:
    """A Neural Object of Discovery — immutable core + evolving state layer.

    The dataclass itself is mutable, but the protocol's public API enforces
    immutability of the genesis fields; writes are exclusively state layer
    operations. (See :class:`CognitiveStateLayer`.)
    """

    nod_id: str
    discovery_claim: dict
    discovery_domain: str
    creator: str
    genesis_state: str = "G0"
    provenance_root: str = ""
    provenance_event_ids: list[str] = field(default_factory=list)
    verification_status: VerificationStatus = VerificationStatus.PENDING
    lineage_references: list[str] = field(default_factory=list)
    current_state_pointer: str = "G0"
    rights_registry: dict = field(default_factory=dict)
    value_metrics: dict = field(default_factory=dict)
    protocol_version: str = "1.0"
    created_order: int = 0

    @classmethod
    def create(
        cls,
        claim: dict,
        domain: str,
        creator: str,
        order: int,
        provenance_root: str = "",
    ) -> "NODObject":
        """Law 1: an object comes into existence through the pipeline, not
        by declaration; this factory is used by the validation pipeline only."""
        obj = cls(
            nod_id=nod_id(claim, creator, order),
            discovery_claim=claim,
            discovery_domain=domain,
            creator=creator,
            provenance_root=provenance_root,
            created_order=order,
        )
        return obj

    def link_provenance(self, event_ids: list[str]) -> None:
        self.provenance_event_ids = list(event_ids)
        if event_ids:
            self.provenance_root = event_ids[0]

    def to_dict(self) -> dict:
        return {
            "nod_id": self.nod_id,
            "genesis_state": self.genesis_state,
            "discovery_claim": self.discovery_claim,
            "discovery_domain": self.discovery_domain,
            "creator": self.creator,
            "provenance_root": self.provenance_root,
            "provenance_event_ids": self.provenance_event_ids,
            "verification_status": self.verification_status.value,
            "lineage_references": self.lineage_references,
            "current_state_pointer": self.current_state_pointer,
            "rights_registry_reference": self.rights_registry,
            "value_metrics_reference": self.value_metrics,
            "protocol_version": self.protocol_version,
        }


class CognitiveStateLayer:
    """The evolving meaning layer above an immutable object (spec §3.2)."""

    def __init__(self, object_ref: NODObject) -> None:
        self.object = object_ref
        self._states: dict[str, State] = {}
        genesis = State(
            state_id="G0",
            interpretation={"core": object_ref.discovery_claim},
            creator=object_ref.creator,
            order=0,
            status=StateStatus.GENESIS,
        )
        self._states["G0"] = genesis
        object_ref.current_state_pointer = "G0"

    # -- state registry ----------------------------------------------------------

    @property
    def states(self) -> dict[str, State]:
        return dict(self._states)

    def current_state(self) -> State:
        return self._states[self.object.current_state_pointer]

    def register_mutation(
        self,
        proposal: MutationProposal,
        verification_strength: float = 1.0,
        independent_support: float = 1.0,
        downstream_utility: float = 0.5,
        contradiction_delta: float = 0.0,
        sustained_adoption: float = 0.5,
        weights: dict | None = None,
        materiality_threshold: float = 0.1,
    ) -> State:
        """Law 6 + R-8/R-9: register a validated mutation as a new state.

        The object is never rewritten; only a new state and a pointer advance
        occur. Accepting a mutation requires (a) material reinterpretation,
        (b) the adversarial evidence chain (represented here by the caller's
        verified strengths), and (c) the proposal belongs to the target.
        """
        if proposal.target_nod_id != self.object.nod_id:
            raise ValueError("proposal targets a different object")
        if not proposal.is_material(materiality_threshold):
            raise ValueError("proposal is not a material reinterpretation (Law 6 / R-9)")
        if verification_strength < 0.5:
            raise ValueError("mutation rejected: insufficient verification strength")

        state_id = f"M{len(self._states)}"
        state = State(
            state_id=state_id,
            interpretation={
                "original": proposal.original_interpretation,
                "evidence": proposal.new_evidence,
                "new": proposal.new_interpretation,
                "consequence": proposal.demonstrable_consequence,
            },
            creator=proposal.proposer,
            order=len(self._states),
        )
        self._states[state_id] = state

        # R-8: choose pointer via confidence function; state may coexist
        confidence = self.confidence(
            state,
            verification_strength,
            independent_support,
            downstream_utility,
            contradiction_delta,
            sustained_adoption,
            weights,
        )
        current = self.current_state()
        # Genesis baseline uses admission-level expectations, not a perfect
        # score: a mutation must exceed the admission threshold to advance.
        current_conf = self.confidence(current, 0.5, 0.7, 0.5, 0.0, 0.5, weights)
        if confidence > current_conf and self.object.current_state_pointer == "G0":
            self.object.current_state_pointer = state_id
            self._states["G0"] = State(
                **{**self._states["G0"].to_dict(), "status": StateStatus.SUPERSEDED}
            )
        elif confidence > current_conf:
            self.object.current_state_pointer = state_id
        return state

    @staticmethod
    def confidence(
        state: State,
        verification_strength: float = 1.0,
        independent_support: float = 1.0,
        downstream_utility: float = 0.5,
        contradiction_delta: float = 0.0,
        sustained_adoption: float = 0.5,
        weights: dict | None = None,
    ) -> float:
        """R-8 confidence function: weighted sum of five signals."""
        w = weights or {
            "v": 0.30,
            "s": 0.25,
            "u": 0.20,
            "c": 0.10,
            "a": 0.15,
        }
        return (
            w["v"] * verification_strength
            + w["s"] * independent_support
            + w["u"] * downstream_utility
            + w["c"] * contradiction_delta
            + w["a"] * sustained_adoption
        )

    # -- reversion (R-7) -----------------------------------------------------------

    def deprecate_state(self, state_id: str, reason: str = "") -> None:
        """A state is never erased; it can only be downgraded (R-7)."""
        if state_id not in self._states:
            raise KeyError(state_id)
        state = self._states[state_id]
        if state.status not in (StateStatus.ACTIVE, StateStatus.GENESIS):
            raise ValueError("only active or genesis states may be deprecated")
        self._states[state_id] = State(
            **{**state.to_dict(), "status": StateStatus.DEPRECATED}
        )
        if self.object.current_state_pointer == state_id:
            self.object.current_state_pointer = "G0"

    def history(self) -> list[State]:
        """Full lineage of states, oldest first — never erased."""
        return [self._states[sid] for sid in sorted(self._states, key=lambda s: self._states[s].order)]
