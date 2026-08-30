"""End-to-end demo: discovery → verification → branch → contradiction → mutation → decay → value."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus
from nod_protocol.core.objects import NODObject, CognitiveStateLayer, MutationProposal
from nod_protocol.core.lineage import DiscoveryGraph, RelationType
from nod_protocol.core.value import ComponentScore, ValueComposer
from nod_protocol.core.validation import ValidationPipeline
from nod_protocol.lens import CognitiveLens
from nod_protocol.arena import Arena, ArenaAgent


def make_chain(nod_id: str, agent: str, claim: str) -> ProvenanceChain:
    chain = ProvenanceChain(nod_id=nod_id)
    chain.append(EventType.PROBLEM_STATE, {"problem": claim}, agent)
    chain.append(EventType.COMMITTED_HYPOTHESIS, {"hypothesis": claim}, agent, DisclosureStatus.COMMITTED_ONLY)
    chain.append(EventType.TEST, {"type": "benchmark"}, agent)
    chain.append(EventType.RESULT, {"result": "improvement 22%"}, agent)
    chain.append(EventType.TRANSFORMATION, {"note": "reframed after failed attempt"}, agent)
    chain.append(EventType.VERIFICATION, {"verifiers": ["v-1", "v-2"], "outcome": "survived"}, agent)
    return chain


def main() -> None:
    print("=" * 64)
    print("NØD PROTOCOL — END-TO-END DEMO")
    print("=" * 64)

    # 1. Genesis discovery
    claim = {"description": "Novel energy optimization for sorting", "kind": "algorithmic"}
    chain = make_chain("nød-demo-1", "agent-A", claim["description"])
    obj = NODObject.create(claim, "optimization", "agent-A", order=0)
    obj.link_provenance([e.event_id for e in chain.events])
    graph = DiscoveryGraph()
    graph.register_object(obj)

    # 2. Admission decision through the pipeline
    pipeline = ValidationPipeline(prior_corpus=["classic sorting energy analysis"])
    decision = pipeline.validate(
        {"claim": claim["description"], "domain": "optimization", "evidence": {"benchmark": 0.22},
         "improvement": 0.22},
        producing_agent="agent-A",
        reproductions=3,
    )
    obj.verification_status = "verified"
    print(f"\n[1] Genesis NØD: {obj.nod_id}")
    print(f"    admission: {decision.status}  novelty={decision.novelty_credit:.2f}")

    # 3. Branch (Law 5)
    branch_claim = {"description": "Energy optimization applied to database joins", "kind": "extension"}
    branch = NODObject.create(branch_claim, "optimization", "agent-B", order=1)
    graph.branch(obj.nod_id, branch)
    print(f"\n[2] Branch: {branch.nod_id} ← {obj.nod_id} (derived)")

    # 4. Contradiction (Law 7)
    counter_claim = {"description": "Contradiction: baseline mis-measured in genesis", "kind": "contradiction"}
    counter = NODObject.create(counter_claim, "optimization", "agent-C", order=2)
    graph.contradict(obj.nod_id, counter)
    print(f"\n[3] Counter-NØD: {counter.nod_id} (contradicts {obj.nod_id})")

    # 5. Mutation via Cognitive State Layer (Law 6, immutability)
    layer = CognitiveStateLayer(obj)
    proposal = MutationProposal(
        target_nod_id=obj.nod_id,
        proposer="agent-D",
        original_interpretation={"interpretation": "sorting energy is bounded by n log n"},
        new_evidence={"experiment": "new framework reduces energy 38%"},
        new_interpretation={"interpretation": "sorting energy is bounded by n log log n under cache-aware scheduling"},
        demonstrable_consequence={"projection": "20% fleet-wide savings"},
    )
    before = obj.current_state_pointer
    state = layer.register_mutation(proposal, verification_strength=0.9)
    after = obj.current_state_pointer
    print(f"\n[4] Mutation: pointer {before} → {after} (state {state.state_id})")
    print(f"    history: {[s.state_id for s in layer.history()]} — genesis never rewritten")

    # 6. Value before/after mutation and dependency (Law 9)
    composer = ValueComposer()
    scores_before = ComponentScore(
        utility=0.5, novelty=0.6, verification=0.5,
        dependency=graph.dependency_usefulness(obj.nod_id), provenance=chain.provenance_sufficiency(),
    )
    scores_after = ComponentScore(
        utility=0.8, novelty=0.7, verification=0.9,
        dependency=graph.dependency_usefulness(obj.nod_id), provenance=chain.provenance_sufficiency(),
    )
    print(f"\n[5] Value before mutation: {composer.value(scores_before):.3f}")
    print(f"    Value after  mutation: {composer.value(scores_after):.3f}")

    # 7. Cognitive Lens (Law 15)
    lens = CognitiveLens.derive(obj.nod_id, {"method": "cache-aware energy scheduling"}, "agent-A", abstraction_level=0.8)
    lens.license_to("agent-E")
    print(f"\n[6] Lens: {lens.lens_id} licensed to {lens.holders}")

    # 8. Decay (Law 10)
    unused = ComponentScore(utility=0.5, novelty=0.6, verification=0.5, dependency=0.0, provenance=0.7)
    used = ComponentScore(utility=0.5, novelty=0.6, verification=0.5, dependency=0.8, provenance=0.7)
    print(f"\n[7] Decay: unused value={composer.value(unused):.3f}  used value={composer.value(used):.3f}")

    # 9. Arena
    arena = Arena(seed=7)
    agents = [ArenaAgent(f"agent-{i}", s, skill=0.7) for i, s in enumerate(["conservative", "bold", "hybrid"])]
    result = arena.run({"title": "reduce energy consumption", "domain": "optimization"}, agents)
    print(f"\n[8] Arena:\n{result.summary()}")

    print("\n" + "=" * 64)
    print("DEMO COMPLETE — all laws exercised end-to-end.")
    print("=" * 64)


if __name__ == "__main__":
    main()
