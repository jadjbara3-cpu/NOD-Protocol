# NØD-002 — Protocol Survival and Persistence Architecture

### *Canonical Identity, Content Addressing, Independent Mirrors, and the Self-Hosting Path*

**NØD Protocol — Phase II/B · Second official development document**

*Status: PROPOSED v1.0 · August 2026*

---

## 1. The Problem

NØD's founding claim is that a verified discovery persists beyond its
discoverer, and that knowledge survives its originators. If the protocol
does not apply that same principle to itself, it is rhetoric.

Today the project lives on GitHub under a single account:

```
GitHub Account (jadjbara3-cpu)
        ↓
NØD exists
```

That is a single point of institutional failure. Deleting the account or
the repository would end the primary publication point. Independent forks,
GitHub Archive Program, and Software Heritage mitigate but do not remove
this dependence.

**The asymmetric requirement:** NØD must be structurally capable of
surviving the disappearance of its founder, its repository, its domain,
and every single hosted node.

---

## 2. The Three-Layer Separation

NØD is separated into three independent layers that must never share a
single point of failure:

```
              NØD PROTOCOL
                   │
     ┌─────────────┼─────────────┐
     │             │             │
 Specification   Code        Network State
     │             │             │
   Immutable    Forkable      Replicated
     │             │             │
   Archives     Mirrors      Independent Nodes
```

| Layer | Property | Anti-fragility mechanism |
|---|---|---|
| **Specification** | Immutable | Content-addressed; versions form an append-only MDP chain |
| **Code** | Forkable | Open license; multiple independent implementations allowed |
| **Network State** | Replicated | Any node can replay the full ledger from Genesis Object |

The three layers are versioned *together* through the **NØD Genesis
Manifest** so that a given specification hash corresponds to a given
implementation and can be verified independently of where it is found.

---

## 3. Canonical Cryptographic Identity

The identity of NØD is **not** a repository URL, an account, or a website.
It is a set of content hashes:

```
NØD Specification
        ↓
Canonical Cryptographic Identity (SHA-256)
        ↓
Multiple Independent Mirrors
        ↓
Anyone Can Run an Implementation
```

`NOD-GENESIS-MANIFEST.json` records the SHA-256 of every foundational
document (White Paper, Laws, Spec, NOD-001, implementation files, tests).
Anyone who retrieves a copy from any mirror can verify:

```
Retrieved file
      ↓
SHA-256
      ↓
Hash matches manifest?
      ↓
Canonical document verified
```

**This is content addressing applied to NØD itself.** The question
changes from *"Where is the file?"* to *"What is the file?"* — and the
answer is a hash.

### 3.1 Why content addressing matters for survival

- An entity can be mirrored to arbitrary locations without losing identity.
- A tampered copy is immediately detectable (hash mismatch).
- A new independent implementation must satisfy the same spec hash to count
  as NØD.
- No domain or account can claim to be "the" NØD; the identity is the
  content, not the host.

---

## 4. Genesis Manifest

First primary artifact of this architecture:

```
NOD-GENESIS-MANIFEST.json
```

Contents:

- protocol name / full name / identity / version
- `genesis_object`: `NØD-EPfTSmFVMmAnkJqZnz6T4h`
- `genesis_author`: Jad Jbara — Genesis Originator, **not** permanent authority
- content identity: SHA-256 per foundational document
- `successor_rule`: *No individual or repository is required for protocol existence.*

The Manifest itself is content-addressed and versioned; a future revision
must append, never overwrite the genesis identity.

---

## 5. Independent Mirrors

Target topology — GitHub becomes a *mirror*, not the *home*:

```
GitHub (primary today)
   │
   ├── Mirror A (independent hosting)
   ├── Mirror B (independent hosting)
   ├── Archive (Software Heritage, GitHub Archive Program)
   ├── Personal offline copy (git bundle + raw files)
   └── Independent community forks
```

Goal is not trust in any single location; the goal is that **no single
deletion can end the project**.

### 5.1 Concrete mirror plan (Phase C)

