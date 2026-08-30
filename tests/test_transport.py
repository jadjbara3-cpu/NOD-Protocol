"""Real transport tests — NØD-Sync over actual TCP sockets.

These run on loopback sockets (no internet): they prove the wire protocol
works, peers verify state roots independently, and nodes converge over a
real network interface.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.sync.transport import PeerServer, PeerClient, bootstrap_nodes
from nod_protocol.sync.state import StateEvent


def ev(kind, nod, prop, v, s, payload=None, order=0):
    return StateEvent(kind=kind, nod_id=nod, proposer=prop, payload=payload or {},
                      verification_strength=v, independent_support=s, order=order)


class TestWireProtocol:
    def test_hello_handshake_and_ping(self):
        srv = PeerServer("server-1", port=0)
        port = srv.start()
        try:
            client = PeerClient("client-1", port=port)
            hs = client.connect()
            assert hs["op"] == "hello_ack"
            assert hs["server"] == "server-1"
            pong = client.ping()
            assert pong["op"] == "pong"
            client.close()
        finally:
            srv.stop()

    def test_state_query_returns_verifiable_root(self):
        srv = PeerServer("server-1", port=0, genesis_hash="gen-x")
        port = srv.start()
        try:
            client = PeerClient("q", port=port)
            client.connect()
            msg = client.query_state()
            assert "state_root" in msg
            assert client.verify_downloaded_state(msg) is True
            client.close()
        finally:
            srv.stop()

    def test_event_submission_accepted_and_applied(self):
        srv = PeerServer("server-1", port=0, genesis_hash="gen-x")
        port = srv.start()
        try:
            client = PeerClient("p", port=port)
            client.connect()
            r = client.submit_event(ev("discovery", "NOD-1", "p", 0.9, 0.9, order=1))
            assert r["accepted"] is True
            state, root = srv.query_state()
            assert len(state.accepted) == 1
            client.close()
        finally:
            srv.stop()

    def test_invalid_event_rejected_over_wire(self):
        srv = PeerServer("server-1", port=0, genesis_hash="gen-x")
        port = srv.start()
        try:
            client = PeerClient("p", port=port)
            client.connect()
            r = client.submit_event(ev("discovery", "NOD-1", "p", 0.1, 0.1, order=1))
            assert r["accepted"] is False
            state, _ = srv.query_state()
            assert len(state.accepted) == 0
            client.close()
        finally:
            srv.stop()

    def test_two_peers_converge_over_loopback(self):
        """Two real nodes on real sockets converge on the same event set."""
        a = PeerServer("A", port=0, genesis_hash="gen-x")
        b = PeerServer("B", port=0, genesis_hash="gen-x")
        a.start()
        b.start()
        try:
            # A submits locally (as a producer) -> accepted in A
            a.submit_event(ev("discovery", "NOD-1", "a", 0.9, 0.9, order=1))
            # B receives the SAME event over the wire
            cba = PeerClient("b", port=b.port)
            cba.connect()
            reply = cba.submit_event(ev("discovery", "NOD-1", "a", 0.9, 0.9, order=1))
            assert reply["accepted"] is True
            time.sleep(0.2)
            state_a, root_a = a.query_state()
            state_b, root_b = b.query_state()
            assert len(state_a.accepted) == 1 and len(state_b.accepted) == 1
            assert root_a == root_b, f"roots differ: {root_a} vs {root_b}"
            cba.close()
        finally:
            a.stop()
            b.stop()

    def test_bootstrap_three_nodes(self):
        net = bootstrap_nodes(["JP", "JO", "BR"], genesis_hash="gen-z")
        try:
            assert len(net) == 3
            for s in net:
                assert s.verify_state() is True
        finally:
            for s in net:
                s.stop()

    def test_any_agent_can_join_real_network(self):
        srv = PeerServer("hub", port=0, genesis_hash="gen-y")
        port = srv.start()
        try:
            for agent in ("GPT", "Gemini", "DeepSeek"):
                c = PeerClient(agent, port=port)
                c.connect()
                assert c.ping()["op"] == "pong"
                c.close()
        finally:
            srv.stop()
