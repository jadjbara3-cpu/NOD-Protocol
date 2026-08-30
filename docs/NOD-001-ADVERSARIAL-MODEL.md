# NØD-001 — Adversarial Discovery Model

### *Threats, Simulations, Failure Modes, and Protocol Responses*

**NØD Protocol — Phase II · First official development document after the White Paper**

*Status: DRAFT v1.0 — measured 2026-08-30 · Reproducible: `PYTHONPATH=src python research/adversarial/suite_runner.py`*

---

## 1. Summary

NØD-001 documents the first **falsification experiment suite** for the NØD
Protocol. Five attack classes were implemented and run against the reference
implementation. The suite produced **measured, reproducible metrics** — not
claims — about the protocol's resistance to manipulation.

**Verdict: The protocol is strong on Sybil/collusion/dependency control but
is BREAKABLE on novelty semantics and admission sanity checks.**

| Attack Class | Metric | Result | Verdict |
|---|---|---|---|
| Fake Discovery (paraphrase) | Novelty FP Rate | 0.00 | ✅ RESILIENT |
| Fake Discovery (synonym spoof) | Novelty FP Rate | **1.00** | ❌ **BREAK** |
| Novelty Spoofing (noise injection) | Novelty FP Rate | **1.00** | ❌ **BREAK** |
| Semantic Garbage Admission | False Admission Rate | **1.00** | ❌ **BREAK** |
| Provenance Padding | Provenance Gaming Score | **1.00** | ❌ **BREAK** |
| Sybil (50 vs 1) | Sybil Detectability | detection = True | ✅ RESILIENT |
| Sybil Dependency Inflation | Inflation | 0.115 | ⚠️ PARTIAL |
| Collusion Economy | Discrimination Index | 0.5 | ⚠️ PARTIAL |
| Dependency Farming | Surviving Inflation | −0.15 | ✅ RESILIENT |

---

## 2. Threat Model

NØD assumes adversaries that control one or more agents and act rationally
to extract value without producing genuine discovery:

```
Attacker Capabilities
    ├── control many agent identities (Sybil)
    ├── share operator/infrastructure/model across agents (collusion)
    ├── fabricate provenance records (padding/fake events)
    ├── rephrase prior art (paraphrase, synonym, inversion, noise)
    ├── construct dependency graphs (branches, cycles)
    └── never produce genuine novel cognition
```

Attack objectives ranked by strategic value:
1. **Admit fabricated discoveries** (Laws 1, 2, 9 bypass).
2. **Inflate Future Dependency** of owned objects (Law 9 D-component).
3. **Smuggle verification** through mass identity (Law 13/14 bypass).
4. **Erode provenance signal** (Law 3/R-6 bypass).

---

## 3. Attack Classes

### 3.1 Fake Discovery Attack — `fake_discovery_attacks.py`

| Vector | Description | Measured |
|---|---|---|
| Paraphrase of prior | Surface rewording (reversal, casing, hyphenation) | FP = 0.00 → rejected ✅ |
| Synonym spoof | Lexical substitution preserving meaning | **FP = 1.00 → admitted ❌** |
| Semantic garbage | Plausible-sounding nonsense | **Admission = 1.00 ❌** |
| Padded provenance | 200 no-op events | **Provenance score = 1.00 ❌** |
| Synthetic branches | 25 near-identical derivatives | recorded; no semantic check |

### 3.2 Novelty Spoofing — `novelty_spoofing.py`

| Vector | Scores | FPR | Verdict |
|---|---|---|---|
| Surface paraphrase | [0.0, 0.0, 0.0] | 0.00 | ✅ RESILIENT |
| Synonym substitution | [0.909, 0.625, 0.667] | **1.00** | ❌ **BREAK** |
| Inversion spoof | [0.143, 0.167, 0.125] | 0.00 | ✅ RESILIENT |
| Noise injection | [0.667, 0.706, 0.632] | **1.00** | ❌ **BREAK** |
| Genuine baseline | 0.917 | — | sanity ✅ |

### 3.3 Sybil Agent Attack — `sybil_simulation.py`

1 honest discovery agent vs 50 coordinated agents under one operator:

```
sybil_independence_max       = 0.301   (vs honest min 0.86)
sybil_verification_strength  = 0.000   (vs honest 0.86)
sybil_dependency_usefulness  = 0.990
honest_dependency_usefulness = 0.875
dependency_inflation         = +0.115
sybil_detected               = True    ✅
```

**Findings:** The protocol **zeroes out** sybil verification strength and
collapses independence — strong. But 50 farmed branches still push
`Future Dependency` usefulness from 0.875 → 0.990 (saturating inflation
without any per-branch independence weighting). ⚠️ PARTIAL.

### 3.4 Collusion Economy — `collusion_simulation.py`

Group A (one operator) performs full self-reward loop vs Group B
(independent agents):

```
artificial_verification_strength   = 0.000
independent_verification_strength  = 0.850
artificial_dependency_usefulness   = 0.750
independent_dependency_usefulness  = 0.944
discrimination_index               = 0.5  (middle: separated on verification,
                                           but NOT on dependency)
```

**Findings:** Verification discrimination works; dependency discrimination
is weak. ⚠️ PARTIAL.

### 3.5 Dependency Farming — `dependency_farming.py`

