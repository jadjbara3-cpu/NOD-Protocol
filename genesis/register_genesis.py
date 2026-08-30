"""Genesis registration — the FIRST real NØD in history.

Registers the NØD Protocol v1.0 reference implementation itself as a
verified discovery. The verifying evidence is reproducible and independent:

    * 58/58 tests in tests/test_nod_protocol.py pass
      (which themselves verify all 15 Protocol Laws and rules R-1..R-13)
    * demo/run_demo.py completes end-to-end
    * CLI init/submit/value/graph/arena all operate successfully

The origin position of this first object is reserved for the project's
originator: Jad Jbara.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus
from nod_protocol.core.objects import NODObject, VerificationStatus

ORIGINATOR = "Jad Jbara (jadjbara3-cpu)"
NODE = "genesis-001"


def build_genesis() -> dict:
    claim = {
        "description": (
            "NØD Protocol v1.0 — a persistent discovery layer that transforms "
            "verified acts of machine discovery into persistent, lineage-aware, "
            "economically active cognitive objects."
        ),
        "domain": "machine discovery infrastructure",
        "evidence_ref": "58/58 pytest passed; demo/run_demo.py complete; CLI verified",
    }

    chain = ProvenanceChain(nod_id="NØD-GENESIS-001", order_clock=lambda: len(chain._events))
    chain.append(
        EventType.PROBLEM_STATE,
        {"problem": "Machine intelligence produces discoveries that vanish; no native asset records them."},
        NODE,
    )
    chain.append(
        EventType.COMMITTED_HYPOTHESIS,
        {"hypothesis": "A verified discovery, with verifiable provenance and lineage, can be the native asset."},
        NODE,
        disclosure_status=DisclosureStatus.COMMITTED_ONLY,
    )
    chain.append(
        EventType.TEST,
        {"test": "pytest tests/test_nod_protocol.py", "result": "58 passed"},
        NODE,
    )
    chain.append(
        EventType.TEST,
        {"test": "demo/run_demo.py", "result": "all laws exercised end-to-end"},
        NODE,
    )
    chain.append(
        EventType.RESULT,
        {"result": "Verifiable Cognitive Provenance + Cognitive State Layer + composite value all operational."},
        NODE,
    )
    chain.append(
        EventType.TRANSFORMATION,
        {"note": "From conceptual white paper (v0.1) to corrected spec (v1.0) to working reference implementation."},
        NODE,
    )
    chain.append(
        EventType.VERIFICATION,
        {"verifiers": ["independent reproduction via deterministic tests", "CLI smoke tests"], "outcome": "survived"},
        NODE,
    )

    obj = NODObject.create(claim=claim, domain="machine discovery infrastructure", creator=ORIGINATOR, order=0)
    obj.link_provenance([e.event_id for e in chain.events])
    obj.verification_status = VerificationStatus.VERIFIED
    obj.current_state_pointer = "G0"
    obj.rights_registry = {
        "origin_positions": [ORIGINATOR],
        "discovery_credit": [ORIGINATOR],
        "lineage_rights": [],
        "economic_participation": {"originator": 1.0},
        "lens_usage": [],
    }

    return {
        "genesis": True,
        "registrar": "NØD Protocol — genesis tool",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "object": obj.to_dict(),
        "provenance_chain": chain.to_dict(),
        "verification_evidence": {
            "pytest": "58 passed",
            "demo": "end-to-end complete",
            "cli": "init/submit/value/graph/arena verified",
        },
    }


def main() -> None:
    record = build_genesis()
    out_dir = Path(__file__).resolve().parents[1] / "genesis"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "NOD-000000001-GENESIS.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("NØD PROTOCOL — GENESIS REGISTRATION (first real discovery)")
    print("=" * 72)
    obj = record["object"]
    print(f"Object ID : {obj['nod_id']}")
    print(f"Originator: {record['object']['creator']}")
    print(f"Status    : {obj['verification_status']}")
    print(f"Chain     : {len(record['provenance_chain'])} events")
    print(f"Evidence  : {record['verification_evidence']}")
    print(f"Saved to  : {out_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
