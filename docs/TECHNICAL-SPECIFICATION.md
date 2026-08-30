# NØD Protocol — Technical Specification

**Version 1.0 — Specification Reference for the Reference Implementation**

*This specification is the normative technical companion to the NØD White Paper v1.0. It defines the implementable data structures, event chains, state mechanics, and value composition that the reference implementation (`src/nod_protocol`) realizes.*

---

## 1. Scope

The reference implementation realizes a **minimal, deterministic, offline-first** core of the NØD Protocol:

- Persisting NØD objects with Verifiable Cognitive Provenance Chains (VCPC).
- Maintaining immutable history with a Cognitive State Layer (Genesis states, Mutations, Current State Pointer).
- Building a discovery lineage graph (branches, contradictions, dependencies).
- Computing composite value under a thresholded weighted composition.
- Validating candidates through a staged pipeline (novelty screen, verification, admission).
- Simulating a small multi-agent environment (Cognitive Arena).

No consensus mechanism, no network layer, no native token, no legal ownership model is implemented. These remain explicitly open (Section 10).

---

## 2. Provenance

### 2.1 Provenance Event

A `ProvenanceEvent` is an immutable record with fields:

```
event_id          (str)      — canonical identifier (hash of content)
nod_id            (str)      — owning object id
event_type        (enum)     — problem_state | committed_hypothesis | test | result | transformation | verification | mutation | contradiction | branch
parent_event_ids  (list)     — cryptographic references to predecessors
agent_identity    (str)      — DID-like identifier
agent_signature   (str)      — signature over event bytes
timestamp_or_order (int)     — monotonic order attestation
content_hash      (str)      — sha256 of canonical content
artifact_reference (str|None)— external reference (e.g. ipfs://...)
execution_reference (str|None)— environment/program reference
verification_reference (str|None)
commitment_reference (str|None) — hidden-state commitment hash
disclosure_status  (enum)    — open | committed_only
protocol_version   (str)     — "1.0"
```

### 2.2 VCPC (Verifiable Cognitive Provenance Chain)

A NØD SHALL contain an ordered chain of events. The canonical chain for a minimal discovery:

```
problem_state → committed_hypothesis → test → result → transformation → verification
```

Rules:

- **R-1** The chain is append-only; no event may be modified after commitment.
- **R-2** Every event links to at least one parent event (or to genesis for the first).
- **R-3** `content_hash` commits the event fields; changing any field changes the id.
- **R-4** Internal reasoning (chain-of-thought, activations, weights, prompts) is **never recorded.**
- **R-5** A hypothesis MAY be `committed_only` (hidden) until disclosure; `commitment_reference` holds its hash.
- **R-6** Longer chains do not by themselves increase value (Law 3 / Law 9).

### 2.3 What is never recorded

Raw hidden chain-of-thought, private model activations, model weights, proprietary inference traces, confidential prompts, private datasets (unless explicitly contributed), credentials, hidden memory contents, unrestricted internal deliberation.

---

## 3. Object and State Layer

### 3.1 NODObject

```
nod_id                 (str)    — "NØD-" + base58(sha256(claim+agent+order)[:16])
genesis_state          (str)    — state id "G0"
discovery_claim        (dict)   — {description, domain, evidences_keys}
discovery_domain       (str)
provenance_root        (str)    — event_id of chain root
provenance_event_ids   (list)
verification_status    (enum)   — pending | verified | challenged | contradicted | archived
lineage_references     (list)   — parent ids
current_state_pointer  (str)    — points to active state (G0 → M1 → M2)
rights_registry_reference (dict) — {origin_positions: [...], licenses: [...]}
value_metrics_reference  (dict) — cached component values
protocol_version       (str)    — "1.0"
```

### 3.2 Cognitive State Layer

- States: `G0` (genesis), `M1`, `M2`, ... — immutable, append-only.
- `Current State Pointer` advances only through an accepted state event.
- **R-7** States are never deleted or overwritten. `superseded` is a status, not a deletion.
- **R-8** Conflicting states may coexist; pointer selection uses a confidence function:

```
confidence(state) = w_v * verification_strength
                  + w_s * independent_support
                  + w_u * downstream_utility
                  + w_c * contradiction_delta
                  + w_a * sustained_adoption
```

- **R-9** Mutation admission: any qualified agent may propose; evidence must demonstrate material change of interpretation (not paraphrase, minor extension, new application, or simple descendant).

### 3.3 Mutation evidence requirements

```
Original Interpretation
        ↓
New Evidence
        ↓
New Interpretation
        ↓
Demonstrable Consequence
```

Adversarial sequence: proposal → novelty/materiality review → independent reproduction → adversarial challenge → verification decision → state registration.

---

## 4. Lineage

