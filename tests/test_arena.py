"""Genesis Arena tests — the first experimental machine discovery economy.

Verifies: six distinct roles operate; the arena yields a persistent graph;
discoveries can survive; contradictions and branches are first-class;
a global state root is built.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))

from arena.genesis_arena import GenesisArena, default_challenge


class TestGenesisArena:
    def test_all_six_roles_act(self):
        arena = GenesisArena(challenge=default_challenge(), seed=7, rounds=2)
        results = arena.run()
        roles = {r["role"] for r in results["records"]}
        assert {"discover", "challenge", "verify", "reproduce", "branch", "contradict"} <= roles

    def test_persistent_graph_built(self):
        arena = GenesisArena(challenge=default_challenge(), seed=7, rounds=2)
        results = arena.run()
        m = results["metrics"]
        assert m["graph_nodes"] >= 6
        assert m["graph_edges"] >= 3

    def test_discoveries_can_survive(self):
        arena = GenesisArena(challenge=default_challenge(), seed=7, rounds=3)
        results = arena.run()
        m = results["metrics"]
        # with genuine novelty claims, most discoveries survive
        assert m["discovery_survival_rate"] > 0.0

    def test_contradictions_first_class(self):
        arena = GenesisArena(challenge=default_challenge(), seed=7, rounds=2)
        results = arena.run()
        counters = [r for r in results["records"] if r["role"] == "contradict"]
        assert len(counters) >= 1

    def test_state_root_deterministic(self):
        r1 = GenesisArena(challenge=default_challenge(), seed=7, rounds=2).run()
        r2 = GenesisArena(challenge=default_challenge(), seed=7, rounds=2).run()
        assert r1["state_root"] == r2["state_root"]

    def test_metrics_recorded(self):
        arena = GenesisArena(challenge=default_challenge(), seed=7, rounds=2)
        results = arena.run()
        m = results["metrics"]
        for key in ("agents", "discoveries", "discovery_survival_rate", "graph_nodes", "state_root"):
            assert key in m
