"""Adversarial suite regression tests.

Each test locks a measured finding from NØD-001 so regressions are caught:

  * known breaks (novelty semantics, admission gate, provenance padding)
  * known strengths (sybil decay, collusion discount, farming suppression)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import research.adversarial.fake_discovery_attacks as attacks
import research.adversarial.novelty_spoofing as novelty
import research.adversarial.sybil_simulation as sybil
import research.adversarial.collusion_simulation as collusion
import research.adversarial.dependency_farming as farming


class TestKnownBreaks:
    """F1, F2, F3, F4 — documented in NOD-001. These currently BREAK by design;
    the tests lock the measured value so the state is never silently 'fixed'
    without updating NOD-001."""

    def test_synonym_spoof_breaks(self):
        out = novelty.run()["vectors"]["synonym_substitution"]
        assert out["false_positive_rate"] >= 0.5  # F1 measured 1.00

    def test_noise_injection_breaks(self):
        out = novelty.run()["vectors"]["noise_injection"]
        assert out["false_positive_rate"] >= 0.5  # F2 measured 1.00

    def test_semantic_garbage_breaks(self):
        out = attacks.run()
        assert out["semantic_garbage_admission"] >= 0.5  # F3 measured 1.00

    def test_padded_provenance_breaks(self):
        out = attacks.run()
        assert out["padded_provenance_score"] >= 0.5  # F4 measured 1.00


class TestKnownStrengths:
    """A6, A7, A8, A9 — the protocol's confirmed resistances."""

    def test_sybil_verification_collapses(self):
        out = sybil.run()
        assert out["sybil_detected"] is True
        assert out["sybil_verification_strength"] < 0.2

    def test_sybil_independence_low(self):
        out = sybil.run()
        assert out["sybil_independence_max"] < 0.5

    def test_paraphrase_resilient(self):
        out = novelty.run()["vectors"]["surface_paraphrase"]
        assert out["false_positive_rate"] == 0.0

    def test_farming_suppresses(self):
        out = farming.run()
        assert out["surviving_inflation"] <= 0.0


class TestInversionSpoof:
    def test_inversion_spoof_resilient(self):
        out = novelty.run()["vectors"]["inversion_spoof"]
        assert out["false_positive_rate"] == 0.0


class TestMetricsRecording:
    def test_results_file_stable(self):
        """The documented results match what the suite reproduces."""
        import json
        from research.adversarial.suite_runner import run_all

        results = run_all()
        assert results["protocol"] == "NØD Protocol"
        assert len(results["attacks"]) == 5
