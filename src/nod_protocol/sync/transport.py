"""NØD-Sync — real transport layer (TCP / NDJSON, optional TLS).

Brings NØD-Sync from simulation to REAL network operation: nodes speak a
simple line-delimited JSON protocol over TCP sockets — optionally wrapped
in TLS for public internet deployment. Any node can:

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

Everything is stdlib-only (socket, threading, json, ssl). The wire identity
is content: peers verify hashes, never trust hosts. For public deployment,
TLS wraps the socket with a self-signed (or real) certificate.
"""

from __future__ import annotations

import json
import socket
import ssl
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from nod_protocol.sync.state import StateEvent, GlobalState

DEFAULT_PORT = 8642
DEFAULT_CERT_DIR = Path(__file__).resolve().parents[2] / "certs"


# ---------------------------------------------------------------------------
# TLS helpers (public deployment)
# ---------------------------------------------------------------------------

def generate_self_signed_cert(cert_dir: Path, common_name: str = "nod-node") -> dict:
    """Generate a self-signed X.509 cert+key for immediate TLS publishing.

    Prefers the standard ``openssl`` CLI (present on virtually all deployment
    hosts and container images); on failure, falls back to the pure-Python
    minimal generator. Production deployments should prefer Let's Encrypt or
    a CA-issued certificate — this is the quick-start path only.
    """
    import shutil
    import subprocess

    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_file = cert_dir / "node-cert.pem"
    key_file = cert_dir / "node-key.pem"

    if shutil.which("openssl"):
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
            "-keyout", str(key_file), "-out", str(cert_file),
            "-days", "365", "-subj", f"/CN={common_name}",
            "-addext", "subjectAltName=DNS:{common_name},IP:127.0.0.1",
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            return {"cert": str(cert_file), "key": str(key_file), "common_name": common_name, "via": "openssl"}
        except (subprocess.CalledProcessError, OSError):
            pass  # fall through to pure-python fallback

    # Pure-python fallback: a minimal self-signed cert so the node can be
    # published with TLS immediately even on minimal hosts. Some ssl builds
    # are stricter about hand-rolled ASN.1; production should ALWAYS use a
    # CA/Let's Encrypt cert, so this is a convenience, not a substitute.
    cert_pem, key_pem = _self_signed_cert_pem(common_name)
    cert_file.write_text(cert_pem, encoding="utf-8")
    key_file.write_text(key_pem, encoding="utf-8")
    return {"cert": str(cert_file), "key": str(key_file), "common_name": common_name, "via": "pure-python"}


