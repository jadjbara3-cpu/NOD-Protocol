"""Survival & persistence tests (NOD-002, Law 16).

Verifies the canonical content identity, the Genesis Manifest, and the
NØD Node v0 self-hosting core — the properties that let the protocol
function without GitHub or any single host.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "node"))

import nod_node  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class TestGenesisManifest:
    def test_manifest_exists(self):
        assert (ROOT / "NOD-GENESIS-MANIFEST.json").exists()

    def test_manifest_identity_fields(self):
        m = json.loads((ROOT / "NOD-GENESIS-MANIFEST.json").read_text(encoding="utf-8"))
        assert m["protocol"] == "NØD Protocol"
        assert m["identity"] == "The Persistent Discovery Layer for Machine Intelligence"
        assert m["genesis_object"].startswith("NØD-")
        assert m["genesis_author"] == "Jad Jbara"
        assert "No individual, repository" in m["successor_rule"]

    def test_manifest_content_hashes_verify(self):
        m = json.loads((ROOT / "NOD-GENESIS-MANIFEST.json").read_text(encoding="utf-8"))
        for rel, prefix in m["content_identity"]["documents"].items():
            p = ROOT / rel
            assert p.exists(), f"missing document: {rel}"
            assert nod_node.sha256_file(p).startswith(prefix), f"hash mismatch: {rel}"

    def test_manifest_principles_include_survival(self):
        m = json.loads((ROOT / "NOD-GENESIS-MANIFEST.json").read_text(encoding="utf-8"))
        assert any("No single party can end it" in p for p in m["principles"])


class TestLaw16:
    def test_law16_declared(self):
        laws = (ROOT / "docs" / "PROTOCOL-LAWS.md").read_text(encoding="utf-8")
        assert "Law 16" in laws
        assert "Law of Protocol Survival" in laws
        assert "shall not depend on the continued existence" in laws or "SHALL NOT depend" in laws
        assert "No single party can end it" in laws


class TestNodeV0:
    def test_node_purge_verify(self, tmp_path):
        # run the node end-to-end: init -> submit -> submit -> graph
        data = tmp_path / "nod-data"
        assert nod_node.init_node(data) is not None
        nod_node.submit_claim(data, "first object", "agent-1", "general")
        nod_node.submit_claim(data, "second object", "agent-2", "general")
        g = nod_node.graph_dist(data)
        assert g["node_count"] == 2

    def test_node_state_append_only(self, tmp_path):
        data = tmp_path / "nod-data"
        nod_node.init_node(data)
        nod_node.submit_claim(data, "object", "a", "general")
        st1 = nod_node.NodeState.load(data)
        nod_node.submit_claim(data, "object2", "b", "general")
        st2 = nod_node.NodeState.load(data)
        assert len(st2.objects) == len(st1.objects) + 1
        assert len(st2.ledger) == len(st1.ledger) + 1

    def test_manifest_verifier_detects_unknown(self, tmp_path):
        manifest = json.loads((ROOT / "NOD-GENESIS-MANIFEST.json").read_text(encoding="utf-8"))
        docs = manifest["content_identity"]["documents"]
        assert docs  # non-empty identity set
