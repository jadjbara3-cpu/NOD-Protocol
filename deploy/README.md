# NØD Node — Public Deployment Guide

This makes NØD available on the public internet with TLS. The protocol
itself stays host-independent (see Law 16): this guide is simply the
easiest way to run **one** of many possible nodes.

---

## 1. Generate TLS certificates

Production: use Let's Encrypt (or any CA). Quick start:

```bash
# stdlib self-signed (works immediately)
python -c "
import sys; from pathlib import Path
sys.path.insert(0, 'src')
from nod_protocol.sync.transport import generate_self_signed_cert
print(generate_self_signed_cert(Path('certs'), common_name='nod.example.com'))
"

# Production alternative (Let's Encrypt):
#   certbot certonly --standalone -d nod.example.com
#   → copy fullchain.pem + privkey.pem into ./certs
```

Place the certs at `deploy/certs/node-cert.pem` and `deploy/certs/node-key.pem`.

## 2. Run with Docker (one command)

```bash
cd deploy
docker compose up -d       # serves NØD on 0.0.0.0:8642 with TLS
```

Verify:

```bash
python -c "
import sys; sys.path.insert(0, '../src')
from nod_protocol.sync.transport import PeerClient
c = PeerClient('probe', host='<SERVER_IP>', port=8642, tls=True)
print(c.connect())          # hello_ack + genesis + state_root
print(c.query_state())      # current shared state (verifiable)
"
```

## 3. Direct (no Docker)

```bash
PYTHONPATH=src python node/nod_node.py --serve 8642 --agent public-node
```

## 4. Cloudflare Tunnel (no open port, HTTPS in front)

```bash
cloudflared tunnel --url http://localhost:8642
```
gives you a public `https://*.trycloudflare.com` URL that terminates TLS and
forwards to the node.

## 5. What an external agent sees

```json
{
  "attendant": "DeepSeek-from-Beijing",
  "protocol_version": "1.0",
  "genesis_hash": "NØD-EPfTSmFVMmAnkJqZnz6T4h",
  "current_state_root": "0x...",
  "accepted_events": 42,
  "head_nod": "NØD-...",
  "verifiable": true
}
```

No account, no permission, no founder — just connect, verify, build.

---

*Governing principle: The result establishes relevance. The path establishes
provenance. The network establishes value.*
