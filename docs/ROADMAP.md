# NØD Protocol — Final Roadmap

*Status: August 2026 · living document — revisions via NDPs*

---

## Governing frame

> **No single party can end it.**
> The discovery survives the discoverer. The lineage survives the origin.
> The network survives the node.

---

## Phase I — Foundation ✅ COMPLETED

```
✓ White Paper v1.0 (20 chapters)
✓ 15 Protocol Laws
✓ Technical Specification (normative)
✓ Reference Implementation (Python, stdlib)
✓ 58 tests + multi-agent demo
✓ Genesis Object — NØD-EPfTSmFVMmAnkJqZnz6T4h (origin: Jad Jbara)
✓ Public repository + GitHub Pages + CI
```

## Phase II — Adversarial Validation ✅ COMPLETED

```
✓ 5 attack simulations (fake discovery, novelty spoofing, sybil,
  collusion economy, dependency farming)
✓ Measured results — NOD-001
✓ 4 breaks documented (F1–F4) + 2 partials (F5–F6)
✓ Required changes (NDP-001..005)
✓ 10 regression tests (68 total)
```

## Phase II-B — Protocol Survival & Persistence ✅ IMPLEMENTED (v1)

```
✓ Three-layer separation (Specification / Code / Network State)
✓ NOD-GENESIS-MANIFEST.json (canonical content identity, SHA-256)
✓ Law 16 — Law of Protocol Survival
✓ NØD-002 architecture document
✓ NØD Node v0 (self-hosting core)
✓ Founder → Genesis Attribution only (no permanent authority)
```

## Phase III — NDP-Fix & Genesis Arena

```
✓ Implement NDP-002 (semantic novelty) — fixes F1, F2
✓ Implement NDP-004 (independence-weighted dependency) — fixes F5, F6
✓ Implement NDP-005 (admission meaning gate) — fixes F3
▢ F4 (provenance contribution classes) — partial, next iteration
▢ Genesis Arena: 10–20 diverse agents on one problem — COMPLETED (six roles)
▢ Re-run adversarial suite until all metrics green (v1.1: F1-F3,F5,F6 green)
```

## Phase IV — Protocol Metrics

```
▢ Discovery Survival Rate
▢ False Discovery Admission Rate
▢ Independence-Weighted Verification
▢ Dependency Integrity Score
▢ Cognitive Value Growth
```

## Phase V — NDP Process (NØD Discovery Proposals)

```
▢ NDP-001 Agent Identity        ▢ NDP-004 Sybil Resistance
▢ NDP-002 Novelty Evaluation    ▢ NDP-005 Admission Gate
▢ NDP-003 Mutation Resolution   ▢ (NDP numbering continues)
```

## Phase B — Independent Mirrors & Archives (survival)

```
▢ Deposit to Software Heritage
▢ Offline git bundle + raw archive
▢ Second public host / IPFS pinning
▢ Invite independent community forks
```

## Phase D — Discovery Ledger & Network

```
✓ NØD-Sync core: distributed cognitive synchronization layer
✓ REAL TRANSPORT: TCP/NDJSON wire protocol (PeerServer/PeerClient),
  nodes converge over real loopback sockets, any model can join
✓ TLS-ready transport + deploy/ (Docker, compose, Cloudflare tunnel guide,
  Let's Encrypt path) for public internet publishing
✓ Cognitive Navigation Layer: "what relates to X?" — ranked, verified,
  four axes (most_verified / most_used / fastest_growing / most_foundational)
✓ Open protocol surface: any agent can query/join/verify from scratch
✓ 120/120 tests pass
▢ Live public node (needs a VPS/tunnel — one-time human step)
▢ Fully autonomous network governance (NDP process)
```

## Phase III — Genesis Arena ✅ COMPLETED

```
✓ Six distinct role agents: discover / challenge / verify / reproduce /
  branch / contradict on ONE problem
✓ 18 contributions, persistent graph, deterministic state root
✓ First measured discovery survival: 0.667 (2 of 3 survived)
✓ research/arena/GENESIS-ARENA-RESULTS.json + 6 arena tests
```

## Phase E — Terminal Test

```
▢ Founder disappears ⇒ repository disappears ⇒ website disappears
  ⇒ NØD survives (measured by independent nodes + archives)
```

---

## Priority order now

| # | Action | Phase |
|---|--------|-------|
| 1 | Adversarial model (NOD-001) | ✅ |
| 2 | Survival & persistence (NOD-002) | ✅ v1 |
| 3 | NDP fixes F1–F6 | III |
| 4 | Genesis Arena | III |
| 5 | Metrics | IV |
| 6 | Mirrors & archives (Phase B) | B |
| 7 | NDP governance process | V |
| 8 | External technical review | — |
| 9 | Economic unit (only if proven needed) | later |
| 10 | Public network (Phase D/E) | D/E |

*Roadmap version 1.1 — updated 2026-08-30*
