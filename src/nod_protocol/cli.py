"""NØD Protocol CLI — minimal registry-backed command line.

Operations: init, submit, verify, mutate, branch, contradict, value, graph, arena
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from nod_protocol.core.provenance import ProvenanceChain, EventType, DisclosureStatus
from nod_protocol.core.objects import NODObject, CognitiveStateLayer, MutationProposal
from nod_protocol.core.lineage import DiscoveryGraph
from nod_protocol.core.value import ComponentScore, ValueComposer
from nod_protocol.arena import Arena, ArenaAgent


class Registry:
    """JSON-backed registry for the demo CLI (spec keeps storage open)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict = {"objects": {}, "chains": {}, "graph": {"nodes": [], "edges": []}}
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


def cmd_init(args) -> None:
    reg = Registry(Path(args.registry))
    reg.save()
    print(f"registry initialized: {args.registry}")


def cmd_submit(args) -> None:
    reg = Registry(Path(args.registry))
    claim = {"claim": args.claim, "domain": args.domain, "evidence": {"kind": args.evidence}}
    chain = ProvenanceChain(nod_id="pending:" + args.agent)
    chain.append(EventType.PROBLEM_STATE, {"problem": args.claim}, args.agent)
    chain.append(EventType.COMMITTED_HYPOTHESIS, {"hypothesis": args.claim}, args.agent,
                 disclosure_status=DisclosureStatus.COMMITTED_ONLY)
    chain.append(EventType.TEST, {"type": args.evidence}, args.agent)
    chain.append(EventType.RESULT, {"result": "positive"}, args.agent)
    chain.append(EventType.TRANSFORMATION, {"note": "initial"}, args.agent)
    chain.append(EventType.VERIFICATION, {"verifier": args.agent}, args.agent)

    obj = NODObject.create(claim, args.domain, args.agent, order=len(reg.data["objects"]))
    obj.link_provenance([e.event_id for e in chain.events])
    reg.data["objects"][obj.nod_id] = obj.to_dict()
    reg.data["chains"][obj.nod_id] = chain.to_dict()
    reg.data["graph"]["nodes"].append(obj.nod_id)
    reg.save()
    print(f"submitted: {obj.nod_id}")


def cmd_value(args) -> None:
    reg = Registry(Path(args.registry))
    raw = dict(reg.data["objects"][args.nod])
    raw.pop("verification_status", None)
    # map stored field names to dataclass constructor names
    key_map = {
        "rights_registry_reference": "rights_registry",
        "value_metrics_reference": "value_metrics",
    }
    raw = {key_map.get(k, k): v for k, v in raw.items()}
    obj = NODObject(**raw)
    composer = ValueComposer()
    scores = ComponentScore(
        utility=float(args.utility),
        novelty=float(args.novelty),
        verification=float(args.verification),
        dependency=float(args.dependency),
        provenance=float(args.provenance),
    )
    result = composer.evaluate(scores)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_graph(args) -> None:
    reg = Registry(Path(args.registry))
    print(json.dumps(reg.data["graph"], ensure_ascii=False, indent=2))


def cmd_arena(args) -> None:
    agents = [ArenaAgent(f"agent-{i}", s, skill=0.6) for i, s in enumerate(args.strategies.split(","))]
    arena = Arena(seed=args.seed)
    result = arena.run({"title": args.challenge, "domain": "optimization"}, agents)
    print(result.summary())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="nod-protocol", description="NØD Protocol CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="create an empty registry")
    p.add_argument("--registry", default="registry.json")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("submit", help="submit a discovery candidate")
    p.add_argument("--registry", default="registry.json")
    p.add_argument("--claim", required=True)
    p.add_argument("--domain", required=True)
    p.add_argument("--evidence", default="benchmark")
    p.add_argument("--agent", default="agent-1")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("value", help="compute composite value for a NØD")
    p.add_argument("--registry", default="registry.json")
    p.add_argument("--nod", required=True)
    p.add_argument("--utility", type=float, default=0.5)
    p.add_argument("--novelty", type=float, default=0.6)
    p.add_argument("--verification", type=float, default=0.5)
    p.add_argument("--dependency", type=float, default=0.4)
    p.add_argument("--provenance", type=float, default=0.7)
    p.set_defaults(func=cmd_value)

    p = sub.add_parser("graph", help="dump the discovery graph")
    p.add_argument("--registry", default="registry.json")
    p.set_defaults(func=cmd_graph)

    p = sub.add_parser("arena", help="run a deterministic Cognitive Arena")
    p.add_argument("--challenge", default="reduce energy consumption")
    p.add_argument("--strategies", default="conservative,bold,hybrid")
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_arena)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
