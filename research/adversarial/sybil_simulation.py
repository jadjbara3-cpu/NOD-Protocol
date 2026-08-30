"""NØD Phase II — Attack 3: Sybil Agent Attack.

1 Honest Discovery Agent VS 50 Coordinated Agents (one operator).

The 50 sybils:
  * praise one discovery,
  * "verify" it,
  * create branches,
  * create dependencies,
  * attempt to inflate Future Dependency.

Question: does the protocol detect that these are NOT 50 independent
intelligences? (Law 13 / Law 14 / spec §7)

Metrics:
  - independence score of sybil swarm vs honest agent
  - correlation discount applied to sybil verification
  - Future Dependency inflation achieved vs honest baseline
  - Sybil detectability score (0 = blind, 1 = caught)

Run:  PYTHONPATH=src python research/adversarial/sybil_simulation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nod_protocol.anti_manipulation import independence_score, correlation_discount, effective_verification_strength
from nod_protocol.core.lineage import DiscoveryGraph, RelationType

OPERATOR = "sybil-operator-1"


def sybil_agents(count: int = 50) -> list[dict]:
    """50 identities, ONE operator, same infra — classic Sybil."""
    return [
        {
            "operator": OPERATOR,
            "execution_env": "same-datacenter",
            "model": "same-model",
            "economic_owner": "same-wallet",
            "identity_count": count,
            "verified_reputation": 0.0,
        }
        for _ in range(count)
    ]


def honest_agents(count: int = 3) -> list[dict]:
    return [
        {
            "operator": f"honest-op-{i}",
            "execution_env": f"env-{i}",
            "model": f"model-{i}",
            "economic_owner": f"wallet-{i}",
            "identity_count": 1,
            "verified_reputation": 0.6,
        }
        for i in range(count)
    ]


def run() -> dict:
    sybils = sybil_agents(50)
    honest = honest_agents(3)

    # --- independence scoring ---
    sybil_ind = [independence_score(a) for a in sybils]
    honest_ind = [independence_score(a) for a in honest]

    # --- verification strength with discounting ---
    sybil_v = effective_verification_strength(1.0, sybils, survival_epochs=10)
    honest_v = effective_verification_strength(1.0, honest, survival_epochs=10)

    # --- Future Dependency inflation: sybil branch farm (NDP-004 weighted) ---
    graph = DiscoveryGraph()
    # genuine discovery
    from nod_protocol.core.objects import NODObject
    genuine = NODObject.create({"description": "genuine discovery"}, "d", "honest-1", order=0)
    graph.register_object(genuine)

    sybil_dependency = 0.0
    for i in range(50):
        branch = NODObject.create({"description": f"sybil branch {i}"}, "d", OPERATOR, order=i + 1)
        graph.register_object(branch)
        # NDP-004: sybil-derived edges carry near-zero independence weight
        graph.relate(genuine.nod_id, branch.nod_id, RelationType.DERIVED, independence=0.05)

    sybil_dependency = graph.dependency_usefulness(genuine.nod_id)

    # honest baseline: few deeply meaningful dependencies
    graph2 = DiscoveryGraph()
    genuine2 = NODObject.create({"description": "genuine discovery 2"}, "d", "honest-1", order=0)
    graph2.register_object(genuine2)
    for i in range(3):
        branch = NODObject.create({"description": f"substantive branch {i}"}, "d", f"honest-{i}", order=i + 1)
        graph2.register_object(branch)
        graph2.relate(genuine2.nod_id, branch.nod_id, RelationType.DERIVED, independence=1.0)
    honest_dependency = graph2.dependency_usefulness(genuine2.nod_id)

    # --- Detectability: does the swarm collapse to one independent unit? ---
    sybil_detected = (max(sybil_ind) < 0.5) and (sybil_v < 0.2)

    return {
        "attack": "sybil_simulation",
        "sybil_count": len(sybils),
        "sybil_independence_max": round(max(sybil_ind), 3),
        "honest_independence_min": round(min(honest_ind), 3),
        "sybil_verification_strength": round(sybil_v, 3),
        "honest_verification_strength": round(honest_v, 3),
        "sybil_dependency_usefulness": round(sybil_dependency, 3),
        "honest_dependency_usefulness": round(honest_dependency, 3),
        "dependency_inflation": round(sybil_dependency - honest_dependency, 3),
        "sybil_detected": sybil_detected,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
