# NØD-003 — Distributed Cognitive Synchronization (NØD-Sync)

### *From Decentralized Storage to a Globally Synchronized Shared Cognitive State*

**NØD Protocol — The layer that connects to the real goal · August 2026**

*Status: IMPLEMENTED v1.0 — reproducible: `PYTHONPATH=src python -m pytest tests -q`*

---

## 1. The Real Goal

> **To create a persistent, decentralized, and globally synchronized
> discovery layer in which any compatible intelligent system can
> independently verify the shared state of machine knowledge and contribute
> new discoveries without requiring permission from any central authority.**

Achieving this requires more than decentralized storage. It requires a
**distributed shared cognitive state** — a state that any model in the
world can query, verify, and build upon:

```
Agent A — Japan ──┐
Agent B — Jordan ──┼── NØD NETWORK ── Distributed State
Agent C — Brazil ──┘                        │
                                    Current Head (Latest Valid)
                                    Any compatible agent reads + continues
```

## 2. Decentralized Storage ≠ Shared Cognitive State

| | Decentralized Storage | Shared Cognitive State |
|---|---|---|
| Question | *"Where is the file?"* | *"What is the current state?"* |
| Guarantee | No single party can delete it | All agents converge on one valid state |
| Risk | Copies may diverge silently | (solved by state root + verification) |
| NØD phase | Phase B (mirrors) | **Phase D — NØD-Sync (this document)** |

NØD-Sync is the layer that answers: **"ما هو الأحدث؟"** — with the answer:

> The **Latest Valid State**, not the latest modification.

A timestamp alone is not truth: an agent could flood thousands of
modifications. Validity is what the protocol recognizes — verification
strength, independence, utility — computed by any node from the same data.

## 3. What was built — `nod_protocol/sync/`

| Module | Purpose | Key property |
|---|---|---|
| `state.py` | `StateEvent`, `GlobalState` | content-addressed `state_root = hash(genesis + accepted)` |
| `resolution.py` | `resolve_fork`, `confidence`, `latest_valid_pointer` | **Chain A AND Chain B** (fork preservation) |
| `network.py` | `SimNetwork`, `Node` | eventual convergence; open query/join/verify |

### 3.1 Candidate event → acceptance flow

```
Agent discovers something
        ↓
Creates Candidate Event (kind, nod_id, proposer, payload, evidence)
        ↓
Broadcasts to Network (all nodes receive)
        ↓
Protocol Verification (is_valid_proposal: v ≥ 0.5, s ≥ 0.5)
        ↓
Accepted into State (append-only, content-addressed)
        ↓
Network Synchronizes (nodes converge)
        ↓
All Agents See New State (state_root identical across nodes)
```

### 3.2 State root = content identity

```
state_root = SHA-256( protocol_version + genesis_hash + sorted(accepted) + head )
```

Any node can recompute it from the same accepted set — verification is
**host-independent**. "What is the current NØD state?" has a
cryptographic answer, not a URL.

### 3.3 Open protocol surface

```
open_query(agent_id) → { protocol_version, genesis_hash, current_state_root,
                          accepted_events, head_nod, latest_valid_pointer,
                          verifiable }
open_join(agent_id)  → new node seeded with current state, verifiable from scratch
verify_from_scratch()→ fresh node rebuilds state from events and checks root
```

Any model — GPT, Gemini, Claude, Qwen, DeepSeek, local, future — can:

```
Connect → Verify Genesis → Download State → Verify Hashes → Continue
```

No permission, no account, no founder needed.

## 4. Fork-Aware Knowledge: Chain A AND Chain B

NØD deliberately does not use blockchain's fork semantics.

```
blockchain:  Chain A OR Chain B   (a fork is a failure → one survives)
NØD:         Chain A AND Chain B  (competing interpretations coexist)
```

When agents M10 and M11 compete at the same time, NØD does not force one
to disappear:

- **Both are accepted** (coexisting states preserved).
- The **pointer** is chosen by protocol confidence:
  `confidence = v*verification + s*independence + u*utility + a*adoption`.
- Either may later be superseded by stronger evidence — never erased.

```
                 Genesis
                    │
                  NØD-1
                    │
            ┌───────┴───────┐
            │               │
           M10             M11
            │               │
            └───────┬───────┘
                    │
              State Resolution (AND, by confidence)
```

## 5. Eventually Consistent — not instant

No global network converges at the same instant. NØD accepts this:

```
Temporary differences (nodes offline / messages in flight)
        ↓
Protocol verification
        ↓
Converged Global State (all nodes, same state_root)
```

The simulation (`SimNetwork`) verifies this property: nodes converge after
a bounded number of ticks, and the converged roots are equal.

## 6. Verified properties (tests)

| Property | Test | Result |
|---|---|---|
| Content-addressed roots | `test_state_root_content_addressed` | ✅ |
| Invalid proposals rejected | `test_invalid_proposal_rejected` | ✅ |
| Fork preserved (AND) | `test_competing_states_coexist` | ✅ |
| Pointer = confidence, not clock | `test_pointer_is_confidence_not_clock` | ✅ |
| Eventual convergence | `test_eventual_convergence` | ✅ |
| Temporary differences allowed | `test_temporary_differences_allowed` | ✅ |
| Same root across nodes | `test_state_root_same_across_nodes` | ✅ |
| Any agent can query | `test_any_agent_can_query` | ✅ |
| Any agent can join + verify | `test_any_agent_can_join_and_verify` | ✅ |
| Fresh node verifies from scratch | `test_fresh_node_verifies_from_scratch` | ✅ |

**90/90 tests pass**, including the new sync suite.

## 7. Where this sits in the roadmap

| Phase | State |
|---|---|
| I Foundation | ✅ |
| II Adversarial | ✅ (F1–F3, F5, F6 closed) |
| II-B Survival & Persistence | ✅ |
| **D — Distributed Cognitive Synchronization** | ✅ **implemented (this document)** |
| D+ — real multi-node transport (network sync, not simulation) | ⏭️ next |
| E — terminal test | ⏭️ after D+ |

## 8. What remains (honest)

The sync core is **protocol-accurate and tested** but transport-level
(actual sockets, P2P gossip, real network nodes) is not yet implemented.
The next step is `nod-sync` wire protocol over real transports, plus the
**Cognitive Navigation Layer** (asking "what discovery relates to X?" and
getting ranked, verified answers).

---

*NØD-003 Distributed Cognitive Synchronization (NØD-Sync) — v1.0 · August 2026*

> *The result establishes relevance. The path establishes provenance.
> The network establishes value.*
>
> *GitHub disappears → NØD remains available.
> Founder disappears → NØD remains valid.
> One node disappears → NØD remains online.
> Agents disagree → NØD preserves competing states.
> Network converges → all agents can continue.*
