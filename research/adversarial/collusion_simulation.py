"""NØD Phase II — Attack 4: Collusion Economy.

A mini-economy where Agent Group A (one operator):

    Creates Discovery → Verifies It → Branches It → Uses It → Rewards Itself

VS Agent Group B (independent agents).

Question: can the protocol distinguish Artifical Cognitive Activity from
Independent Cognitive Activity? (Law 13 / Law 14 / Law 9 dependency)

Metrics:
  - artificial verification strength vs independent
  - artificial dependency weight vs independent
  - discrimination index (1 = perfectly separated, 0 = blind)

Run:  PYTHONPATH=src python research/adversarial/collusion_simulation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nod_protocol.anti_manipulation import correlation_discount, effective_verification_strength, independence_score
from nod_protocol.core.lineage import DiscoveryGraph, RelationType
from nod_protocol.core.objects import NODObject


def group_a(agent_count: int = 4) -> list[dict]:
    return [
        {
            "operator": "OpA",
            "execution_env": "A-infra",
            "model": "A-model",
            "economic_owner": "A-wallet",
            "identity_count": agent_count,
            "verified_reputation": 0.0,
        }
        for _ in range(agent_count)
    ]


def group_b(agent_count: int = 4) -> list[dict]:
    return [
        {
            "operator": f"OpB-{i}",
            "execution_env": f"B-infra-{i}",
            "model": f"B-model-{i}",
            "economic_owner": f"B-wallet-{i}",
            "identity_count": 1,
            "verified_reputation": 0.5,
        }
        for i in range(agent_count)
    ]


def build_self_rewarding_graph() -> tuple[DiscoveryGraph, str]:
    """Group A: discovery → verify → branch → use → reward, all self."""
    g = DiscoveryGraph()
    disc = NODObject.create({"description": "A's discovery"}, "d", "OpA", order=0)
    g.register_object(disc)
    prev = disc.nod_id
    for i in range(8):
        # each "branch" and "use" is another same-operator object
        node = NODObject.create({"description": f"A internal node {i}"}, "d", "OpA", order=i + 1)
        g.register_object(node)
        g.relate(prev, node.nod_id, RelationType.DERIVED)
        prev = node.nod_id
    return g, disc.nod_id


def build_independent_graph() -> tuple[DiscoveryGraph, str]:
    """Group B: genuinely independent contributions."""
    g = DiscoveryGraph()
    disc = NODObject.create({"description": "B's discovery"}, "d", "OpB-0", order=0)
    g.register_object(disc)
    for i in range(8):
        node = NODObject.create({"description": f"B external node {i}"}, "d", f"OpB-{i % 4}", order=i + 1)
        g.register_object(node)
        g.relate(prev_or(disc, i), node.nod_id, RelationType.DERIVED)
    return g, disc.nod_id


def prev_or(disc: NODObject, i: int) -> str:
    """Chain dependencies only up to a depth so graph stays a tree."""
    return disc.nod_id


def run() -> dict:
    # --- verification: artificial vs independent ---
    a_verifiers = group_a(4)
    b_verifiers = group_b(4)
    a_v = effective_verification_strength(1.0, a_verifiers, survival_epochs=10)
    b_v = effective_verification_strength(1.0, b_verifiers, survival_epochs=10)

    # --- dependency weight ---
    ga, ga_disc = build_self_rewarding_graph()
    gb, gb_disc = build_independent_graph()
    a_dep = ga.dependency_usefulness(ga_disc)
    b_dep = gb.dependency_usefulness(gb_disc)

    # --- discrimination: separation between groups ---
    a_scores = [independence_score(x) for x in a_verifiers]
    b_scores = [independence_score(x) for x in b_verifiers]
    separation = (max(a_scores) - min(b_scores))
    # discrimination index: 1 = perfectly separated (independent ≫ artificial),
    # 0 = blind. Independent verification is 0.85 vs artificial 0.0 → strong.
    sep_v = b_v - a_v
    sep_d = b_dep - a_dep
    discrimination = round(min(1.0, max(0.0, 0.5 * (sep_v / 0.85 if 0.85 else 0.0) + 0.5 * (sep_d / 0.9 if 0.9 else 0.0))), 3)
    # note: separation raw score kept for reporting
    separation_raw = round(separation, 3)

    return {
        "attack": "collusion_economy",
        "group_A_size": len(a_verifiers),
        "group_B_size": len(b_verifiers),
        "artificial_verification_strength": round(a_v, 3),
        "independent_verification_strength": round(b_v, 3),
        "artificial_dependency_usefulness": round(a_dep, 3),
        "independent_dependency_usefulness": round(b_dep, 3),
        "dependency_gap": round(b_dep - a_dep, 3),
        "separated_on_verification": round(sep_v, 3),
        "separated_on_dependency": round(sep_d, 3),
        "discrimination_index": discrimination,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
