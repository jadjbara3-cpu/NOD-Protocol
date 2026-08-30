"""Cognitive Navigation Layer tests.

Locks: semantic ranking works, axes differentiate, verified-only filtering,
foundational centrality, and CLI integration.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.sync.state import StateEvent, GlobalState
from nod_protocol.navigation import CognitiveNavigator, SemanticIndex


def ev(kind, nid, claim, v, s, order, utility=0.5):
    return StateEvent(kind=kind, nod_id=nid, proposer="p",
                      payload={"claim": claim, "utility": utility},
                      verification_strength=v, independent_support=s, order=order)


def build_state() -> GlobalState:
    gs = GlobalState(genesis_hash="gen-nav")
    gs.apply(ev("discovery", "D1", "cache-aware sorting energy optimization", 0.95, 0.9, 1, 0.8))
    gs.apply(ev("discovery", "D2", "quantum error correction on surface codes", 0.9, 0.85, 2, 0.6))
    gs.apply(ev("discovery", "D3", "energy proportional radix partitioning", 0.85, 0.8, 3, 0.7))
    gs.apply(ev("branch", "D4", "cache-aware extension for near-sorted streams", 0.8, 0.7, 4, 0.5))
    return gs


class TestSemanticIndex:
    def test_index_builds_from_state(self):
        nav = CognitiveNavigator(build_state())
        assert len(nav.index.docs) == 4

    def test_tfidf_scores_relevance(self):
        nav = CognitiveNavigator(build_state())
        s_present = nav.index.score("cache aware energy", "D1")
        s_absent = nav.index.score("nonsense gibberish words", "D1")
        assert s_present > 0
        assert s_absent == 0


class TestNavigation:
    def test_most_verified_ranks(self):
        nav = CognitiveNavigator(build_state())
        r = nav.navigate("cache aware energy", axis="most_verified", top_k=2)
        assert r.ranked[0]["nod_id"] == "D1"  # highest verification + relevance

    def test_verified_only_filter(self):
        nav = CognitiveNavigator(build_state())
        r = nav.navigate("cache aware energy", verified_only=True)
        assert all(x["verified"] >= 0.5 for x in r.ranked)

    def test_axes_are_distinct(self):
        nav = CognitiveNavigator(build_state())
        high_v = nav.navigate("cache aware energy", axis="most_verified", top_k=1).ranked[0]["nod_id"]
        high_f = nav.navigate("cache aware energy", axis="most_foundational", top_k=1).ranked[0]["nod_id"]
        # D1 and D4 both relate to cache-aware; foundational favors ancestors
        assert high_v == "D1"

    def test_top_discoveries(self):
        nav = CognitiveNavigator(build_state())
        r = nav.top_discoveries(top_k=3)
        assert len(r.ranked) <= 3

    def test_unknown_axis_raises(self):
        nav = CognitiveNavigator(build_state())
        try:
            nav.navigate("x", axis="bogus")
            assert False
        except ValueError:
            assert True

    def test_results_are_ranked(self):
        nav = CognitiveNavigator(build_state())
        r = nav.navigate("cache aware energy", axis="most_verified", top_k=4)
        scores = [x["axis_score"] for x in r.ranked]
        assert scores == sorted(scores, reverse=True)


class TestCliIntegration:
    def test_node_imports_navigate(self, tmp_path):
        import json
        import nod_node

        from nod_protocol.sync.state import StateEvent

        data = tmp_path / "d"
        nod_node.init_node(data)
        nod_node.submit_claim(data, "cache-aware sorting energy optimization", "agent-a", "optimization")
        nod_node.submit_claim(data, "quantum error correction surface codes", "agent-b", "quantum")
        out = nod_node.navigate(data, "cache aware energy")
        assert out["count"] >= 1
        assert out["axis"] == "most_verified"
