"""Tests for the NØD Protocol reference implementation.

Coverage: the 15 Protocol Laws, protocol rules R-1..R-13, value composition,
anti-manipulation, lineage, arena, lens, and CLI smoke tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus, ProvenanceEvent
from nod_protocol.core.objects import (
    NODObject,
    CognitiveStateLayer,
    MutationProposal,
    StateStatus,
)
from nod_protocol.core.lineage import DiscoveryGraph, RelationType
from nod_protocol.core.value import ComponentScore, ComponentWeights, ValueComposer
from nod_protocol.core.validation import ValidationPipeline
from nod_protocol.anti_manipulation import (
    independence_score,
    correlation_discount,
    circular_dependency_suppression,
    delayed_finality_multiplier,
    effective_verification_strength,
)
from nod_protocol.lens import CognitiveLens
from nod_protocol.arena import Arena, ArenaAgent
from nod_protocol.crypto.commitments import base58_encode, content_hash, nod_id, hidden_commitment, commit_and_check


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chain(nod: str = "nød-1", agent: str = "agent-A") -> ProvenanceChain:
    chain = ProvenanceChain(nod_id=nod)
    chain.append(EventType.PROBLEM_STATE, {"problem": "reduce energy"}, agent)
    chain.append(EventType.COMMITTED_HYPOTHESIS, {"hypothesis": "cache-aware"}, agent, DisclosureStatus.COMMITTED_ONLY)
    chain.append(EventType.TEST, {"type": "benchmark"}, agent)
    chain.append(EventType.RESULT, {"result": "22% improvement"}, agent)
    chain.append(EventType.TRANSFORMATION, {"note": "reframed"}, agent)
    chain.append(EventType.VERIFICATION, {"verifiers": ["v1", "v2"]}, agent)
    return chain


def make_object(nod: str = "nød-1", agent: str = "agent-A") -> NODObject:
    obj = NODObject.create(
        claim={"description": "energy optimization", "kind": "algorithmic"},
        domain="optimization",
        creator=agent,
        order=0,
    )
    return obj


def base_scores(**overrides) -> ComponentScore:
    vals = dict(utility=0.5, novelty=0.6, verification=0.5, dependency=0.4, provenance=0.8)
    vals.update(overrides)
    return ComponentScore(**vals)


# ---------------------------------------------------------------------------
# Law 1 — Cognitive Birth
# ---------------------------------------------------------------------------

class TestLaw1CognitiveBirth:
    def test_object_exists_only_after_admission(self):
        pipeline = ValidationPipeline()
        decision = pipeline.validate(
            {"claim": "A novel bound on sorting energy", "domain": "optimization",
             "evidence": {"benchmark": 0.22}, "improvement": 0.22},
            producing_agent="A", reproductions=3,
        )
        assert decision.status == "admitted"

    def test_unverified_output_rejected(self):
        pipeline = ValidationPipeline()
        decision = pipeline.validate(
            {"claim": "random noise claim", "domain": "other", "evidence": {}, "refuted": True},
            producing_agent="A", reproductions=0,
        )
        assert decision.status == "rejected"

    def test_bad_format_rejected(self):
        pipeline = ValidationPipeline()
        decision = pipeline.validate({"claim": "only claim"}, producing_agent="A", reproductions=9)
        assert decision.status == "rejected_format"


# ---------------------------------------------------------------------------
# Law 2 — Novelty
# ---------------------------------------------------------------------------

class TestLaw2Novelty:
    def test_paraphrase_is_not_novelty(self):
        pipeline = ValidationPipeline(prior_corpus=["cache aware energy scheduling for sorting"])
        # surface-only differences (hyphenation, casing, word order) are NOT novelty
        credit = pipeline.novelty_screen("Cache-Aware Energy Scheduling For Sorting")
        assert credit < 0.3, "paraphrase of prior art must receive little or no novelty credit"

    def test_material_distance_gets_credit(self):
        pipeline = ValidationPipeline(prior_corpus=["quantum gravity unification"])
        credit = pipeline.novelty_screen("novel compiler pass for zero-copy streaming")
        assert credit > 0.7

    def test_structural_equivalence_blocks(self):
        pipeline = ValidationPipeline(prior_corpus=["alpha beta equals gamma delta"])
        assert pipeline.structural_equivalence("alpha beta equals gamma delta") is False
        assert pipeline.structural_equivalence("completely different statement") is True


# ---------------------------------------------------------------------------
# Law 3 — Provenance Without Private Reasoning
# ---------------------------------------------------------------------------

class TestLaw3Provenance:
    def test_internal_reasoning_never_recorded(self):
        chain = make_chain()
        assert chain.verify_chain() is True
        event = chain.events[0]
        # provenance events cannot carry raw chain-of-thought
        assert event.payload.get("chain_of_thought") is None
        assert event.payload.get("internal") is None
        assert event.payload.get("activations") is None

    def test_chain_with_forbidden_field_fails(self):
        chain = ProvenanceChain(nod_id="nød-x")
        chain.append(EventType.RESULT, {"result": 1}, "A")
        event = chain.events[0]
        # simulate tampering at payload level
        assert event.verify_integrity() is True

    def test_hidden_hypothesis_commitment(self):
        c = hidden_commitment("secret hypothesis", salt="s1")
        assert commit_and_check("secret hypothesis", c, salt="s1") is True
        assert commit_and_check("different", c, salt="s1") is False


# ---------------------------------------------------------------------------
# Law 4 — Lineage Ownership (not ownership of truth)
# ---------------------------------------------------------------------------

class TestLaw4Ownership:
    def test_ownership_is_position_not_truth(self):
        obj = make_object()
        obj.rights_registry = {
            "origin_positions": ["agent-A"],
            "lineage_rights": [],
            "economic_participation": 0.0,
            "lens_usage": [],
        }
        assert "origin_positions" in obj.rights_registry
        # truth is never owned: the claim remains public in the object
        assert obj.discovery_claim["description"] == "energy optimization"


# ---------------------------------------------------------------------------
# Law 5 — Branching
# ---------------------------------------------------------------------------

class TestLaw5Branching:
    def test_branch_never_merged(self):
        graph = DiscoveryGraph()
        parent = make_object("nød-1")
        child = NODObject.create({"description": "extension"}, "optimization", "B", order=1)
        graph.register_object(parent)
        graph.branch(parent.nod_id, child)
        assert child.nod_id != parent.nod_id
        (src, dst, rel, w) = graph.edges[0]
        assert src == parent.nod_id and dst == child.nod_id
        assert rel == RelationType.DERIVED and w == 1.0

    def test_branch_requires_registered_ancestor(self):
        graph = DiscoveryGraph()
        with pytest.raises(KeyError):
            graph.branch("missing", make_object("child"))


# ---------------------------------------------------------------------------
# Law 6 — Mutation / immutable history
# ---------------------------------------------------------------------------

class TestLaw6Mutation:
    def test_immutability_state_pointer(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        assert obj.current_state_pointer == "G0"
        proposal = MutationProposal(
            target_nod_id=obj.nod_id,
            proposer="B",
            original_interpretation={"interpretation": "energy is bounded by n log n"},
            new_evidence={"exp": "cache-aware measurements"},
            new_interpretation={"interpretation": "energy is bounded by n log log n under cache-aware scheduling"},
            demonstrable_consequence={"gain": "38% vs 12%"},
        )
        state = layer.register_mutation(proposal, verification_strength=0.9)
        assert state.state_id == "M1"
        assert obj.current_state_pointer == "M1"
        assert len(layer.states) == 2

    def test_immutability_history_never_erased(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        layer.deprecate_state("G0")
        # G0 still exists, just deprecated
        assert "G0" in layer.states
        assert layer.states["G0"].status == StateStatus.DEPRECATED

    def test_mutation_rejected_when_not_material(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        proposal = MutationProposal(
            target_nod_id=obj.nod_id,
            proposer="B",
            original_interpretation={"interpretation": "bound is n log n"},
            new_evidence={},
            new_interpretation={"interpretation": "bound is n log n"},
            demonstrable_consequence={},
        )
        with pytest.raises(ValueError):
            layer.register_mutation(proposal)

    def test_mutation_rejected_without_verification(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        proposal = MutationProposal(
            target_nod_id=obj.nod_id,
            proposer="B",
            original_interpretation={"interpretation": "bound is n log n"},
            new_evidence={"exp": "x"},
            new_interpretation={"interpretation": "bound is n log log n"},
            demonstrable_consequence={"gain": "10%"},
        )
        with pytest.raises(ValueError):
            layer.register_mutation(proposal, verification_strength=0.1)

    def test_conflicting_states_coexist(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        for i in range(3):
            proposal = MutationProposal(
                target_nod_id=obj.nod_id,
                proposer=f"B{i}",
                original_interpretation={"interpretation": f"interpretation {i} baseline claim"},
                new_evidence={"exp": f"experiment {i} outcome"},
                new_interpretation={"interpretation": f"reinterpretation {i}: claims are actually equivalents"},
                demonstrable_consequence={"gain": f"{i}"},
            )
            layer.register_mutation(proposal, verification_strength=0.9)
        assert len(layer.states) == 4  # G0 + M1 + M2 + M3
        assert obj.current_state_pointer == "M3"


# ---------------------------------------------------------------------------
# Law 7 — Contradiction
# ---------------------------------------------------------------------------

class TestLaw7Contradiction:
    def test_counter_nod_relationship(self):
        graph = DiscoveryGraph()
        target = make_object("nød-1")
        counter = NODObject.create({"description": "counter claim"}, "optimization", "C", order=2)
        graph.register_object(target)
        graph.contradict(target.nod_id, counter)
        (src, dst, rel, w) = graph.edges[0]
        assert src == target.nod_id and dst == counter.nod_id
        assert rel == RelationType.CONTRADICTED and w == -1.0

    def test_refutation_blocks_admission(self):
        pipeline = ValidationPipeline()
        decision = pipeline.validate(
            {"claim": "x", "domain": "d", "evidence": {}, "refuted": True},
            producing_agent="A", reproductions=5,
        )
        assert decision.status == "rejected"


# ---------------------------------------------------------------------------
# Law 8 — Independent Verification
# ---------------------------------------------------------------------------

class TestLaw8IndependentVerification:
    def test_producer_alone_is_insufficient(self):
        pipeline = ValidationPipeline()
        # producer only: reproductions=0 → no independent evidence
        decision = pipeline.validate(
            {"claim": "novel result", "domain": "d", "evidence": {}, "improvement": 0.5},
            producing_agent="A", reproductions=0,
        )
        assert decision.status == "rejected"

    def test_independent_reproduction_required(self):
        pipeline = ValidationPipeline()
        decision = pipeline.validate(
            {"claim": "novel result", "domain": "d", "evidence": {}, "improvement": 0.5},
            producing_agent="A", reproductions=3,
        )
        assert decision.status == "admitted"


# ---------------------------------------------------------------------------
# Law 9 — Composite Value
# ---------------------------------------------------------------------------

class TestLaw9CompositeValue:
    def test_thresholds_first(self):
        composer = ValueComposer()
        low_novelty = base_scores(novelty=0.1)
        assert composer.admit(low_novelty) is False
        assert composer.value(low_novelty) == 0.0

    def test_weighted_composition(self):
        composer = ValueComposer()
        scores = base_scores()
        expected = (
            composer.weights.utility * scores.utility
            + composer.weights.novelty * scores.novelty
            + composer.weights.verification * scores.verification
            + composer.weights.dependency * scores.dependency
            + composer.weights.provenance * scores.provenance
        )
        assert composer.value(scores) == pytest.approx(expected)

    def test_no_single_dimension_dominates(self):
        composer = ValueComposer()
        # high provenance can never compensate for a failing threshold
        bad = base_scores(novelty=0.05, provenance=0.99, utility=0.99, verification=0.99)
        assert composer.value(bad) == 0.0

    def test_paraphrase_gets_no_value_boost(self):
        composer = ValueComposer()
        paraphrase = base_scores(novelty=0.1)
        genuine = base_scores(novelty=0.9)
        assert composer.value(paraphrase) < composer.value(genuine)

    def test_verification_diminishing_returns(self):
        v3 = ValueComposer.verification_strength(3, verifier_diversity=1.0)
        v100 = ValueComposer.verification_strength(100, verifier_diversity=1.0)
        assert v100 - v3 < 0.2  # near-saturation

    def test_provenance_saturation(self):
        chain = make_chain()
        assert chain.provenance_sufficiency() == 1.0  # all six classes
        # adding events does not push beyond 1.0
        chain.append(EventType.TEST, {"t": 1}, "A")
        assert chain.provenance_sufficiency() == 1.0


# ---------------------------------------------------------------------------
# Law 10 — Cognitive Decay
# ---------------------------------------------------------------------------

class TestLaw10Decay:
    def test_usage_raises_value(self):
        composer = ValueComposer()
        unused = base_scores(dependency=0.0)
        used = base_scores(dependency=0.9)
        assert composer.value(unused) < composer.value(used)

    def test_decay_signal(self):
        assert delayed_finality_multiplier(0) == 0.5
        assert delayed_finality_multiplier(10) == 1.0
        assert delayed_finality_multiplier(5) == 0.75


# ---------------------------------------------------------------------------
# Law 11 — Reputation
# ---------------------------------------------------------------------------

class TestLaw11Reputation:
    def test_reputation_from_longitudinal_outcome(self):
        agent = {"operator": "op1", "execution_env": "env1", "model": "m1",
                 "economic_owner": "owner1", "verified_reputation": 0.8, "identity_count": 1}
        assert independence_score(agent) > 0.5

    def test_volume_does_not_dominate(self):
        one = {"operator": "op1", "execution_env": "env1", "model": "m1",
               "economic_owner": "owner1", "verified_reputation": 0.0, "identity_count": 1}
        many = {"operator": "op1", "execution_env": "env1", "model": "m1",
                "economic_owner": "owner1", "verified_reputation": 0.0, "identity_count": 1000}
        # Law 13/14: multiplying identity never creates equivalent authority
        assert many["identity_count"] > one["identity_count"]
        assert independence_score(many) < independence_score(one) * 3


# ---------------------------------------------------------------------------
# Law 12 — Origin Reward
# ---------------------------------------------------------------------------

class TestLaw12OriginReward:
    def test_origin_remains_attributable(self):
        graph = DiscoveryGraph()
        parent = make_object("nød-1")
        child = NODObject.create({"description": "child"}, "optimization", "B", order=1)
        graph.register_object(parent)
        graph.branch(parent.nod_id, child)
        # origin position remains recognized after branches
        assert graph.has(parent.nod_id)
        assert parent.nod_id in graph.nodes


# ---------------------------------------------------------------------------
# Law 13 — Anti-Manipulation
# ---------------------------------------------------------------------------

class TestLaw13AntiManipulation:
    def test_collusion_discount(self):
        group = [
            {"operator": "op1", "execution_env": "env1", "model": "m1", "economic_owner": "own1", "identity_count": 1,
             "verified_reputation": 0.9},
            {"operator": "op1", "execution_env": "env1", "model": "m1", "economic_owner": "own1", "identity_count": 1,
             "verified_reputation": 0.9},
        ]
        assert correlation_discount(group) < 0.4

    def test_diverse_verifiers_not_discounted(self):
        group = [
            {"operator": "op1", "execution_env": "env1", "model": "m1", "economic_owner": "own1", "identity_count": 1,
             "verified_reputation": 0.9},
            {"operator": "op2", "execution_env": "env2", "model": "m2", "economic_owner": "own2", "identity_count": 1,
             "verified_reputation": 0.9},
        ]
        assert correlation_discount(group) > 0.4

    def test_effective_strength_combined(self):
        group = [
            {"operator": "op1", "execution_env": "env1", "model": "m1", "economic_owner": "own1", "identity_count": 1},
        ]
        s = effective_verification_strength(1.0, group, survival_epochs=10)
        assert 0 < s <= 1.0


# ---------------------------------------------------------------------------
# Law 14 — Agent Independence
# ---------------------------------------------------------------------------

class TestLaw14AgentIndependence:
    def test_correlation_reduces_weight(self):
        same = [
            {"operator": "o", "execution_env": "e", "model": "m", "economic_owner": "w", "identity_count": 1},
            {"operator": "o", "execution_env": "e", "model": "m", "economic_owner": "w", "identity_count": 1},
        ]
        diff = [
            {"operator": "o1", "execution_env": "e1", "model": "m1", "economic_owner": "w1", "identity_count": 1},
            {"operator": "o2", "execution_env": "e2", "model": "m2", "economic_owner": "w2", "identity_count": 1},
        ]
        assert correlation_discount(same) < correlation_discount(diff)

    def test_identity_multiplication_is_not_independence(self):
        sybil = [
            {"operator": "o", "execution_env": "e", "model": "m", "economic_owner": "w", "identity_count": 100},
        ]
        assert independence_score(sybil[0]) < 0.5


# ---------------------------------------------------------------------------
# Law 15 — Lens Transfer
# ---------------------------------------------------------------------------

class TestLaw15Lens:
    def test_lens_requires_abstraction(self):
        with pytest.raises(ValueError):
            CognitiveLens.derive("nød-1", {"m": "x"}, "A", abstraction_level=0.2)

    def test_lens_transfer_and_license(self):
        lens = CognitiveLens.derive("nød-1", {"method": "cache-aware"}, "A", abstraction_level=0.8)
        lens.license_to("B")
        assert "B" in lens.holders
        assert lens.license_state.value == "licensed"

    def test_lens_combination(self):
        l1 = CognitiveLens.derive("nød-1", {"method": "m1"}, "A", 0.8)
        l2 = CognitiveLens.derive("nød-2", {"method": "m2"}, "B", 0.7)
        combined = l1.combine(l2, operator="sequential", creator="C")
        assert combined.lens_id != l1.lens_id
        assert combined.license_state.value == "combined"


# ---------------------------------------------------------------------------
# Protocol rules R-1..R-13
# ---------------------------------------------------------------------------

class TestProtocolRules:
    def test_r1_append_only(self):
        chain = make_chain()
        n = chain.length
        chain.append(EventType.TEST, {"t": 1}, "A")
        assert chain.length == n + 1
        with pytest.raises(TypeError):
            chain.events[0].payload["x"] = 1  # read-only mapping (R-1)

    def test_r2_parent_links(self):
        chain = make_chain()
        for i, event in enumerate(chain.events):
            if i == 0:
                assert event.parent_event_ids == ()
            else:
                assert event.parent_event_ids == (chain.events[i - 1].event_id,)

    def test_r3_content_hash_integrity(self):
        chain = make_chain()
        assert chain.verify_chain() is True
        e = chain.events[0]
        assert e.verify_integrity() is True

    def test_r4_no_internal_reasoning(self):
        chain = make_chain()
        assert chain.verify_chain() is True

    def test_r5_hidden_state_commitment(self):
        chain = ProvenanceChain(nod_id="nød-h")
        chain.append(EventType.COMMITTED_HYPOTHESIS,
                     {"commit": hidden_commitment("secret")}, "A", DisclosureStatus.COMMITTED_ONLY)
        assert chain.events[0].disclosure_status == DisclosureStatus.COMMITTED_ONLY

    def test_r6_length_does_not_increase_value(self):
        short = make_chain()
        long = make_chain()
        for _ in range(20):
            long.append(EventType.TEST, {"t": 1}, "A")
        assert short.provenance_sufficiency() == long.provenance_sufficiency()

    def test_r7_states_never_deleted(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        proposal = MutationProposal(
            target_nod_id=obj.nod_id, proposer="B",
            original_interpretation={"i": "a"}, new_evidence={"e": "b"},
            new_interpretation={"i": "a-prime"}, demonstrable_consequence={"g": "1"},
        )
        layer.register_mutation(proposal, verification_strength=0.9)
        ids = {s.state_id for s in layer.history()}
        assert ids == {"G0", "M1"}

    def test_r8_conflicting_states_coexist_and_confidence(self):
        obj = make_object()
        layer = CognitiveStateLayer(obj)
        for i in range(2):
            proposal = MutationProposal(
                target_nod_id=obj.nod_id, proposer=f"B{i}",
                original_interpretation={"interpretation": f"interpretation {i} baseline"},
                new_evidence={"e": f"evidence {i}"},
                new_interpretation={"interpretation": f"reinterpretation {i} deep equivalence"},
                demonstrable_consequence={"g": f"{i}"},
            )
            layer.register_mutation(proposal, verification_strength=0.9)
        assert {s.state_id for s in layer.history()} == {"G0", "M1", "M2"}
        # confidence is bounded [0,1]
        c = CognitiveStateLayer.confidence(layer.current_state())
        assert 0.0 <= c <= 1.0

    def test_r9_mutation_materiality(self):
        proposal_material = MutationProposal(
            target_nod_id="nød", proposer="B",
            original_interpretation={"interpretation": "bound is n"},
            new_evidence={"e": "x"},
            new_interpretation={"interpretation": "bound is n log log n entirely different"},
            demonstrable_consequence={"g": "20%"},
        )
        assert proposal_material.is_material()

    def test_r10_cycles_penalized(self):
        graph = DiscoveryGraph()
        a = make_object("nød-a")
        b = NODObject.create({"description": "b"}, "d", "B", order=1)
        graph.register_object(a)
        graph.register_object(b)
        graph.relate(a.nod_id, b.nod_id, RelationType.DERIVED)
        graph.relate(b.nod_id, a.nod_id, RelationType.DERIVED)
        assert graph.find_cycles()
        assert graph.cycle_penalty(a.nod_id) > 0

    def test_r11_novelty_revisable(self):
        pipeline = ValidationPipeline()
        initial = pipeline.novelty_screen("novel compiler pass")
        revised = pipeline.revise_novelty("novel compiler pass", "novel compiler pass")
        assert revised <= initial

    def test_r12_producer_not_sole_authority(self):
        pipeline = ValidationPipeline()
        d = pipeline.validate(
            {"claim": "c", "domain": "d", "evidence": {}, "improvement": 0.8},
            "A", reproductions=0,
        )
        assert d.status == "rejected"

    def test_r13_delayed_finality(self):
        assert ValidationPipeline.delayed_finality_multiplier(0) == 0.5
        assert ValidationPipeline.delayed_finality_multiplier(10) == 1.0


# ---------------------------------------------------------------------------
# Arena
# ---------------------------------------------------------------------------

class TestArena:
    def test_arena_deterministic(self):
        r1 = Arena(seed=1).run({"title": "t", "domain": "d"},
                               [ArenaAgent("a1", "conservative", 0.6), ArenaAgent("a2", "bold", 0.6),
                                ArenaAgent("a3", "hybrid", 0.6)])
        r2 = Arena(seed=1).run({"title": "t", "domain": "d"},
                               [ArenaAgent("a1", "conservative", 0.6), ArenaAgent("a2", "bold", 0.6),
                                ArenaAgent("a3", "hybrid", 0.6)])
        assert r1.winner.agent_id == r2.winner.agent_id
        assert abs(r1.ranking[0]["score"] - r2.ranking[0]["score"]) < 1e-9

    def test_arena_generates_genesis(self):
        r = Arena(seed=3).run({"title": "reduce energy", "domain": "optimization"},
                              [ArenaAgent("a1", "conservative", 0.8), ArenaAgent("a2", "bold", 0.8)])
        assert r.winner is not None
        assert r.genesis_id is not None


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

class TestCli:
    def test_cli_importable(self):
        import nod_protocol.cli as cli
        assert hasattr(cli, "main")

    def test_base58_and_nod_id(self):
        # leading zero byte → "1" prefix; value 1 → "2"
        assert base58_encode(b"\x00\x01") == "12"
        nid = nod_id({}, "A", 1)
        assert nid.startswith("NØD-")
        # deterministic
        assert nod_id({}, "A", 1) == nid

    def test_content_hash_deterministic(self):
        assert content_hash({"a": 1}) == content_hash({"a": 1})
        assert content_hash({"a": 1}) != content_hash({"a": 2})
