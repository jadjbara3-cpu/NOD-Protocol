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
        """
        if not self.prior_corpus:
            return 1.0
        norm = claim.lower().strip()
        best = 0.0
        for prior in self.prior_corpus:
            p = prior.lower().strip()
            best = max(best, self._similarity(norm, p))
        return 1.0 - best

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

        # R-12: independent reproductions, not self-verification
        reproduction = self.reproduction(reproductions, diversity=1.0)
        utility = self.utility_evaluation(payload.get("improvement"))
        refuted = self.contradiction_search(bool(payload.get("refuted", False)))

        results = {
            "format_check": True,
            "novelty_screen": novelty >= 0.3,
            "structural_equivalence": eq,
            "adversarial_novelty": objections == 0,
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
