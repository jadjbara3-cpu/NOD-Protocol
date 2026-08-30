"""NØD-Sync tests — distributed cognitive synchronization.

Locks the properties of the shared global cognitive state:

  * Latest Valid State (protocol-recognized, NOT latest clock)
  * fork preservation: Chain A AND Chain B (not OR)
  * eventual convergence of independent nodes
  * open protocol: any model can query, verify, and continue
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.sync.state import StateEvent, GlobalState
from nod_protocol.sync.network import SimNetwork, Node
from nod_protocol.sync.resolution import resolve_fork, latest_valid_pointer, confidence


def ev(kind, nod, prop, v, s, payload=None, order=0):
    return StateEvent(kind=kind, nod_id=nod, proposer=prop,
                      payload=payload or {"desc": nod + "-" + kind},
                      verification_strength=v, independent_support=s, order=order)


class TestGlobalState:
    def test_state_root_content_addressed(self):
        g = GlobalState(genesis_hash="G1")
        e1 = ev("discovery", "N1", "a", 0.9, 0.8)
        g.apply(e1)
        r1 = g.state_root()
        g2 = GlobalState(genesis_hash="G1")
        g2.apply(ev("discovery", "N1", "a", 0.9, 0.8))
        assert g2.state_root() == r1  # same content → same root

    def test_state_root_changes_with_order(self):
        g = GlobalState(genesis_hash="G1")
        g.apply(ev("discovery", "N1", "a", 0.9, 0.8, order=1))
        r1 = g.state_root()
        g2 = GlobalState(genesis_hash="G1")
        g2.apply(ev("discovery", "N1", "a", 0.9, 0.8, order=2))
        assert g2.state_root() != r1  # different event → different root

    def test_verify_root(self):
        g = GlobalState(genesis_hash="G1")
        g.apply(ev("discovery", "N1", "a", 0.9, 0.8))
        assert g.verify_root(g.state_root()) is True
        assert g.verify_root("0xdead") is False

    def test_invalid_proposal_rejected(self):
        g = GlobalState(genesis_hash="G1")
        weak = ev("discovery", "N1", "a", 0.2, 0.1)  # below thresholds
        assert weak.is_valid_proposal() is False
        assert g.apply(weak) is False
        assert len(g.accepted) == 0


class TestForkPreservation:
    def test_competing_states_coexist(self):
        """Chain A AND Chain B — a fork is NOT a failure."""
        m10 = ev("mutation", "NOD-1", "jp", 0.9, 0.9, {"utility": 0.4}, order=10)
        m11 = ev("mutation", "NOD-1", "jo", 0.95, 0.85, {"utility": 0.7}, order=11)
        res = resolve_fork([m10, m11])
        assert len(res.coexisting) == 2          # both preserved
        assert res.pointer == "NOD-1"            # pointer chosen by confidence
        assert res.note.startswith("fork preserved")

    def test_pointer_is_confidence_not_clock(self):
        """The LATER timestamp with weaker verification must NOT win."""
        old_strong = ev("mutation", "N1", "a", 0.98, 0.95, {"utility": 0.9}, order=100)
        new_weak = ev("mutation", "N2", "b", 0.51, 0.51, {"utility": 0.2}, order=999)
        assert confidence(new_weak) < confidence(old_strong)
        res = resolve_fork([new_weak, old_strong])
        assert res.pointer == old_strong.nod_id  # protocol-recognized, not newest

    def test_invalid_candidates_not_accepted(self):
        res = resolve_fork([ev("mutation", "N1", "a", 0.1, 0.1)])
        assert res.accepted == []
        assert res.note == "no valid candidate; state unchanged"


class TestNetwork:
    def test_eventual_convergence(self):
        net = SimNetwork(genesis_hash="gen-A")
        for nid in ("JP", "JO", "BR"):
            net.add_node(Node(nid))
        net.broadcast(ev("discovery", "D1", "jp", 0.85, 0.8, order=1))
        net.broadcast(ev("branch", "D2", "jo", 0.9, 0.9, order=2))
        ok, ticks = net.run_until_converged()
        assert ok is True
        assert ticks <= 100
        assert all(len(n.state.accepted) == 2 for n in net.nodes)

    def test_temporary_differences_allowed(self):
        """Before convergence, nodes may differ — that is the design."""
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("X"))
        net.add_node(Node("Y"))
        net.broadcast(ev("discovery", "D1", "x", 0.9, 0.9, order=1))
        # process only X
        net.nodes[0].process_messages()
        assert set(net.nodes[0].state.accepted) != set(net.nodes[1].state.accepted)
        net.tick()  # Y catches up
        assert net.converged()

    def test_state_root_same_across_nodes(self):
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("1"))
        net.add_node(Node("2"))
        net.broadcast(ev("discovery", "D1", "a", 0.9, 0.9, order=1))
        net.run_until_converged()
        assert net.nodes[0].state_root() == net.nodes[1].state_root()


class TestOpenProtocol:
    def test_any_agent_can_query(self):
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("n1"))
        net.broadcast(ev("discovery", "D1", "t", 0.9, 0.9, order=1))
        net.run_until_converged()
        q = net.open_query("Claude-from-Paris")
        assert q["attendant"] == "Claude-from-Paris"
        assert q["protocol_version"] == "1.0"
        assert q["verifiable"] is True
        assert "current_state_root" in q

    def test_any_agent_can_join_and_verify(self):
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("n1"))
        net.broadcast(ev("discovery", "D1", "t", 0.9, 0.9, order=1))
        net.run_until_converged()
        new_node = net.open_join("Qwen-from-Shenzhen")
        net.run_until_converged()
        assert new_node.converged_with(net.nodes[0])
        assert new_node.verify_state() is True

    def test_fresh_node_verifies_from_scratch(self):
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("n1"))
        net.broadcast(ev("discovery", "D1", "t", 0.9, 0.9, order=1))
        net.run_until_converged()
        assert net.verify_from_scratch() is True

    def test_latest_valid_pointer(self):
        net = SimNetwork(genesis_hash="gen-A")
        net.add_node(Node("n1"))
        net.broadcast(ev("mutation", "M1", "a", 0.95, 0.9, {"utility": 0.8}, order=1))
        net.run_until_converged()
        assert latest_valid_pointer(net.nodes[0].state) == "M1"
