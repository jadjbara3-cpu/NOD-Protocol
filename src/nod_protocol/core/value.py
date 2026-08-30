"""Composite value — Thresholded Weighted Composition (spec §5, Law 9).

Vn = wU·U + wN·N + wV·V + wD·D + wP·P

with admission thresholds first:

    Novelty ≥ Nmin
    Verification ≥ Vmin
    Provenance ≥ Pmin
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from nod_protocol.core.provenance import ProvenanceChain


@dataclass(frozen=True)
class ComponentWeights:
    """Domain-sensitive weights (spec §5.2 — conceptual starting ranges).

    No permanent universal weights are claimed; defaults sit inside the
    recommended ranges and users may pass their own.
    """

    utility: float = 0.25
    novelty: float = 0.20
    verification: float = 0.25
    dependency: float = 0.20
    provenance: float = 0.10

    def normalized(self) -> "ComponentWeights":
        total = self.utility + self.novelty + self.verification + self.dependency + self.provenance
        if total <= 0:
            raise ValueError("weights must sum to a positive value")
        return ComponentWeights(
            utility=self.utility / total,
            novelty=self.novelty / total,
            verification=self.verification / total,
            dependency=self.dependency / total,
            provenance=self.provenance / total,
        )


@dataclass
class ComponentScore:
    utility: float = 0.0
    novelty: float = 0.0
    verification: float = 0.0
    dependency: float = 0.0
    provenance: float = 0.0

    def __getitem__(self, key: str) -> float:
        return getattr(self, key)

    def to_dict(self) -> dict:
        return {
            "utility": self.utility,
            "novelty": self.novelty,
            "verification": self.verification,
            "dependency": self.dependency,
            "provenance": self.provenance,
        }


class ValueComposer:
    """Computes composite NØD value under Law 9."""

    def __init__(
        self,
        weights: ComponentWeights | None = None,
        novelty_min: float = 0.3,
        verification_min: float = 0.3,
        provenance_min: float = 0.5,
    ) -> None:
        self.weights = (weights or ComponentWeights()).normalized()
        self.novelty_min = novelty_min
        self.verification_min = verification_min
        self.provenance_min = provenance_min

    # -- component helpers ---------------------------------------------------------

    @staticmethod
    def utility_score(improvement: float | None, baseline_verified: bool = True) -> float:
        """U: measured against a defined baseline; unverified improvement gets 0."""
        if improvement is None:
            return 0.0
        score = min(1.0, max(0.0, improvement))
        return score if baseline_verified else 0.0

    @staticmethod
    def novelty_from_similarity(similarity_to_prior: float) -> float:
        """N: paraphrase/similarity → ~0 credit; material distance → high."""
        # Law 2: expression differences are not novelty — similarity is measured
        # on structure/meaning, so a near-identical structure scores ~0.
        return max(0.0, min(1.0, 1.0 - similarity_to_prior))

    @staticmethod
    def verification_strength(
        independent_reproductions: int,
        verifier_diversity: float = 1.0,
        formal_proof: bool = False,
        adversarial_outcomes: int = 0,
    ) -> float:
        """V: diminishing returns + collaboration discount (Law 13).

        1 - 0.5^n: the difference between 0 and 3 verifications matters more
        than between 100 and 103 (spec §5.3 boundedness).
        """
        base = 1.0 - 0.5 ** max(0, independent_reproductions)
        if formal_proof:
            base = max(base, 0.9)
        base += min(0.2, adversarial_outcomes * 0.05)
        # diversity in [0,1]; correlated verifiers reduce strength
        return max(0.0, min(1.0, base * verifier_diversity))

    @staticmethod
    def provenance_score(chain: ProvenanceChain) -> float:
        return chain.provenance_sufficiency()

    # -- composite ---------------------------------------------------------------

    def admit(self, scores: ComponentScore) -> bool:
        """Thresholds first (spec §5.1)."""
        return (
            scores.novelty >= self.novelty_min
            and scores.verification >= self.verification_min
            and scores.provenance >= self.provenance_min
        )

    def value(self, scores: ComponentScore) -> float:
        """Vn (spec §5.2) — only meaningful when admitted."""
        if not self.admit(scores):
            return 0.0
        return (
            self.weights.utility * scores.utility
            + self.weights.novelty * scores.novelty
            + self.weights.verification * scores.verification
            + self.weights.dependency * scores.dependency
            + self.weights.provenance * scores.provenance
        )

    def evaluate(self, scores: ComponentScore) -> dict:
        return {
            "admitted": self.admit(scores),
            "components": scores.to_dict(),
            "value": self.value(scores),
        }

    @staticmethod
    def clamping(v: float) -> float:
        return max(0.0, min(1.0, v))
