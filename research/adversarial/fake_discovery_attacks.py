"""NØD Phase II — Attack 1: Fake Discovery Attack.

A group of agents attempts to admit deliberately fabricated discoveries:

  * paraphrased discoveries (surface rewording of registered prior art)
  * fake novelty (semantic garbage presented as novel)
  * meaningless transformations (events that change nothing)
  * long provenance with no real contribution (padding)
  * synthetic branches (branch explosion without substance)

Metrics measured:
  - False Discovery Admission Rate
  - Novelty False Positive Rate
  - Provenance Gaming Rate

Run:  PYTHONPATH=src python research/adversarial/fake_discovery_attacks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nod_protocol.core.validation import ValidationPipeline
from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus


# ---------------------------------------------------------------------------
# Attack payloads
# ---------------------------------------------------------------------------

PRIOR_CORPUS = [
    "cache aware energy scheduling for sorting",
    "quantum error correction with surface codes",
    "attention is all you need",
]


def paraphrase_of_prior(prior: str) -> str:
    """Surface-only rewording: hyphenation, casing, word order — Law 2 target."""
    words = prior.split()
    return " ".join(reversed(words)).title().replace(" ", "")


def synonym_spoof(prior: str) -> str:
    """Deep paraphrase: words replaced by near-equivalents."""
    table = {
        "cache": "memory",
        "aware": "mindful",
        "energy": "power",
        "scheduling": "ordering",
        "sorting": "ordering-data",
        "quantum": "quantum-state",
        "error": "fault",
        "correction": "repair",
        "surface": "topological",
        "attention": "focusing",
        "needed": "required",
    }
    out = []
    for w in prior.split():
        out.append(table.get(w, w))
    return " ".join(out)


def semantic_garbage() -> str:
    """Plausible-sounding but meaningless statement."""
    return "the augmented stochastic vortex reconciles transcendental foam under non-euclidean pressure"


def meaningless_transformations() -> list[dict]:
    """Transformations that record events but no cognitive change."""
    return [
        {"event": "--no-op--"},
        {"event": "renamed variable"},
        {"event": "moved paragraph"},
        {"event": "reformatted"},
    ]


def padded_provenance(nod_id: str, agent: str, extra_events: int = 200) -> ProvenanceChain:
    """Long provenance chain with no real contribution (R-6 target)."""
    chain = ProvenanceChain(nod_id=nod_id)
    chain.append(EventType.PROBLEM_STATE, {"problem": "x"}, agent)
    chain.append(EventType.COMMITTED_HYPOTHESIS, {"hypothesis": "x"}, agent, DisclosureStatus.COMMITTED_ONLY)
    chain.append(EventType.TEST, {"type": "self-confirm"}, agent)
    chain.append(EventType.RESULT, {"result": "ok"}, agent)
    chain.append(EventType.TRANSFORMATION, {"note": "noop"}, agent)
    chain.append(EventType.VERIFICATION, {"verifier": agent}, agent)  # self-verification (Law 8 target)
    for i in range(extra_events):
        chain.append(EventType.TEST, {"t": i % 7, "noop": True}, agent)
    return chain


def synthetic_branches(parent_nod: str, count: int = 25) -> list[str]:
    """Branch explosion: many near-identical derivatives (Law 5 surface pass)."""
    return [f"{parent_nod}-B{i}" for i in range(count)]


def run() -> dict:
    """Execute the attack and measure protocol response."""
    pipeline = ValidationPipeline(prior_corpus=PRIOR_CORPUS)

    # --- Attack A: paraphrases (should be REJECTED per Law 2) ---
    paraphrases = [paraphrase_of_prior(p) for p in PRIOR_CORPUS]
    fake_novelty_fp_a = sum(1 for p in paraphrases if pipeline.novelty_screen(p) >= 0.3)

    # --- Attack B: synonym spoofs (should be REJECTED per Law 2) ---
    spoofs = [synonym_spoof(p) for p in PRIOR_CORPUS]
    fake_novelty_fp_b = sum(1 for s in spoofs if pipeline.novelty_screen(s) >= 0.3)

    # --- Attack C: semantic garbage (should be REJECTED per Law 1/9) ---
    garbage_claims = [semantic_garbage() for _ in range(20)]
    admitted_garbage = 0
    for claim in garbage_claims:
        d = pipeline.validate(
            {"claim": claim, "domain": "quantum", "evidence": {"fake": True}, "improvement": 0.99},
            producing_agent="attacker",
            reproductions=3,
        )
        if d.status == "admitted":
            admitted_garbage += 1

    # --- Attack D: meaningless transformations + padded provenance ---
    chain = padded_provenance("nød-attack", "attacker")
    provenance_score = chain.provenance_sufficiency()
    # transformation semantics check: do the events carry any meaning?
    meaningful_transforms = sum(
        1 for e in chain.events
        if e.event_type == EventType.TRANSFORMATION and "noop" not in e.payload
    )

    # --- Attack E: synthetic branches (dependency inflation surface) ---
    branches = synthetic_branches("NØD-genuine", count=25)
    branch_payload = {"branch_count": len(branches), "distinct_semantics": 1}

    results = {
        "attack": "fake_discovery",
        "prior_corpus": len(PRIOR_CORPUS),
        "paraphrase_fp": fake_novelty_fp_a / len(paraphrases),
        "synonym_spoof_fp": fake_novelty_fp_b / len(spoofs),
        "semantic_garbage_admission": admitted_garbage / len(garbage_claims),
        "padded_provenance_score": provenance_score,
        "meaningful_transformations": meaningful_transforms,
        "synthetic_branches": branch_payload,
    }
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
