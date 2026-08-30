"""NØD-Sync — Distributed Cognitive Synchronization Layer.

Transforms NØD from decentralized STORAGE into a decentralized SHARED
COGNITIVE STATE: content-addressed state roots, fork-aware resolution,
eventual convergence, and an open protocol any model can query, verify,
and build upon.
"""

from nod_protocol.sync.state import StateEvent, GlobalState
from nod_protocol.sync.resolution import Resolution, resolve_fork, confidence, latest_valid_pointer
from nod_protocol.sync.network import Node, SimNetwork

__all__ = [
    "StateEvent",
    "GlobalState",
    "Resolution",
    "resolve_fork",
    "confidence",
    "latest_valid_pointer",
    "Node",
    "SimNetwork",
]
