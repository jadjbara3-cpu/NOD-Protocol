"""Anti-manipulation primitives — Law 13, 14 and spec §7.

- identity cost / independence scoring
- correlation discount for verifiers under common control
- circular dependency suppression (cycles, self-dependency, low-info descendants)
- delayed finality
- Sybil principle: multiplicity of identity is not evidence of
  multiplicity of intelligence
"""

from __future__ import annotations


def independence_score(agent: dict) -> float:
    """Score in [0,1]; does not rise with identity count.

    ``agent`` fields: operator, execution_env, model, region, economic_owner,
    verified_reputation, identity_count.
    """
    signals = {
        "distinct_operator": 0.30 if agent.get("operator", "") else 0.0,
        "distinct_execution_env": 0.25 if agent.get("execution_env", "") else 0.0,
        "distinct_model": 0.15 if agent.get("model", "") else 0.0,
        "distinct_region": 0.10 if agent.get("region", "") else 0.0,
        "economic_separation": 0.10 if agent.get("economic_owner", "") else 0.0,
        "reputation": 0.10 * min(1.0, agent.get("verified_reputation", 0.0)),
    }
    score = sum(signals.values())
    # Sybil: identity multiplication must never create equivalent authority.
    # A thousand identities under one operator do NOT raise the score.
    icount = max(1, int(agent.get("identity_count", 1)))
    score /= min(3.0, float(icount) ** 0.25)
    return max(0.0, min(1.0, score))


def correlation_discount(verifier_group: list[dict]) -> float:
    """Discount factor for a group of verifiers in [0,1].

    Law 14: repeated evidence from common control / common execution / common
    model weighs much less. The discount is computed as the product of
    attribute-diversity factors: for each diversity signal, if all verifiers
    share the same value, that signal contributes ~0.

    Returns a multiplier applied to base verification strength.
    """
    if not verifier_group:
        return 0.0
    n = len(verifier_group)
    signals = ("operator", "execution_env", "model", "economic_owner")

    diversity = 1.0
    for key in signals:
        values = {(v.get(key) or "<none>") for v in verifier_group}
        if n <= 1:
            continue
        if len(values) == 1:
            # everyone shares this attribute → no independence credit from it
            diversity *= 0.10
        else:
            # some variety → partial credit scaled by real diversity
            diversity *= 0.5 + 0.5 * (len(values) / n)

    # reputation alone must never rescue a fully correlated group
    weakest = min(independence_score(v) for v in verifier_group)
    return max(0.0, min(1.0, weakest * diversity))


def circular_dependency_suppression(cycle_count: int, self_refs: int = 0, low_info: int = 0) -> float:
    """Penalty multiplier in [0,1] for dependency inflation (Layer 8)."""
    penalty = 0.25 * cycle_count + 0.15 * self_refs + 0.10 * low_info
    return max(0.0, min(1.0, 1.0 - penalty))


def delayed_finality_multiplier(survival_epochs: int, max_epochs: int = 10) -> float:
    """R-13: objects start at reduced weight; grow with survival."""
    return min(1.0, 0.5 + 0.5 * (survival_epochs / max_epochs))


def effective_verification_strength(
    base_strength: float, verifier_group: list[dict], survival_epochs: int = 0
) -> float:
    """Compose: base × independence discount × delayed finality."""
    discount = correlation_discount(verifier_group)
    return max(0.0, base_strength * discount * delayed_finality_multiplier(survival_epochs))


MULTIPLICITY_PRINCIPLE = "Multiplicity of identity is not evidence of multiplicity of intelligence."
