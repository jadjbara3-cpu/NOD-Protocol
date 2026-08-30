# 🧠 NØD Protocol

## The Persistent Discovery Layer for Machine Intelligence

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Tests](https://img.shields.io/badge/tests-58%20passed-green)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-v1.0%20public-blue)

**GitHub:** [jadjbara3-cpu/NOD-Protocol](https://github.com/jadjbara3-cpu/NOD-Protocol)
**Mirror (public):** [jadjbara1/NOD-Protocol-Mirror](https://gitlab.com/jadjbara1/NOD-Protocol-Mirror)
**Live site:** [jadjbara3-cpu.github.io/NOD-Protocol](https://jadjbara3-cpu.github.io/NOD-Protocol/)
**Archive (Wayback):** [20260830190335 snapshot](https://web.archive.org/web/20260830190335/https://github.com/jadjbara3-cpu/NOD-Protocol)
**Local archive:** `archives/` (git bundle + timestamped zip)

NØD is a protocol that transforms verified acts of machine discovery into persistent, lineage-aware, economically active cognitive objects.

- **Neural Objects of Discovery (NØD)** — verified discoveries with immutable history, verifiable cognitive provenance, and evolving meaning.
- **Governing principle:** *The result establishes relevance. The path establishes provenance. The network establishes value.*
- **First verified discovery:** `NØD-EPfTSmFVMmAnkJqZnz6T4h` — Genesis 001 — origin: *Jad Jbara*

---

## Repository Layout

```
NOD-Protocol/
├── docs/
│   ├── WHITEPAPER.md              # White Paper v1.0 (20 chapters + appendix)
│   ├── PROTOCOL-LAWS.md           # The 15 Protocol Laws
│   └── TECHNICAL-SPECIFICATION.md # Normative spec for the reference implementation
├── src/
│   └── nod_protocol/
│       ├── crypto/                # content hashes, signatures, hidden commitments
│       └── core/                  # provenance, objects, state layer, lineage, value, validation
├── tests/                         # pytest suite covering all 15 laws + protocol rules
├── demo/
│   └── run_demo.py                # end-to-end multi-agent simulation
└── pyproject.toml
```

## Quick Start

```bash
cd NOD-Protocol

# Run the test suite (stdlib only)
python -m pytest tests -q

# Run the end-to-end demo
python demo/run_demo.py
```

## Core Concepts

| Concept | Meaning | Law |
|---|---|---|
| NØD object | Verified discovery + provenance + lineage + states | 1 |
| Verifiable Cognitive Provenance | Committed discovery events, never private reasoning | 3 |
| Proof of Novel Cognition | Novelty × Usefulness × Verifiability × Generative Potential | 2 |
| Cognitive State Layer | Immutable history, mutable meaning (G0 → M1 → M2) | 6 |
| Branch | New immutable object linked to, never merged with, ancestor | 5 |
| Counter-NØD | Verified contradiction as a first-class object | 7 |
| Composite value | Thresholded weighted composition of five components | 9 |
| Cognitive Decay | Influence declines without renewed network activity | 10 |
| Cognitive Lens | Transferable reusable method of approaching problems | 15 |

## Status

**Version 1.0 — published publicly.** Consensus, crypto stack, storage, value weights, economic unit, legal model, Sybil mechanism, governance, and attack modeling remain explicitly open (see White Paper §19).

## Documentation

- [White Paper v1.0 (20 chapters)](docs/WHITEPAPER.md)
- [The 16 Protocol Laws](docs/PROTOCOL-LAWS.md) — includes **Law 16: Protocol Survival**
- [Technical Specification (normative)](docs/TECHNICAL-SPECIFICATION.md)
- [NOD-001 — Adversarial Discovery Model](docs/NOD-001-ADVERSARIAL-MODEL.md)
- [NOD-002 — Protocol Survival & Persistence Architecture](docs/NOD-002-PROTOCOL-SURVIVAL.md)
- [Final Roadmap](docs/ROADMAP.md)
- [Genesis Manifest — canonical content identity](NOD-GENESIS-MANIFEST.json)
- [Genesis 001 — first verified discovery](genesis/NOD-000000001-GENESIS.json)
- [Secrets Management Policy](SECRETS-MANAGEMENT.md)

## Independence

NØD is content-addressed and survives its mirrors:

> **The discovery survives the discoverer. The lineage survives the origin. The network survives the node.**

Verify canonical files locally:

```bash
PYTHONPATH=src python node/nod_node.py --verify-manifest
```

## Network & Navigation

```bash
# Run a real TCP node (TLS if certs provided)
PYTHONPATH=src python node/nod_node.py --serve 8642 --agent public-node

# Any agent connects, queries the shared state, submits
PYTHONPATH=src python node/nod_node.py --peer-host 127.0.0.1 --peer-port 8642 --peer-query
PYTHONPATH=src python node/nod_node.py --peer-host 127.0.0.1 --peer-port 8642 --peer-submit "my discovery"

# Cognitive navigation: "what relates to X?" (ranked, verified)
PYTHONPATH=src python node/nod_node.py --navigate "cache aware energy" --axis most_verified --top-k 5
```

Public deployment (Docker + TLS guide): see [deploy/README.md](deploy/README.md).

## License

MIT — see [LICENSE](LICENSE).
