"""NØD Phase II — Adversarial Validation Suite runner.

Runs all five attack simulations and aggregates the measured metrics
into a single JSON document: research/adversarial/RESULTS.json

Run:  PYTHONPATH=src python research/adversarial/suite_runner.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

here = Path(__file__).resolve().parent

# imports that work both as script (PYTHONPATH=src) and under pytest
if str(here) not in sys.path:
    sys.path.insert(0, str(here))

import fake_discovery_attacks
import novelty_spoofing
import sybil_simulation
import collusion_simulation
import dependency_farming


def run_all() -> dict:
    attacks = [
        fake_discovery_attacks.run(),
        novelty_spoofing.run(),
        sybil_simulation.run(),
        collusion_simulation.run(),
        dependency_farming.run(),
    ]
    summary = {
        "protocol": "NØD Protocol",
        "phase": "II — Adversarial Validation",
        "generated": True,
        "attacks": attacks,
    }
    return summary


def main() -> None:
    results = run_all()
    out = here / "RESULTS.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
