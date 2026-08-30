"""NØD-Sync — distributed network simulation.

Models a set of independent NØD nodes that:

    * receive candidate events (broadcast),
    * verify them (protocol rules),
    * accept into local state,
    * eventually converge to the same accepted event set.

The convergence guarantee is *eventually consistent*, not instantaneous:
temporary differences are allowed; the network converges to a single
recognized state after protocol verification.

Also models the OPEN protocol surface: any compatible agent (any model,
any geography) can connect, verify genesis, download state, verify hashes,
and continue.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nod_protocol.sync.state import StateEvent, GlobalState
from nod_protocol.sync.resolution import resolve_fork, latest_valid_pointer


@dataclass
class Node:
    """One independent NØD node."""

    node_id: str
    state: GlobalState = field(default_factory=GlobalState)
    inbox: list[StateEvent] = field(default_factory=list)

    def receive(self, event: StateEvent) -> None:
        """Broadcast delivery into the node's inbox (offline-tolerant)."""
        self.inbox.append(event)

    def process_messages(self) -> int:
        """Verify and accept pending messages; returns count accepted.

        Protocol rule: an event is accepted only when it carries sufficient
        verification and independence (Law 8, Law 13) — NOT merely because it
        arrived last.
        """
        accepted = 0
        while self.inbox:
            event = self.inbox.pop(0)
            if self.state.apply(event):
                accepted += 1
        return accepted

    def converged_with(self, other: "Node") -> bool:
        return set(self.state.accepted) == set(other.state.accepted)

    def state_root(self) -> str:
        return self.state.state_root()

    def verify_state(self) -> bool:
        """Any node can verify its own state root independent of hosts."""
        return self.state.verify_root(self.state.state_root())


@dataclass
class SimNetwork:
    """A deterministic simulation of N nodes exchanging events."""

    nodes: list[Node] = field(default_factory=list)
    genesis_hash: str = ""

    def add_node(self, node: Node) -> None:
        node.state.genesis_hash = self.genesis_hash
        self.nodes.append(node)

    def broadcast(self, event: StateEvent) -> None:
        for node in self.nodes:
            node.receive(event)

    def tick(self) -> int:
        """Each node processes its inbox; returns total accepted."""
        total = 0
        for node in self.nodes:
            total += node.process_messages()
        return total

    def run_until_converged(self, max_ticks: int = 100) -> tuple[bool, int]:
        for i in range(max_ticks):
            self.tick()
            if self.converged():
                return True, i + 1
        return self.converged(), max_ticks

    def converged(self) -> bool:
        if not self.nodes:
            return True
        first = set(self.nodes[0].state.accepted)
        return all(set(n.state.accepted) == first for n in self.nodes)

    def final_pointer(self) -> str:
        return latest_valid_pointer(self.nodes[0].state) if self.nodes else ""

    # -- open protocol surface ------------------------------------------------

    def open_query(self, agent_id: str) -> dict:
        """Any model, anywhere, can ask: 'What is the current NØD state?'

        Returns an open, host-independent snapshot: protocol version,
        genesis hash, current state root, accepted event count, head,
        and the protocol-recognized pointer.
        """
        st = self.nodes[0].state if self.nodes else GlobalState()
        return {
            "attendant": agent_id,
            "protocol_version": st.protocol_version,
            "genesis_hash": st.genesis_hash,
            "current_state_root": st.state_root(),
            "accepted_events": len(st.accepted),
            "head_nod": st.head_nod,
            "latest_valid_pointer": latest_valid_pointer(st),
            "verifiable": st.verify_root(st.state_root()),
        }

    def open_join(self, agent_id: str) -> Node:
        """Any compatible agent can connect and become a node.

        On join, the new node is seeded with the current shared state so it
        can verify and continue from the same convergence point (open
        protocol: download state, verify hashes, continue).
        """
        node = Node(node_id=agent_id)
        if self.nodes:
            # seed from the reference node's accepted state
            node.state = GlobalState.from_dict(self.nodes[0].state.to_dict())
        self.add_node(node)
        return node

    def verify_from_scratch(self) -> bool:
        """A new node can download the state and verify it independently."""
        # simulate a fresh node that only trusts the genesis hash
        st = self.nodes[0].state
        rebuilt = GlobalState(genesis_hash=st.genesis_hash)
        for e in st.events.values():
            rebuilt.apply(e)
        return rebuilt.verify_root(st.state_root())
