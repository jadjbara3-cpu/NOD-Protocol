# Phase II — Adversarial Validation

This is where NØD attempts to **break itself before the world does.**

## Suite

```bash
PYTHONPATH=src python research/adversarial/suite_runner.py
```

Runs five attack simulations and writes `RESULTS.json`:

| File | Attack | Key metrics |
|---|---|---|
| `fake_discovery_attacks.py` | Fake discoveries (paraphrase, synonym, garbage, padding, branches) | False Discovery Admission Rate, Novelty FP, Provenance Gaming |
| `novelty_spoofing.py` | Novelty spoofing (surface/synonym/inversion/noise) | Novelty FP Rate per vector |
| `sybil_simulation.py` | 1 honest vs 50 sybils | Sybil detectability, dependency inflation |
| `collusion_simulation.py` | Self-rewarding economy vs independent | Discrimination index |
| `dependency_farming.py` | Cycles + low-info farm | Surviving inflation |

## Results

Measured findings are documented in
[`docs/NOD-001-ADVERSARIAL-MODEL.md`](../../docs/NOD-001-ADVERSARIAL-MODEL.md) —
threat model, attack classes, failures (F1–F4), partials (F5–F6), and
required changes (NDP-001..005).

**Current verdict:** strong on Sybil/collusion/dependency; **breakable on
novelty semantics and admission gates** — exactly what NØD-001 required us
to find.