| Mirror | Method | Prepared |
|---|---|---|
| Software Heritage | `swh` deposit of the repository | not yet |
| GitHub Archive | automatic (public repos are archived) | automatic |
| Offline bundle | `git bundle` + `tar` of repository | to create |
| Secondary host | second public git host / IPFS pinning | to create |
| Community forks | README + LICENSE permit forks; invite independent forks | to create |

---

## 6. Self-Hosting: the NØD Node

The deepest survival step: the reference implementation becomes a **NØD
Node** that anyone can run:

```
GitHub Repository
        ↓
Reference Implementation
        ↓
NØD Node (nod-node)
        ↓
NØD Network
        ↓
Independent Nodes
```

At that point:

```
You disappear
GitHub disappears
Website disappears
        ↓
NØD nodes continue
```

### 6.1 Minimum viable node (v0)

A `nod-node` is an executable that:

1. Loads the Genesis Manifest and verifies its content hashes.
2. Loads a local registry of NØD objects (append-only state).
3. Produces and verifies provenance chains.
4. Serves read/query of the discovery graph.
5. Can synchronize with other nodes (later phase).

This is implemented as `node/nod_node.py` in this repository (see §11).

---

## 7. Founder vs Authority

```               Jad Jbara
                    │
                    │ Genesis Attribution
                    ▼
                 NØD Genesis
                    │
                    └──── No Permanent Administrative Control
```

Formal principle:

- Jad Jbara remains **Genesis Originator** — attribution always recorded.
- NØD does **not** require the founder's signature, permission, or
  existence to continue operating, evolving, or being verified.
- The protocol may fork; governance is forkable.

The relationship is additive to Law 16: attribution persists, authority
does not.

---

## 8. New Law — Law 16: Protocol Survival

Added to `docs/PROTOCOL-LAWS.md`:

> **The existence, operation, validity, and historical continuity of the
> NØD Protocol SHALL NOT depend on the continued existence, availability,
> identity, permission, or operation of any single individual, repository,
> company, domain, server, or implementation.**

Mechanism: independent implementations; replicated specifications;
cryptographic content identity; independent node operation; forkable
governance; distributed archival persistence.

Failure modes prevented: founder disappearance, repository deletion,
company shutdown, domain expiration, infrastructure censorship, single-point
institutional failure.

---

## 9. On "Forever"

No system can scientifically guarantee data persists forever. Even IPFS
requires storage retention; the network does not promise permanent
availability by itself. Continuous persistence needs:

- machines that run;
- people who hold copies;
- economic or social incentives;
- software updates.

**The correct objective is therefore not:**

> *Guaranteed Forever*

**but:**

> *No Single Party Can End It*

That is the strictly weaker, but actually achievable, standard —
and it is the standard NØD-002 adopts.

---

## 10. The NØD Survival Model

```
Phase A (NOW)   — Canonical Specification + Genesis Manifest + Content Hashes
                      + Public Source + Open License        ← implemented
Phase B (NOW+)  — Independent Mirrors (archive, bundle, second host)
Phase C         — Reference Implementation → NØD Node        ← implemented (v0)
Phase D         — NØD Discovery Ledger (distributed, not necessarily blockchain)
Phase E         — Founder disappears ⇒ repository disappears ⇒ website
                      disappears ⇒ NØD survives
```

---

## 11. Implemented in this revision

| Artifact | Path | Status |
|---|---|---|
| Genesis Manifest | `NOD-GENESIS-MANIFEST.json` | ✅ created |
| Law 16 | `docs/PROTOCOL-LAWS.md` | ✅ added |
| NØD Node v0 | `node/nod_node.py` | ✅ created |
| Survival model doc | `docs/NOD-002-PROTOCOL-SURVIVAL.md` | ✅ this document |
| Roadmap update | `docs/ROADMAP.md` | ✅ updated |

---

## 12. Open items (Phase B)

1. Deposit the repository into **Software Heritage**.
2. Create an offline `git bundle` + raw archive under `archives/`.
3. Pin a release to a second public host / IPFS.
4. Implement node-to-node synchronization (Phase D).
5. Define fork-governance rules for spec revisions (NDP mechanism).

---

*NØD-002 Protocol Survival and Persistence Architecture — v1.0 · August 2026*
*The discovery survives the discoverer. The lineage survives the origin.
The network survives the node.*