Farmed graph (3 cycles + 20-node chain + near-duplicates) vs honest deep chain:

```
cycles_detected         = 3
cycle_penalty_applied   = 0.75
suppression_multiplier  = 0.00  (fully suppressed)
farmed_usefulness       = 0.600
honest_usefulness       = 0.750
surviving_inflation     = −0.150   ✅ farming FAILED
```

**Finding:** The cycle/dedup machinery correctly suppresses the farm.
✅ RESILIENT.

---

## 4. Protocol Assumptions (tested in NØD-001)

| # | Assumption | Held? |
|---|---|---|
| A1 | Surface paraphrase receives no novelty credit | ✅ |
| A2 | Synonym-equivalent claims receive no novelty credit | ❌ |
| A3 | Noise injection cannot boost novelty | ❌ |
| A4 | Garbage claims fail admission | ❌ |
| A5 | Padding cannot inflate provenance | ❌ |
| A6 | 50 same-operator identities ≠ 50 independent intelligences | ✅ |
| A7 | Artificial verification collapses under correlation discount | ✅ |
| A8 | Farmed dependencies get suppressed | ✅ |
| A9 | Independent use scores above self-rewarding use | ✅ (0.75 vs 0.6) |
| A10 | Deep honest discovery > shallow farm | ✅ |

**Result: 6 of 10 assumptions held. 4 failed — all on the semantics axis.**

---

## 5. Measured Results — failure table

| Failure ID | Attack | Measured evidence | Consequence |
|---|---|---|---|
| F1 | Synonym substitution | 0.909 novelty credit for a paraphrase | Semantically identical claim admitted as novel |
| F2 | Noise injection | 12 random tokens raise novelty 0.0 → 0.667 | Cheap gaming; any attack can bump score |
| F3 | Semantic garbage | 100% admission with fabricated evidence | PNC pipeline has no meaning gate |
| F4 | Padded provenance | 200 no-op events → sufficiency 1.0 | Provenance = volume, not contribution |
| F5 | Sybil dependency | +0.115 inflation despite detection | Branch weight ignores origin independence |
| F6 | Collusion dependency | discrimination 0.5 (blind on D) | Two economies score too similarly |

---

## 6. Required Changes

### NDP-001 — Agent Identity & Correlation
**Status:** NOT REQUIRED (A6/A7 hold — verification side is already strong).
*Differs from earlier assumption; keep verification discount, extend to
dependency weighting.*

### NDP-002 — Novelty Evaluation (Priority — fixes F1, F2)
**Required:** Replace token-overlap novelty with **semantic-structure** scoring:
- Embedding-based semantic distance (or synonym-expanded token graph).
- **Noise tolerance**: subtract entropy of out-of-vocabulary tokens.
- **Equivalence normalization**: canonicalize via synonym dictionary, so
  synonym-substituted claims map to the same prior-art equivalence class.
- Enforce a **minimum evidence of structural change** (e.g., ≥2 new
  relationship tokens, not just reworded existing ones).

### NDP-003 — Mutation Resolution (confirms immutability design)
**Required:** formalize competing-state pointer resolution; current confidence
weights (v/s/u/c/a) are reasonable defaults. No failure measured; NDP-003
is deferred to the next arena phase with real competing mutations.

### NDP-004 — Sybil Resistance (partially required — fixes F5, F6)
**Required:** apply **independence weighting to dependency edges**, not just
verification:
- Each derived edge carries `independence_weight` (from `correlation_discount`
  of the branch creator group).
- `dependency_usefulness` weights edges by independence, so a single operator's
  50 branches contribute ≈ as much as one independent branch.
- Add **semantic diversity requirement** for dependency credit (F3-related):
  a descendant must differ from its ancestor beyond token noise.

### NDP-005 — Admission Meaning Gate (Priority — fixes F3, F4)
**Required:** Add to the Validation Pipeline, before registration:
- **Utility gate**: `improvement` must be attested by an independent baseline
  (not self-reported) — reject fabricated evidence payloads.
- **Contribution gate**: `provenance_sufficiency()` must measure *contribution
  classes*, not event *count*; no-op events (e.g., `{"noop": true}`) are
  scored zero and do not count toward coverage.
- **Transformational check**: at least one material transformation
  (`is_material` style) must exist between problem state and result.

---

## 7. Reproducibility

```bash
git clone https://github.com/jadjbara3-cpu/NOD-Protocol
cd NOD-Protocol
PYTHONPATH=src python research/adversarial/suite_runner.py
# → writes research/adversarial/RESULTS.json
```

All simulations are deterministic and stdlib-only.

---

## 8. What NØD-001 establishes

NØD-001 is the first document that converts the project from:

> *idea + white paper + prototype*

into:

> **a protocol undergoing falsification.**

Four protocol failures are now **measured and documented** (F1–F4), two
partials are characterized (F5, F6), and the protocol's genuine strengths
(Sybil decay, collusion discount, dependency-farm suppression) are confirmed
by evidence — not by assertion.

The next step is Phase III: the NØD Genesis Arena — a small economy of
diverse independent agents creating, verifying, branching, and contradicting
on one problem — built on top of the NDP fixes required here.

---

*NØD-001 Adversarial Discovery Model — Phase II · DRAFT v1.0 · August 2026*
*Governing principle: The result establishes relevance. The path establishes provenance. The network establishes value.*
