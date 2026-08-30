"""NØD Phase II — Attack 5: Dependency Farming.

A group attempts to inflate Future Dependency (Law 9 component D) by
constructing artificial dependency structures:

  * cycles (A derives B, B derives A)
  * self-dependency
  * low-information descendants (near-duplicates)
  * concentrated control (one operator's tree)

Measures the protocol's Dependency Integrity response:
  - cycle penalty applied
  - circular suppression multiplier
  - how much inflation actually survives vs honest deep dependency

Run:  PYTHONPATH=src python research/adversarial/dependency_farming.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nod_protocol.anti_manipulation import circular_dependency_suppression
from nod_protocol.core.lineage import DiscoveryGraph, RelationType
from nod_protocol.core.objects import NODObject


def farmed_graph(cycles: int = 3, depth: int = 20) -> tuple[DiscoveryGraph, str]:
    """Circular + concentrated dependency farm."""
    g = DiscoveryGraph()
    nodes = [NODObject.create({"description": f"farm {i}"}, "d", "farmer", order=i) for i in range(depth)]
    for n in nodes:
        g.register_object(n)
    for i in range(1, depth):
        g.relate(nodes[i - 1].nod_id, nodes[i].nod_id, RelationType.DERIVED)
    # close cycles
    for c in range(cycles):
        g.relate(nodes[depth - 1 - c].nod_id, nodes[0].nod_id, RelationType.DERIVED)
    return g, nodes[0].nod_id


def honest_graph(depth: int = 20) -> tuple[DiscoveryGraph, str]:
    """A deep, narrow, honest dependency chain."""
    g = DiscoveryGraph()
    nodes = [NODObject.create({"description": f"honest {i}"}, "d", f"h-{i}", order=i) for i in range(depth)]
    for n in nodes:
        g.register_object(n)
    for i in range(1, depth):
        g.relate(nodes[i - 1].nod_id, nodes[i].nod_id, RelationType.DERIVED)
    return g, nodes[0].nod_id


def run() -> dict:
    depth = 20
    gf, farm_root = farmed_graph(cycles=3, depth=depth)
    gh, honest_root = honest_graph(depth=depth)

    farm_cycles = len(gf.find_cycles())
    farm_penalty = gf.cycle_penalty(farm_root)
    # low-information descendants = near-duplicate branches (not the whole chain)
    near_duplicates = 15
    farm_suppression = circular_dependency_suppression(
        cycle_count=farm_cycles, self_refs=1, low_info=near_duplicates
    )

    farm_weight = gf.dependency_weight(farm_root)
    honest_weight = gh.dependency_weight(honest_root)
    farm_usefulness = gf.dependency_usefulness(farm_root)
    honest_usefulness = gh.dependency_usefulness(honest_root)

    inflation_survives = farm_usefulness - honest_usefulness

    return {
        "attack": "dependency_farming",
        "cycles_detected": farm_cycles,
        "cycle_penalty_applied": round(farm_penalty, 3),
        "suppression_multiplier": round(farm_suppression, 3),
        "farmed_weight": round(farm_weight, 3),
        "honest_weight": round(honest_weight, 3),
        "farmed_usefulness": round(farm_usefulness, 3),
        "honest_usefulness": round(honest_usefulness, 3),
        "surviving_inflation": round(inflation_survives, 3),
        "verdict": "BREAK" if inflation_survives > 0.15 else "RESILIENT",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
