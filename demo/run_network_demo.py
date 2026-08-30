"""Real network demo — three NØD nodes on real TCP loopback sockets.

Demonstrates the open protocol end-to-end:

    Node JP (server) ── Node JO (server) ── Node BR (server)
                  └──── all accept a broadcast event

Then any compatible agent (GPT / Gemini / DeepSeek) connects, queries the
shared state, verifies the state root, and submits an event.

Run:  PYTHONPATH=src python demo/run_network_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.sync.transport import PeerServer, PeerClient, bootstrap_nodes
from nod_protocol.sync.state import StateEvent

GENESIS = "GENESIS-ARENA-001"


def ev(kind, nod, prop, v, s, payload=None, order=0):
    return StateEvent(kind=kind, nod_id=nod, proposer=prop, payload=payload or {},
                      verification_strength=v, independent_support=s, order=order)


def main() -> None:
    print("=" * 64)
    print("NØD-SYNC — REAL NETWORK DEMO (TCP/NDJSON)")
    print("=" * 64)

    nodes = bootstrap_nodes(["JP", "JO", "BR"], genesis_hash=GENESIS)
    print(f"[1] three nodes on real sockets: {[n.port for n in nodes]}")

    # Agent A (Japan) discovers and submits locally
    print("\n[2] Agent JP discovers a solution (local submit)...")
    di = ev("discovery", "NOD-DISCOVERY-1", "JP-agent", 0.92, 0.88,
            payload={"claim": "cache-aware relaxed latency bounds", "utility": 0.72}, order=1)
    nodes[0].submit_event(di)
    time.sleep(0.1)

    # replicate the same accepted event to the other two nodes via wire
    for i in (1, 2):
        c = PeerClient("replicator", port=nodes[i].port)
        c.connect()
        ack = c.submit_event(di)
        c.close()
        time.sleep(0.1)

    print("\n[3] state roots across nodes:")
    roots = []
    for n in nodes:
        _, root = n.query_state()
        roots.append(root)
        print(f"    {n.node_id}: {root[:24]}...")
    print("    converge:", len(set(roots)) == 1)

    # Any compatible agent queries + verifies + submits
    print("\n[4] open protocol — any model can join:")
    for agent in ("GPT", "Gemini", "Claude", "Qwen", "DeepSeek"):
        client = PeerClient(agent, port=nodes[0].port)
        client.connect()
        q = client.query_state()
        ver = client.verify_downloaded_state(q)
        print(f"    {agent}: state_root={q['state_root'][:16]}... verifiable={ver}")
        client.close()
        time.sleep(0.05)

    print("\n[5] a new agent challenges the discovery (submits contradiction):")
    c = PeerClient("skeptic-1", port=nodes[2].port)
    c.connect()
    c.submit_event(ev("contradiction", "NOD-DISCOVERY-1", "skeptic-1", 0.8, 0.75,
                      payload={"challenged": True}, order=2))
    c.close()
    time.sleep(0.1)

    print("\n[6] final shared states:")
    for n in nodes:
        st, _ = n.query_state()
        print(f"    {n.node_id}: {len(st.accepted)} events, root={st.state_root()[:16]}...")

    for n in nodes:
        n.stop()
    print("\n" + "=" * 64)
    print("DEMO COMPLETE — real sockets, shared state, any model welcome.")
    print("=" * 64)


if __name__ == "__main__":
    main()
