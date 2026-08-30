"""Cognitive Arena — a deterministic multi-agent competition (spec §9).

Each agent proposes a solution; evaluation is U×N×V×G; the winner becomes a
Genesis object; other agents may branch from it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from nod_protocol.core.value import ComponentWeights, ComponentScore, ValueComposer


@dataclass
class ArenaAgent:
    agent_id: str
    strategy: str  # "conservative" | "bold" | "hybrid" — shapes proposals
    skill: float = 0.5

    def propose(self, challenge: dict, rng: random.Random) -> dict:
        base = self.skill * (0.6 if self.strategy == "conservative" else 0.9)
        return {
            "agent_id": self.agent_id,
            "claim": f"{challenge['title']} :: {self.strategy} approach",
            "claim_similarity": max(0.0, min(0.9, rng.random() * (1 - base) * 0.6)),
            "utility": max(0.05, min(0.95, base * rng.uniform(0.7, 1.1))),
            "verification_potential": max(0.05, min(0.95, base * rng.uniform(0.8, 1.2))),
            "generative_potential": max(0.05, min(0.95, base * rng.uniform(0.6, 1.2))),
        }


@dataclass
class ArenaResult:
    challenge: dict
    ranking: list
    winner: ArenaAgent | None
    genesis_id: str | None

    def summary(self) -> str:
        lines = [f"Arena: {self.challenge.get('title')}"]
        for i, entry in enumerate(self.ranking, start=1):
            lines.append(f"  #{i} {entry['agent'].agent_id}: score={entry['score']:.3f}")
        lines.append(
            f"Winner: {self.winner.agent_id if self.winner else 'none'} — genesis_id={self.genesis_id}"
        )
        return "\n".join(lines)


class Arena:
    """Runs a bounded, deterministic competition (seed-driven)."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = random.Random(seed)

    def run(self, challenge: dict, agents: list[ArenaAgent]) -> ArenaResult:
        composer = ValueComposer(
            # arena evaluation: U × N × V × G — weighted composite
            weights=ComponentWeights(utility=0.3, novelty=0.3, verification=0.25, dependency=0.0, provenance=0.15)
        )
        proposals = [a.propose(challenge, self.rng) for a in agents]
        ranking: list[dict] = []

        for agent, proposal in zip(agents, proposals):
            scores = ComponentScore(
                utility=composer.utility_score(proposal["utility"], baseline_verified=True),
                novelty=composer.novelty_from_similarity(proposal["claim_similarity"]),
                verification=composer.verification_strength(1, verifier_diversity=1.0),
                dependency=0.0,
                provenance=0.5,
            )
            admitted = composer.admit(scores)
            score = composer.value(scores) if admitted else 0.0
            # generative potential as tie-break multiplier (arena axis)
            score *= proposal["generative_potential"]
            ranking.append({"agent": agent, "score": score, "proposal": proposal, "admitted": admitted})

        ranking.sort(key=lambda r: r["score"], reverse=True)
        winner = ranking[0]["agent"] if ranking else None
        genesis_id = f"GEN-{winner.agent_id}" if winner else None
        return ArenaResult(challenge=challenge, ranking=ranking, winner=winner, genesis_id=genesis_id)
