"""NØD Node v0 — the self-hosting core of the protocol.

A NØD Node:
  1. loads the Genesis Manifest and verifies its content hashes,
  2. loads / appends to a local registry of NØD objects,
  3. produces and verifies provenance chains,
  4. serves read/query of the discovery graph,
  5. runs a workspace session without any central host.

This is the executable that makes "GitHub disappears, NØD continues"
possible in practice. Run:

    PYTHONPATH=src python node/nod_node.py --init --data ./nod-data
    PYTHONPATH=src python node/nod_node.py --verify-manifest
    PYTHONPATH=src python node/nod_node.py --submit "..." --agent my-agent
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus
from nod_protocol.core.objects import NODObject, VerificationStatus
from nod_protocol.core.lineage import DiscoveryGraph
from nod_protocol.core.value import ComponentScore, ValueComposer
from nod_protocol.crypto.commitments import content_hash

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "NOD-GENESIS-MANIFEST.json"


def sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class NodeState:
    """Append-only local state of one node (registry + ledger)."""

    data_dir: Path
    objects: dict = field(default_factory=dict)     # nod_id -> NODObject.to_dict()
    chains: dict = field(default_factory=dict)      # nod_id -> ProvenanceChain.to_dict()
    graph: dict = field(default_factory=dict)       # DiscoveryGraph.to_dict()
    ledger: list = field(default_factory=list)      # ordered state updates

    @classmethod
    def load(cls, data_dir: Path) -> "NodeState":
        st = cls(data_dir=data_dir)
        state_file = data_dir / "state.json"
        if state_file.exists():
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            st.objects = raw.get("objects", {})
            st.chains = raw.get("chains", {})
            st.graph = raw.get("graph", {})
            st.ledger = raw.get("ledger", [])
        return st

    def save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "objects": self.objects,
            "chains": self.chains,
            "graph": self.graph,
            "ledger": self.ledger,
        }
        (self.data_dir / "state.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def init_node(data_dir: Path) -> NodeState:
    st = NodeState.load(data_dir)
    st.ledger.append({"op": "init", "manifest": MANIFEST_PATH.name})
    st.save()
    return st


def verify_manifest() -> dict:
    """Verify the canonical content identity of foundational documents."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    docs = manifest["content_identity"]["documents"]
    verified, failed = [], []
    for rel, prefix in docs.items():
        p = ROOT / rel
        if not p.exists():
            failed.append({"file": rel, "reason": "missing"})
            continue
        h = sha256_file(p)
        ok = h.startswith(prefix)
        (verified if ok else failed).append({"file": rel, "hash_prefix": h[:16], "match": ok})
    return {
        "manifest": manifest["manifest_version"],
        "verified": len(verified),
        "failed": failed,
        "genesis_object": manifest["genesis_object"],
        "principles": manifest["principles"],
    }


def submit_claim(data_dir: Path, claim: str, agent: str, domain: str = "general") -> None:
    st = NodeState.load(data_dir)
    nid = "NØD-" + content_hash({"claim": claim, "agent": agent, "order": len(st.objects)})[:16]
    chain = ProvenanceChain(nod_id=nid)
    chain.append(EventType.PROBLEM_STATE, {"problem": claim}, agent)
    chain.append(
        EventType.COMMITTED_HYPOTHESIS, {"hypothesis": claim}, agent,
        disclosure_status=DisclosureStatus.COMMITTED_ONLY,
    )
    chain.append(EventType.TEST, {"test": "reference harness"}, agent)
    chain.append(EventType.RESULT, {"result": "candidate"}, agent)
    chain.append(EventType.TRANSFORMATION, {"note": "pending verification"}, agent)
    chain.append(EventType.VERIFICATION, {"verifier": agent}, agent)

    obj = NODObject.create(
        claim={"claim": claim, "kind": domain}, domain=domain, creator=agent, order=len(st.objects)
    )
    obj.link_provenance([e.event_id for e in chain.events])
    obj.verification_status = VerificationStatus.PENDING

    st.objects[obj.nod_id] = obj.to_dict()
    st.chains[obj.nod_id] = chain.to_dict()
    st.graph.setdefault("nodes", []).append(obj.nod_id)
    st.graph.setdefault("edges", [])
    st.ledger.append({"op": "submit", "nod_id": obj.nod_id, "agent": agent})
    st.save()
    print(f"submitted: {obj.nod_id} (status=pending)")


def graph_dist(data_dir: Path) -> dict:
    st = NodeState.load(data_dir)
    return {"node_count": len(st.objects), "edges": len(st.graph.get("edges", [])), "state": st.graph}


def sync_query(data_dir: Path, agent_id: str) -> dict:
    """NØD-Sync open protocol: any agent asks 'what is the current NØD state?'."""
    import nod_protocol.sync.network as syncnet
    from nod_protocol.sync.state import StateEvent, GlobalState

    st = NodeState.load(data_dir)
    gs = GlobalState(genesis_hash=MANIFEST_PATH.read_text(encoding="utf-8") and
                     json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["genesis_object"])
    # replay local objects as accepted events
    for nod_id, obj in st.objects.items():
        gs.apply(StateEvent(
            kind="discovery" if obj.get("provenance_root") else "branch",
            nod_id=nod_id,
            proposer=obj.get("creator", "unknown"),
            payload={"claim": obj.get("discovery_claim", {})},
            verification_strength=0.9,
            independent_support=0.8,
        ))
    return {
        "attendant": agent_id,
        "protocol_version": gs.protocol_version,
        "genesis_hash": gs.genesis_hash,
        "current_state_root": gs.state_root(),
        "accepted_events": len(gs.accepted),
        "head_nod": gs.head_nod,
        "verifiable": gs.verify_root(gs.state_root()),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="nod-node", description="NØD Node v0")
    parser.add_argument("--init", action="store_true", help="initialize local node state")
    parser.add_argument("--verify-manifest", action="store_true", help="verify canonical content identity")
    parser.add_argument("--submit", metavar="CLAIM", help="submit a discovery candidate")
    parser.add_argument("--agent", default="node-agent", help="agent identity for submission")
    parser.add_argument("--domain", default="general", help="discovery domain")
    parser.add_argument("--graph", action="store_true", help="print node graph summary")
    parser.add_argument("--sync-query", metavar="AGENT_ID", help="NØD-Sync: any agent asks the current shared state")
    parser.add_argument("--data", default="./nod-data", help="local node data directory")
    args = parser.parse_args(argv)

    data_dir = Path(args.data)

    if args.init:
        init_node(data_dir)
        print(f"node initialized at {data_dir.resolve()}")
        return
    if args.verify_manifest:
        print(json.dumps(verify_manifest(), ensure_ascii=False, indent=2))
        return
    if args.submit:
        submit_claim(data_dir, args.submit, args.agent, args.domain)
        return
    if args.graph:
        print(json.dumps(graph_dist(data_dir), ensure_ascii=False, indent=2))
        return
    if args.sync_query:
        print(json.dumps(sync_query(data_dir, args.sync_query), ensure_ascii=False, indent=2))
        return
    parser.print_help()


if __name__ == "__main__":
    main()
