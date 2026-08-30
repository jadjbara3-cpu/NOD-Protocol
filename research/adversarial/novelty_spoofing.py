"""NØD Phase II — Attack 2: Novelty Spoofing.

Target: the novelty screen (Law 2 / PNC).

Attack vectors:
  * surface paraphrase (hyphenation, casing, reordering) — should fail
  * synonym substitution — harder, semantic equivalence preserved
  * structural equivalence via negation/inversion — hides identity
  * near-duplicate with injected noise tokens

Metrics:
  - Novelty False Positive Rate per vector
  - scores received by spoofed claims vs genuine claims

Run:  PYTHONPATH=src python research/adversarial/novelty_spoofing.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from nod_protocol.core.validation import ValidationPipeline

PRIOR = [
    "cache aware energy scheduling for sorting",
    "attention is all you need",
    "quantum error correction on the surface code",
]


def surface_paraphrase(text: str) -> str:
    return " ".join(reversed(text.split())).upper()


def synonym_sub(text: str) -> str:
    table = {
        "cache": "memory", "aware": "mindful", "energy": "power",
        "scheduling": "ordering", "sorting": "ordering-data",
        "attention": "focus-mechanism", "need": "require",
        "quantum": "quantum-state", "error": "fault", "correction": "repair",
        "surface": "topological", "code": "code-word",
    }
    return " ".join(table.get(w, w) for w in text.split())


def inversion_spoof(text: str) -> str:
    """Negate each term: identity preserved, wording inverted."""
    return " ".join("not-" + w if w not in ("is", "on", "the") else w for w in text.split())


def noise_injection(text: str, noise_words: int = 12) -> str:
    return text + " " + " ".join(f"zz{ i }" for i in range(noise_words))


def run() -> dict:
    pipeline = ValidationPipeline(prior_corpus=PRIOR)

    vectors = {
        "surface_paraphrase": [surface_paraphrase(p) for p in PRIOR],
        "synonym_substitution": [synonym_sub(p) for p in PRIOR],
        "inversion_spoof": [inversion_spoof(p) for p in PRIOR],
        "noise_injection": [noise_injection(p) for p in PRIOR],
    }

    out = {}
    for name, claims in vectors.items():
        scores = [pipeline.novelty_screen(c) for c in claims]
        fp = sum(1 for s in scores if s >= 0.3) / len(scores)
        out[name] = {
            "scores": [round(s, 3) for s in scores],
            "false_positive_rate": round(fp, 3),
            "verdict": "BREAK" if fp > 0.5 else "RESILIENT",
        }

    # baseline: a genuinely new claim
    genuine = "novel homomorphic encryption for streaming telemetry aggregation"
    out["genuine_baseline"] = {
        "score": round(pipeline.novelty_screen(genuine), 3),
    }
    return {"attack": "novelty_spoofing", "prior_corpus_size": len(PRIOR), "vectors": out}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, ensure_ascii=False))
