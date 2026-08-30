"""NØD Cognitive Navigation Layer.

Turns the discovery graph from a raw database into machine-readable
discovery infrastructure: any agent can ask

    "What discoveries exist related to X?"

and receive ranked, verified answers along four axes:

    Most Verified       (verification strength)
    Most Used           (future dependency / usage)
    Fastest Growing     (recent adoption growth)
    Most Foundational   (graph centrality / lineage depth)

All rankings are recomputed from the same content-addressed state, so an
agent in Japan, Jordan, or Brazil gets the identical answer from any node.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from nod_protocol.sync.state import GlobalState


# ---------------------------------------------------------------------------
# Lightweight semantic index (tf-idf over discovery claims)
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z\d]{3,}", text.lower()))


@dataclass
class SemanticIndex:
    """Inverted index built from accepted discovery events."""

    state: GlobalState
    doc_freq: dict[str, int] = field(default_factory=dict)
    docs: dict[str, dict] = field(default_factory=dict)   # nod_id -> {text, tokens, tf}

    def build(self) -> "SemanticIndex":
        self.doc_freq.clear()
        self.docs.clear()
        for h, e in self.state.events.items():
            if e.kind not in ("discovery", "branch", "mutation"):
                continue
            text = str(e.payload.get("claim") or e.payload.get("desc") or e.nod_id)
            toks = _tokens(text)
            self.docs[e.nod_id] = {
                "text": text,
                "tokens": toks,
                "tf": Counter(toks),
                "event_hash": h,
                "event": e,
            }
            for t in toks:
                self.doc_freq[t] = self.doc_freq.get(t, 0) + 1
        return self

    def idf(self, token: str) -> float:
        n = max(1, len(self.docs))
        df = self.doc_freq.get(token, 0)
        return math.log((n + 1) / (df + 1)) + 1.0

    def score(self, query: str, nod_id: str) -> float:
        if nod_id not in self.docs:
            return 0.0
        qtoks = _tokens(query)
        if not qtoks:
            return 0.0
        doc = self.docs[nod_id]
        covered = qtoks & doc["tokens"]
        if not covered:
            return 0.0
        denom = sum(len(doc["tf"]) for _ in [0])
        score = sum(doc["tf"][t] * self.idf(t) for t in covered)
        # normalize by document length
        return score / (1.0 + math.log(1.0 + denom))


# ---------------------------------------------------------------------------
# Navigation result
# ---------------------------------------------------------------------------

@dataclass
class NavigationResult:
    query: str
    ranked: list[dict]
    axis: str
    verified_only: bool

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "axis": self.axis,
            "verified_only": self.verified_only,
            "results": self.ranked,
            "count": len(self.ranked),
        }


class CognitiveNavigator:
    """Answers 'what discoveries relate to X?' from the shared state."""

    AXES = ("most_verified", "most_used", "fastest_growing", "most_foundational")

    def __init__(self, state: GlobalState) -> None:
        self.state = state
        self.index = SemanticIndex(state).build()

    # -- axis scorers ----------------------------------------------------------

    def _verification(self, nod_id: str) -> float:
        vals = [e.verification_strength for e in self.state.events.values() if e.nod_id == nod_id]
        return max(vals) if vals else 0.0

    def _usage(self, nod_id: str) -> float:
        vals = [e.independent_support for e in self.state.events.values() if e.nod_id == nod_id]
        return sum(vals) if vals else 0.0

    def _growth(self, nod_id: str) -> float:
        recent = [e for e in self.state.events.values()
                  if e.nod_id == nod_id and e.order >= max(0, self.state.root_order() - 3)]
        return float(len(recent))

    def _foundational(self, nod_id: str) -> int:
        return len(self.state.lineage.get(nod_id, []))

    # -- query -----------------------------------------------------------------

    def navigate(self, query: str, axis: str = "most_verified", top_k: int = 5,
                 verified_only: bool = True) -> NavigationResult:
        if axis not in self.AXES:
            raise ValueError(f"unknown axis {axis}; choose from {self.AXES}")
        scored = []
        for nod_id in self.index.docs:
            rel = self.index.score(query, nod_id)
            if rel <= 0:
                continue
            if axis == "most_verified":
                s = rel * self._verification(nod_id)
            elif axis == "most_used":
                s = rel * self._usage(nod_id)
            elif axis == "fastest_growing":
                s = rel * self._growth(nod_id)
            else:
                s = rel * self._foundational(nod_id)
            if verified_only and self._verification(nod_id) < 0.5:
                continue
            scored.append({
                "nod_id": nod_id,
                "relevance": round(rel, 4),
                "axis_score": round(s, 4),
                "verified": self._verification(nod_id),
                "claim": self.index.docs[nod_id]["text"][:120],
            })
        scored.sort(key=lambda d: d["axis_score"], reverse=True)
        return NavigationResult(query, scored[:top_k], axis, verified_only)

    # -- convenience -----------------------------------------------------------

    def top_discoveries(self, top_k: int = 5) -> NavigationResult:
        """'What are the most foundational discoveries in the network?'"""
        return self.navigate("discovery discovery discovery", axis="most_foundational", top_k=top_k)


# ---------------------------------------------------------------------------
# Convenience: patch-free — rely on GlobalState.root_order()
# ---------------------------------------------------------------------------
