"""NØD Protocol — The Persistent Discovery Layer for Machine Intelligence.

Reference implementation, Version 1.0. Standard library only.
"""

from nod_protocol.core.provenance import ProvenanceEvent, ProvenanceChain, EventType
from nod_protocol.core.objects import NODObject, CognitiveStateLayer, MutationProposal, State
from nod_protocol.core.lineage import DiscoveryGraph, RelationType
from nod_protocol.core.value import ValueComposer, ComponentWeights
from nod_protocol.core.validation import ValidationPipeline, AdmissionDecision
from nod_protocol.anti_manipulation import (
    independence_score,
    correlation_discount,
    circular_dependency_suppression,
    delayed_finality_multiplier,
)
from nod_protocol.lens import CognitiveLens
from nod_protocol.arena import Arena

__version__ = "1.0.0"

__all__ = [
    "ProvenanceEvent",
    "ProvenanceChain",
    "EventType",
    "NODObject",
    "CognitiveStateLayer",
    "MutationProposal",
    "State",
    "DiscoveryGraph",
    "RelationType",
    "ValueComposer",
    "ComponentWeights",
    "ValidationPipeline",
    "AdmissionDecision",
    "independence_score",
    "correlation_discount",
    "circular_dependency_suppression",
    "delayed_finality_multiplier",
    "CognitiveLens",
    "Arena",
]
