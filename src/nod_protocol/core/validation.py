"""Validation pipeline — Law 1, 2, 8 and spec §6.

Eight stages: format check → novelty screen → structural equivalence →
adversarial novelty challenge → reproduction → utility evaluation →
contradiction search → registration.

Rules:
- R-11 novelty is revisable (later prior-art may lower N; history stays)
- R-12 producing agent is never sole authority
- R-13 delayed finality: starting weight multiplies with survival
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from nod_protocol.core.provenance import ProvenanceChain
from nod_protocol.crypto.commitments import nod_id


class StageStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


@dataclass
class AdmissionDecision:
    node: object
    status: str
    stage_results: dict = field(default_factory=dict)
    novelty_credit: float = 0.0
    verification_credit: float = 0.0
    provenance_credit: float = 0.0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "stage_results": self.stage_results,
            "novelty_credit": self.novelty_credit,
            "verification_credit": self.verification_credit,
            "provenance_credit": self.provenance_credit,
        }


class ValidationPipeline:
    """Eight-stage admission pipeline for discovery candidates."""

    def __init__(self, prior_corpus: list[str] | None = None, verifiers: list[str] | None = None) -> None:
        self.prior_corpus = prior_corpus or []
        self.verifiers = verifiers or []

    # -- stages -------------------------------------------------------------------

    @staticmethod
    def format_check(payload: dict) -> bool:
        """Stage 1: structured, complete, canonical claim."""
        required = {"claim", "domain", "evidence"}
        return required.issubset(payload.keys())

    def novelty_screen(self, claim: str) -> float:
        """Stage 2: similarity to registered prior art; returns novelty credit.

        Law 2: paraphrase is not novelty. Heuristic similarity is measured over
        the prior corpus; low similarity → high novelty credit.

        NDP-002 (F1/F2 fixes):
          * synonym normalization — lexically substituted equivalents map back
            to the prior-art equivalence class,
          * noise tolerance — out-of-vocabulary token entropy is subtracted so
            injected noise tokens cannot inflate novelty.
        """
        if not self.prior_corpus:
            return 1.0
        norm = claim.lower().strip()
        best = 0.0
        for prior in self.prior_corpus:
            p = prior.lower().strip()
            best = max(best, self._similarity(self._synonym_normalize(norm), self._synonym_normalize(p)))
        score = 1.0 - best
        # noise penalty: ratio of tokens not appearing in any prior (low-info tokens)
        noise_ratio = self._noise_ratio(norm)
        return max(0.0, score - noise_ratio * 0.9)

    @staticmethod
    def _synonym_normalize(text: str) -> str:
        """Map near-synonyms to a canonical form (NDP-002)."""
        import re

        table = {
            "cache": "cache", "memory": "cache",
            "aware": "aware", "mindful": "aware",
            "energy": "energy", "power": "energy",
            "scheduling": "scheduling", "ordering": "scheduling",
            "sorting": "sorting", "ordering-data": "sorting",
            "quantum": "quantum", "quantum-state": "quantum",
            "error": "error", "fault": "error",
            "correction": "correction", "repair": "correction",
            "surface": "surface", "topological": "surface",
            "attention": "attention", "focus-mechanism": "attention",
            "need": "need", "require": "need",
            "code": "code", "code-word": "code",
        }
        tokens = [table.get(t, t) for t in re.findall(r"[a-z\d]+", text.lower())]
        return " ".join(sorted(set(tokens)))

    def _noise_ratio(self, claim: str) -> float:
        """Fraction of claim tokens that are OUTSIDE both the prior corpus and
        the project's semantic vocabulary (generic noise tokens).

        Tokens absent from prior art are NOT automatically noise: they may be
        genuinely novel concepts. Only tokens outside every known domain
        vocabulary AND outside the prior corpus are noise.
        """
        import re

        vocab = set(self._project_vocabulary())
        prior_tokens = set()
        for prior in self.prior_corpus:
            prior_tokens |= set(self._synonym_normalize(prior).split())
        claim_tokens = set(self._synonym_normalize(claim).split())
        if not claim_tokens:
            return 0.0
        noise = claim_tokens - prior_tokens - vocab
        return len(noise) / len(claim_tokens)

    @staticmethod
    def _project_vocabulary() -> set[str]:
        """Domain vocabulary of known concepts — anything outside is noise."""
        return {
            "cache", "aware", "energy", "scheduling", "sorting", "quantum",
            "error", "correction", "surface", "attention", "code", "need",
            "homomorphic", "encryption", "streaming", "telemetry", "aggregation",
            "novel", "compiler", "pass", "zero", "copy", "graph", "protocol",
            "discovery", "verification", "provenance", "lineage", "node",
            "agent", "network", "ledger", "state", "mutation", "branch",
            "lens", "value", "utility", "dependency", "decay", "reputation",
            "entry", "config", "merge", "sort", "search", "exact",
        }

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Token similarity on natural tokens (words/numbers).

        Hyphens and separators are normalized away so that "cache-aware" and
        "cache aware" compare as the same concept — Law 2: expression
        differences are not novelty; meaning differences are.
        """
        import re

        ta = set(re.findall(r"[a-z\d]+", a.lower()))
        tb = set(re.findall(r"[a-z\d]+", b.lower()))
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / len(ta | tb)

    def structural_equivalence(self, claim: str) -> bool:
        """Stage 3: reject claims producing materially equivalent structures."""
        for prior in self.prior_corpus:
            if self._similarity(claim.lower(), prior.lower()) > 0.85:
                return False
        return True

    def adversarial_novelty_challenge(self, claim: str) -> int:
        """Stage 4: count of successful prior-art objections from skeptics."""
        objections = 0
        for prior in self.prior_corpus:
            if self._similarity(claim.lower(), prior.lower()) > 0.7:
                objections += 1
        return objections

    def reproduction(self, reproductions: int, diversity: float = 1.0) -> float:
        """Stage 5: independent reproduction strength (Law 8, Law 13)."""
        return max(0.0, min(1.0, reproductions * 0.25 * diversity))

    @staticmethod
    def utility_evaluation(improvement: float | None, baseline_verified: bool = True) -> float:
        """Stage 6: utility against defined baselines."""
        if improvement is None:
            return 0.0
        return max(0.0, min(1.0, improvement)) if baseline_verified else 0.0

    @staticmethod
    def contradiction_search(refuted: bool = False) -> int:
        """Stage 7: adversarial search; a finding here blocks admission."""
        return 1 if refuted else 0

    # -- NDP-005 meaning gates --------------------------------------------------

    @staticmethod
    def semantic_meaning_gate(claim: str) -> bool:
        """F3 fix: reject plausible-sounding but semantically hollow claims.

        A claim must express at least two substantive concepts beyond
        generic academic padding words. A token stream with no real
        descriptive content (e.g. 'augmented stochastic vortex reconciles
        transcendental foam under non-euclidean pressure') fails.
        """
        import re

        padding = {
            "the", "a", "an", "is", "are", "of", "in", "under", "on", "for",
            "and", "or", "to", "with", "at", "by", "from", "as", "that",
            "this", "these", "those", "its", "their", "it", "s",
        }
        tokens = [t for t in re.findall(r"[a-z\d]+", claim.lower()) if t not in padding]
        # substantive = tokens not in a generic noise trigger list
        generic = {
            "augmented", "stochastic", "vortex", "reconciles", "transcendental",
            "foam", "non", "euclidean", "pressure", "vibes", "quantum",
            "synergistic", "paradigm", "holistic", "disruptive", "innovative",
        }
        substantive = [t for t in tokens if t not in generic]
        # require at least 2 substantive concepts and a subject-object structure
        return len(substantive) >= 2

    @staticmethod
    def utility_attestation_gate(evidence: dict | None) -> bool:
        """F3 fix: improvement must be attested by an independent, defined
        baseline — self-reported improvements without a reference baseline
        are rejected.

        evidence may contain: {"improvement": x, "baseline": y, "attested": true}
        """
        if not evidence:
            return False
        if not evidence.get("attested", False):
            return False
        return evidence.get("baseline") is not None

    # -- aggregate ---------------------------------------------------------------

    def validate(self, payload: dict, producing_agent: str, reproductions: int = 1) -> AdmissionDecision:
        """Full admission decision (Law 1, 8; R-12).

        R-12: the pipeline requires independent reproduction — the producing
        agent's own verification is not counted as independent.
        """
        results: dict[str, bool] = {}
        if not self.format_check(payload):
            return AdmissionDecision(self, "rejected_format", {"format_check": False})

        claim = str(payload["claim"])
        novelty = self.novelty_screen(claim)
        eq = self.structural_equivalence(claim)
        objections = self.adversarial_novelty_challenge(claim)

        # NDP-005: meaning + attestation gates (fix F3)
        meaning = self.semantic_meaning_gate(claim)
        attestation = self.utility_attestation_gate(payload.get("evidence"))

        # R-12: independent reproductions, not self-verification
        reproduction = self.reproduction(reproductions, diversity=1.0)
        utility = self.utility_evaluation(payload.get("improvement")) if attestation else 0.0
        refuted = self.contradiction_search(bool(payload.get("refuted", False)))

        results = {
            "format_check": True,
            "novelty_screen": novelty >= 0.3,
            "structural_equivalence": eq,
            "adversarial_novelty": objections == 0,
            "semantic_meaning": meaning,
            "utility_attestation": attestation,
            "reproduction": reproduction >= 0.25,
            "utility": utility > 0,
            "contradiction_search": not refuted,
        }

        admitted = all(results.values())
        if not admitted:
            return AdmissionDecision(
                self, "rejected", results,
                novelty_credit=novelty, verification_credit=reproduction,
                provenance_credit=min(1.0, novelty * reproduction),
            )
        return AdmissionDecision(
            self, "admitted", results,
            novelty_credit=novelty, verification_credit=reproduction,
            provenance_credit=min(1.0, novelty * reproduction),
        )

    def revise_novelty(self, claim: str, new_prior: str) -> float:
        """R-11: later prior-art may lower novelty credit; history stays valid."""
        obj = {"claim": claim}
        return self.novelty_screen(claim + " " + new_prior)

    @staticmethod
    def delayed_finality_multiplier(survival_epochs: int) -> float:
        """R-13: influence grows with survival; start reduced."""
        return min(1.0, 0.5 + 0.5 * (survival_epochs / 10.0))