- **Branch** (Law 5): a materially distinct extension creates a new object (`NØD-100-B`) with `parent = NØD-100`; never merged into ancestor.
- **Contradiction** (Law 7): a verified contradiction creates a Counter-NØD object with an adversarial edge to the challenged object or state.
- **Dependency** edges carry weight; **R-10** self-dependency, cycles, and low-information descendants are penalized (Law 13 / Layer 8).
- Graph metrics computed for value: direct descendants, weighted dependency, lens adoption, derivative count.

---

## 5. Value Composition

### 5.1 Admission thresholds (Law 9)

```
Novelty ≥ Nmin
Verification ≥ Vmin
Provenance ≥ Pmin
```

### 5.2 Then composite value

```
Vn = wU*U + wN*N + wV*V + wD*D + wP*P
```

Conceptual starting ranges (domain-sensitive, NOT fixed for all time):

```
Discovery Utility         20–30%
Novelty                   15–25%
Verification Strength     20–30%
Future Dependency         15–30%
Cognitive Provenance       5–15%
```

### 5.3 Component definitions (normalized 0..1)

| Component | Definition | Measurement inputs | Anti-gaming |
|---|---|---|---|
| Utility (U) | measurable improvement | benchmark delta, error reduction, efficiency, resolution, external validation | must be measured against defined baselines; reproducible; not self-selected conditions |
| Novelty (N) | material distance from prior knowledge | semantic distance, structural comparison, prior-art retrieval, formal equivalence, novelty review | paraphrase gets ~0 credit; bounded |
| Verification Strength (V) | survived independent evaluation | # reproductions, verifier diversity, deterministic checks, formal proof, challenge outcomes, survival duration | correlated (common-control) verifiers discounted; diminishing returns |
| Future Dependency (D) | downstream dependence | descendants, weighted edges, lens adoption, derivatives, criticality | self-generated descendants and circular refs → zero/reduced weight; nonlinear |
| Cognitive Provenance (P) | integrity of discovery history | completeness of event classes, cryptographic continuity, attestations, temporal consistency | length ≠ value; evidentiary sufficiency, saturation cap |

---

## 6. Validation Pipeline (Law 1, 2, 8)

Stages for a candidate:

```
1. format_check        — structured, complete, canonical claim
2. novelty_screen      — against registered NØDs + prior corpus (domain registry)
3. structural_equivalence — where possible, compare formal/structural identity
4. adversarial_novelty_challenge — skeptic agents may raise prior-art objections
5. reproduction        — independent verifiers reproduce result (or deterministic check)
6. utility_evaluation  — baseline comparison
7. contradiction_search — adversary search for refutations
8. registration        — NØD created if thresholds met
```

Rules:

- **R-11** Novelty status is revisable: later prior-art discovery may lower N; object stays historically valid as an event.
- **R-12** Producer is never sole authority (Law 8).
- **R-13** Delay finality: object starts with reduced weight; influence grows with survival (Layer 4).

---

## 7. Anti-Manipulation (Law 13, 14)

Implemented primitives in the reference core:

- Identity cost: each agent has a persistent identity; `independence_score` combines known diversity signals.
- Correlation discount: verifiers sharing operator/model/infra id get reduced weight.
- Circular dependency suppression: cycle detection + penalty (`cycle_penalty = 0.25 * number_of_cycles` cap).
- Delayed finality: `weight_multiplier` = min(1, 0.5 + 0.5 * survival_epochs/10).
- Sybil note: reference implementation does NOT implement decentralized identity (open item); tests assert that multiplicity of identity alone does not raise independence scores.

---

## 8. Cognitive Lens (Law 15)

A `CognitiveLens` object: `{lens_id, claim_origin, method_signature, abstraction_level, rights_owner, license_state}`. Lenses may be referenced, licensed, combined.

---

## 9. Arena (simulation)

`Arena.run(challenge, agents, rounds)`: deterministic random; each agent runs `propose()` → `evaluate(score = U*N*V*G)`; winner creates Genesis object; other agents may branch. Used by `demo/run_demo.py`.

---

## 10. Explicitly Open (NOT implemented in v1.0)

1. Universal novelty algorithm
2. Consensus mechanism
3. Cryptographic stack selection
4. Storage architecture
5. Universal value weights
6. Final economic unit (no token defined)
7. Legal ownership model
8. Sybil-resistance mechanism
9. Collusion-detection algorithm (heuristics only here)
10. Agent identity standard
11. Mutation materiality threshold (implemented as configurable threshold)
12. Domain-specific verification standards (pluggable interface only)
13. Privacy/selective-disclosure architecture (commitments only)
14. Governance model
15. Formal economic attack modeling

---

*NØD Protocol — Technical Specification v1.0 — August 2026*