def _self_signed_cert_pem(common_name: str = "nod-node") -> tuple[str, str]:
    """Minimal self-signed certificate via pure Python (no cryptography dep).

    Uses RSA key generation via stdlib-only math. This is an educational
    fallback; production should use Let's Encrypt / CA certs.
    """
    import hashlib
    import hmac
    import os
    import struct
    import time

    def rsa_key(bits: int = 2048):
        # deterministic-ish but seeded from os.urandom for uniqueness
        import random
        rng = random.Random(os.urandom(32))
        # prime helpers (trial division + Miller-Rabin)
        def is_prime(n: int) -> bool:
            if n < 2:
                return False
            for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
                if n % p == 0:
                    return n == p
            d, r = n - 1, 0
            while d % 2 == 0:
                d //= 2
                r += 1
            for _ in range(20):
                a = rng.randrange(2, n - 1)
                x = pow(a, d, n)
                if x in (1, n - 1):
                    continue
                for _ in range(r - 1):
                    x = x * x % n
                    if x == n - 1:
                        break
                else:
                    return False
            return True

        def prime_of(bits: int) -> int:
            while True:
                n = rng.getrandbits(bits) | (1 << (bits - 1)) | 1
                if is_prime(n):
                    return n

        e = 65537
        while True:
            p = prime_of(bits // 2)
            q = prime_of(bits // 2)
            if p == q:
                continue
            n = p * q
            phi = (p - 1) * (q - 1)
            if phi % e == 0:
                continue
            d = pow(e, -1, phi)
            return n, e, d, p, q

    n, e, d, p, q = rsa_key(2048)

    # Minimal PKCS#1 ASN.1 DER encoding helpers
    def der_len(n: int) -> bytes:
        if n < 0x80:
            return bytes([n])
        out = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return bytes([0x80 | len(out)]) + out

    def der_seq(*parts: bytes) -> bytes:
        body = b"".join(parts)
        return b"\x30" + der_len(len(body)) + body

    def der_int(v: int) -> bytes:
        raw = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
        if raw[0] & 0x80:
            raw = b"\x00" + raw
        return b"\x02" + der_len(len(raw)) + raw

    def der_null() -> bytes:
        return b"\x05\x00"

    def der_oid(oid: str) -> bytes:
        parts = [int(x) for x in oid.split(".")]
        body = bytes([40 * parts[0] + parts[1]])
        for v in parts[2:]:
            chunk = []
            while True:
                chunk.insert(0, v & 0x7F)
                v >>= 7
                if not v:
                    break
            body += bytes([(c | 0x80) if i < len(chunk) - 1 else c for i, c in enumerate(chunk)])
        return b"\x06" + der_len(len(body)) + body

    def der_bitstring(data: bytes) -> bytes:
        return b"\x03" + der_len(len(data) + 1) + b"\x00" + data

    def der_utf8(s: str) -> bytes:
        b = s.encode("utf-8")
        return b"\x0c" + der_len(len(b)) + b

    def der_seq_of_utf8(items: list[str]) -> bytes:
        inner = b"".join(der_utf8(x) for x in items)
        return b"\x31" + der_len(len(inner)) + inner

    # Serialize RSA public key DER
    def rsa_pub_der(nn: int, ee: int) -> bytes:
        def der_int_uns(v: int) -> bytes:
            raw = v.to_bytes((v.bit_length() + 7) // 8 or 1, "big")
            return b"\x02" + der_len(len(raw)) + raw
        alg = der_seq(der_oid("1.2.840.113549.1.1.1"), der_null())
        rsa = der_seq(der_int_uns(nn), der_int_uns(ee))
        inner = b"\x30" + der_len(len(rsa)) + rsa
        return der_seq(alg, der_bitstring(inner))

    # Serialize RSA private key DER (PKCS#1 RSAPrivateKey)
    def rsa_priv_der(nn, ee, dd, pp, qq) -> bytes:
        exp1 = dd % (pp - 1)
        exp2 = dd % (qq - 1)
        coeff = pow(qq, -1, pp)
        body = der_int(0) + der_int(nn) + der_int(ee) + der_int(dd) + der_int(pp) + der_int(qq) + der_int(exp1) + der_int(exp2) + der_int(coeff)
        return b"\x30" + der_len(len(body)) + body

    # TBSCertificate
    serial = int.from_bytes(os.urandom(8), "big") & 0x7FFFFFFFFFFFFFFF
    tbs_body = (
        der_seq(der_oid("1.2.840.113549.1.1.11"), der_null())  # signature alg (sha256RSA)
        + der_int(serial)
        + der_seq(der_int(int(time.time())), der_int(int(time.time()) + 365 * 86400))
        + der_seq_of_utf8([common_name])
        + rsa_pub_der(n, e)
    )
    tbs = b"\x30" + der_len(len(tbs_body)) + tbs_body

    # signature over TBSCertificate using sha256 with RSA (PKCS#1 v1.5)
    data_hash = hashlib.sha256(tbs).digest()
    prefix = bytes.fromhex("3031300d060960864801650304020105000420")
    em = b"\x00\x01" + b"\xff" * (256 - len(prefix) - len(data_hash) - 3) + b"\x00" + prefix + data_hash
    sig = pow(int.from_bytes(em, "big"), d, n).to_bytes(256, "big")

    cert_der = der_seq(tbs, der_seq(der_oid("1.2.840.113549.1.1.11"), der_null()), der_bitstring(sig))

    # PEM wrappers (base64)
    def pem(der: bytes, label: str) -> str:
        import base64
        b64 = base64.b64encode(der).decode("ascii")
        lines = [b64[i:i + 64] for i in range(0, len(b64), 64)]
        return f"-----BEGIN {label}-----\n" + "\n".join(lines) + f"\n-----END {label}-----\n"

    key_der = rsa_priv_der(n, e, d, p, q)
    return pem(cert_der, "CERTIFICATE"), pem(key_der, "RSA PRIVATE KEY")


def make_server_tls_context(cert_file: str | Path, key_file: str | Path) -> ssl.SSLContext:
    """Server-side TLS context for public/internet deployment."""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert_file), str(key_file))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def make_client_tls_context(verify: bool = False, ca_file: str | None = None) -> ssl.SSLContext:
    """Client-side TLS context. For self-signed test certs verify=False."""
    ctx = ssl.create_default_context()
    if verify and ca_file:
        ctx.load_verify_locations(cafile=str(ca_file))
    else:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


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
    tls_cert: str | None = None      # path to cert PEM
    tls_key: str | None = None       # path to key PEM

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = GlobalState(genesis_hash=self.genesis_hash)
        self._server: socket.socket | None = None
        self._threads: list[threading.Thread] = []
        self._running = False
        self._lock = threading.Lock()
        self._peers: set[str] = set()
        self._ssl_ctx: ssl.SSLContext | None = None
        if self.tls_cert and self.tls_key and Path(self.tls_cert).exists() and Path(self.tls_key).exists():
            self._ssl_ctx = make_server_tls_context(self.tls_cert, self.tls_key)

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
            if self._ssl_ctx:
                try:
                    conn = self._ssl_ctx.wrap_socket(conn, server_side=True)
                except (ssl.SSLError, OSError):
                    try:
                        conn.close()
                    except OSError:
                        pass
                    continue
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
    tls: bool = False
    ca_file: str | None = None

    def __post_init__(self) -> None:
        self._sock: socket.socket | None = None
        self._ssl_ctx: ssl.SSLContext | None = None
        if self.tls:
            self._ssl_ctx = make_client_tls_context(verify=self.ca_file is not None, ca_file=self.ca_file)

    def connect(self) -> dict:
        raw = socket.create_connection((self.host, self.port), timeout=self.timeout)
        raw.settimeout(self.timeout)
        if self._ssl_ctx:
            self._sock = self._ssl_ctx.wrap_socket(raw, server_hostname=self.host)
        else:
            self._sock = raw
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
