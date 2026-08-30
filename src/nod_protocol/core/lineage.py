"""Discovery lineage: the directed graph of cognitive objects.

Implements Technical Specification §4:

- RelationType with weights (derived 1.0, improved 0.8, contradicted -1.0,
  verified 0.5, combined 0.7, extended 0.6, reinterpreted 0.4)
- Law 5 branching: new immutable object linked to, never merged with ancestor
- Law 7 contradiction: Counter-NØD with adversarial edge
- R-10: cycles, self-dependency, low-information descendants penalized
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from nod_protocol.core.provenance import ProvenanceChain


class RelationType(str, Enum):
    DERIVED = "derived_from"
    IMPROVED = "improved_by"
    CONTRADICTED = "contradicted_by"
    VERIFIED = "verified_by"
    COMBINED = "combined_with"
    EXTENDED = "extended_by"
    REINTERPRETED = "reinterpreted_by"

    @property
    def weight(self) -> float:
        return {
            RelationType.DERIVED: 1.0,
            RelationType.IMPROVED: 0.8,
            RelationType.CONTRADICTED: -1.0,
            RelationType.VERIFIED: 0.5,
            RelationType.COMBINED: 0.7,
            RelationType.EXTENDED: 0.6,
            RelationType.REINTERPRETED: 0.4,
        }[self]


class DiscoveryGraph:
    """Directed weighted graph of NØD objects."""

    def __init__(self) -> None:
        self._nodes: dict[str, Any] = {}
        self._edges: list[tuple[str, str, RelationType, float]] = []
        self._edge_independence: dict[tuple[str, str, str], float] = {}

    # -- nodes -----------------------------------------------------------------

    def add_object(self, nod_id: str, obj: Any = None) -> None:
        if nod_id in self._nodes:
            raise ValueError(f"object already registered: {nod_id}")
        self._nodes[nod_id] = obj

    def register_object(self, obj: Any) -> None:
        self.add_object(obj.nod_id, obj)

    def has(self, nod_id: str) -> bool:
        return nod_id in self._nodes

    def get(self, nod_id: str) -> Any:
        return self._nodes.get(nod_id)

    @property
    def nodes(self) -> dict[str, Any]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[tuple[str, str, RelationType, float]]:
        return list(self._edges)

    def edge_independence(self, source: str, target: str, relation: RelationType) -> float:
        """NDP-004: independence weight of an edge (0..1). Defaults to 1.0."""
        return self._edge_independence.get((source, target, relation.value), 1.0)

    # -- edges -------------------------------------------------------------------

    def relate(
        self,
        source: str,
        target: str,
        relation: RelationType,
        weight_override: float | None = None,
        independence: float = 1.0,
    ) -> None:
        if source not in self._nodes or target not in self._nodes:
            raise KeyError("edge endpoints must be registered objects")
        if source == target:
            raise ValueError("self-dependency is prohibited (Law 13 / R-10)")
        w = relation.weight if weight_override is None else weight_override
        self._edges.append((source, target, relation, w))
        self._edge_independence[(source, target, relation.value)] = max(0.0, min(1.0, independence))

    def branch(self, parent_id: str, child_obj: Any) -> None:
        """Law 5: a branch is a new object linked to — never merged with — its ancestor."""
        if not self.has(parent_id):
            raise KeyError(parent_id)
        self.register_object(child_obj)
        self.relate(parent_id, child_obj.nod_id, RelationType.DERIVED)

    def contradict(self, target_id: str, counter: Any) -> None:
        """Law 7: a verified contradiction creates a Counter-NØD with an adversarial edge."""
        if not self.has(target_id):
            raise KeyError(target_id)
        self.register_object(counter)
        self.relate(target_id, counter.nod_id, RelationType.CONTRADICTED)

    def improve(self, source_id: str, target_id: str) -> None:
        self.relate(source_id, target_id, RelationType.IMPROVED)

    # -- analysis -------------------------------------------------------------------

    def descendants(self, nod_id: str) -> set[str]:
        """All transitive derivative nodes."""
        out: set[str] = set()
        frontier = [nod_id]
        while frontier:
            node = frontier.pop()
            for src, dst, rel, _ in self._edges:
                if src == node and rel in (RelationType.DERIVED, RelationType.EXTENDED, RelationType.IMPROVED):
                    if dst not in out:
                        out.add(dst)
                        frontier.append(dst)
        return out

    def direct_children(self, nod_id: str) -> list[tuple[str, RelationType]]:
        return [(dst, rel) for src, dst, rel, _ in self._edges if src == nod_id]

    def find_cycles(self) -> list[list[str]]:
        """Detect cycles in the derived-lineage subgraph (R-10 penalty input)."""
        adj: dict[str, list[str]] = {n: [] for n in self._nodes}
        for src, dst, rel, _ in self._edges:
            if rel in (RelationType.DERIVED, RelationType.EXTENDED, RelationType.IMPROVED):
                adj[src].append(dst)

        cycles: list[list[str]] = []
        visited: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            path.append(node)
            for nxt in adj[node]:
                if nxt in path:
                    cycles.append(path[path.index(nxt):] + [nxt])
                elif nxt not in visited:
                    dfs(nxt)
            path.pop()

        for node in adj:
            if node not in visited:
                dfs(node)
        return cycles

    def cycle_penalty(self, nod_id: str) -> float:
        """R-10: penalize nodes inside cycles; cap at 0.25 per cycle."""
        cycles = self.find_cycles()
        return min(0.25 * sum(1 for c in cycles if nod_id in c), 0.75)

    def dependency_weight(self, nod_id: str) -> float:
        """Future Dependency component input: weighted outgoing dependency strength.

        NDP-004 (F5 fix): each edge is weighted by its independence — a single
        operator's 50 farmed branches contribute ≈ as much as ONE independent
        branch. Self-generated/circular contribution is reduced by the cycle
        penalty; independent downstream usage is what counts.
        """
        total = 0.0
        for src, dst, rel, w in self._edges:
            if src == nod_id and rel in (RelationType.DERIVED, RelationType.EXTENDED, RelationType.IMPROVED):
                indep = self.edge_independence(src, dst, rel)
                total += max(w, 0.0) * indep
        return max(0.0, total - self.cycle_penalty(nod_id))

    def dependency_usefulness(self, nod_id: str) -> float:
        """Nonlinear D: one deeply independent downstream matters more than many
        trivial references — modeled as log-scaled weighted dependency."""
        w = self.dependency_weight(nod_id)
        if w <= 0:
            return 0.0
        return min(1.0, 0.5 + 0.5 * (w / (1.0 + w)))

    def to_dict(self) -> dict:
        return {
            "nodes": list(self._nodes.keys()),
            "edges": [
                {"source": s, "target": t, "relation": r.value, "weight": w}
                for s, t, r, w in self._edges
            ],
        }
