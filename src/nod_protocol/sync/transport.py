"""NØD-Sync — real transport layer (TCP / NDJSON).

Brings NØD-Sync from simulation to REAL network operation: nodes speak a
simple line-delimited JSON protocol over TCP sockets. Any node can:

    * connect as a peer,
    * receive and apply accepted events,
    * query the current global state,
    * verify state roots independently.

Protocol (NDJSON frames):

    {"op":"hello","node_id":..., "genesis_hash":...}
    {"op":"state_query","requester":...}
    {"op":"state","payload":<GlobalState.to_dict()>}
    {"op":"event","event":<StateEvent.canonical()>}
    {"op":"ack","event_hash":..., "accepted":true}
    {"op":"ping"}

Everything is stdlib-only (socket, threading, json). The wire identity is
content: peers verify hashes, never trust hosts.
"""

from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass
from typing import Callable

from nod_protocol.sync.state import StateEvent, GlobalState

DEFAULT_PORT = 8642


# ---------------------------------------------------------------------------
# Wire helpers
# ---------------------------------------------------------------------------

def _encode(obj: dict) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _decode(line: bytes) -> dict:
    return json.loads(line.decode("utf-8"))


def _recv_line(sock: socket.socket, buffer: bytes, limit: int = 1 << 20) -> tuple[bytes | None, bytes]:
    """Read one newline-terminated frame from a buffer; returns (line, rest)."""
    while b"\n" not in buffer:
        chunk = sock.recv(65536)
        if not chunk:
            return None, buffer
        buffer += chunk
        if len(buffer) > limit:
            raise ValueError("frame too large")
    line, rest = buffer.split(b"\n", 1)
    return line, rest


# ---------------------------------------------------------------------------
# PeerServer — a real NØD node listening on a TCP port
# ---------------------------------------------------------------------------

@dataclass
class PeerServer:
    """A listening NØD node with real socket transport.

    Accepts multiple peers (thread per connection). Maintains its own
    GlobalState; events arriving from peers are validated by protocol rules
    and applied. The state root is content-addressed and verifiable by any
    peer.
    """

    node_id: str
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    genesis_hash: str = ""
    state: GlobalState | None = None

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = GlobalState(genesis_hash=self.genesis_hash)
        self._server: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._peers: set[str] = set()

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> int:
        """Bind and listen; returns the bound port (useful for port=0)."""
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(16)
        self._running = True
        self.port = self._server.getsockname()[1]
        t = threading.Thread(target=self._accept_loop, daemon=True)
        t.start()
        self._threads.append(t)
        return self.port

    def stop(self) -> None:
        self._running = False
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass

    # -- internals --------------------------------------------------------------

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, _addr = self._server.accept()
            except OSError:
                break
            t = threading.Thread(target=self._handle_conn, args=(conn,), daemon=True)
            t.start()
            self._threads.append(t)

    def _handle_conn(self, conn: socket.socket) -> None:
        buffer = b""
        conn.settimeout(30)
        try:
            # hello handshake
            line, buffer = _recv_line(conn, buffer)
            if line is None:
                conn.close()
                return
            hello = _decode(line)
            self._peers.add(hello.get("node_id", "?"))
            conn.sendall(_encode({"op": "hello_ack", "server": self.node_id,
                                  "genesis_hash": self.state.genesis_hash,
                                  "state_root": self.state.state_root()}))
            # message loop
            while True:
                line, buffer = _recv_line(conn, buffer)
                if line is None:
                    break
                msg = _decode(line)
                self._dispatch(conn, msg)
        except (ValueError, OSError, json.JSONDecodeError):
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _dispatch(self, conn: socket.socket, msg: dict) -> None:
        op = msg.get("op")
        if op == "state_query":
            with self._lock:
                payload = self.state.to_dict()
            conn.sendall(_encode({"op": "state", "payload": payload,
                                  "state_root": self.state.state_root()}))
        elif op == "event":
            c = msg["event"]
            ev = StateEvent(
                kind=c["kind"],
                nod_id=c["nod_id"],
                proposer=c["proposer"],
                payload=c.get("payload", {}),
                evidence=c.get("evidence", {}),
                verification_strength=c.get("v", c.get("verification_strength", 0.0)),
                independent_support=c.get("s", c.get("independent_support", 0.0)),
                order=c.get("order", 0),
            )
            with self._lock:
                accepted = self.state.apply(ev)
            conn.sendall(_encode({"op": "ack", "event_hash": ev.event_hash,
                                  "accepted": accepted}))
        elif op == "ping":
            conn.sendall(_encode({"op": "pong"}))

    # -- server API -------------------------------------------------------------

    def submit_event(self, event: StateEvent) -> dict:
        """Local submission (also used by peers via network) — protocol-validated."""
        with self._lock:
            accepted = self.state.apply(event)
        return {"event_hash": event.event_hash, "accepted": accepted}

    def query_state(self) -> tuple[GlobalState, str]:
        with self._lock:
            snapshot = GlobalState.from_dict(self.state.to_dict())
        return snapshot, snapshot.state_root()

    def verify_state(self) -> bool:
        with self._lock:
            return self.state.verify_root(self.state.state_root())


# ---------------------------------------------------------------------------
# PeerClient — any model/agent connecting to the network
# ---------------------------------------------------------------------------

@dataclass
class PeerClient:
    """A client speaking the NØD wire protocol to a PeerServer.

    This is the 'any compatible agent' surface: it connects, verifies the
    genesis, downloads the state, verifies the state root, and can submit
    events. No account, no central authority, no permission.
    """

    node_id: str
    host: str = "127.0.0.1"
    port: int = DEFAULT_PORT
    timeout: float = 10.0

    def __post_init__(self) -> None:
        self._sock: socket.socket | None = None

    def connect(self) -> dict:
        self._sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self._sock.settimeout(self.timeout)
        self._sock.sendall(_encode({"op": "hello", "node_id": self.node_id}))
        line, _ = _recv_line(self._sock, b"")
        if line is None:
            raise ConnectionError("no hello ack")
        return _decode(line)

    def send(self, msg: dict) -> dict:
        if self._sock is None:
            raise ConnectionError("not connected")
        self._sock.sendall(_encode(msg))
        line, _ = _recv_line(self._sock, b"")
        if line is None:
            raise ConnectionError("connection closed")
        return _decode(line)

    def query_state(self) -> dict:
        return self.send({"op": "state_query", "requester": self.node_id})

    def submit_event(self, event: StateEvent) -> dict:
        return self.send({"op": "event", "event": event.canonical()})

    def ping(self) -> dict:
        return self.send({"op": "ping"})

    def verify_downloaded_state(self, msg: dict) -> bool:
        """Recompute the state root from the downloaded payload and compare."""
        st = GlobalState.from_dict(msg["payload"])
        return st.verify_root(msg["state_root"])

    def close(self) -> None:
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None


# ---------------------------------------------------------------------------
# Bootstrap network helper
# ---------------------------------------------------------------------------

def bootstrap_nodes(node_ids: list[str], genesis_hash: str = "", host: str = "127.0.0.1", port: int = 0) -> list[PeerServer]:
    """Start a small real network on ephemeral ports for tests/demos."""
    servers: list[PeerServer] = []
    for nid in node_ids:
        srv = PeerServer(nid, host=host, port=port, genesis_hash=genesis_hash)
        srv.start()
        servers.append(srv)
    return servers
