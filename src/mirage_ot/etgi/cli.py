"""Command line for indexing, investigation, and the comparison suite."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .agent.controller import Flags, investigate
from .agent.ollama import OllamaClient
from .evaluation.harness import MODALITY_PRESETS, build_questions, preset, run_named
from .evidence.index import index_window, open_indexed
from .evidence.queries import EvidenceDB
from .reporting.generator import write_report


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="etgi", description="Evidence-seeking temporal graph investigation")
    commands = parser.add_subparsers(dest="command", required=True)
    index = commands.add_parser("index")
    index.add_argument("--archive", type=Path, required=True)
    index.add_argument("--scenario", required=True)
    index.add_argument("--recording", required=True, choices=("train", "test"))
    index.add_argument("--start", type=float, required=True)
    index.add_argument("--end", type=float, required=True)
    index.add_argument("--context-seconds", type=float, default=15)
    index.add_argument("--modalities", default="both", choices=("both", "network", "electrical"))
    index.add_argument("--out", type=Path, required=True)
    investigate_cmd = commands.add_parser("investigate")
    investigate_cmd.add_argument("--db", type=Path, required=True)
    investigate_cmd.add_argument("--out", type=Path, required=True)
    investigate_cmd.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    investigate_cmd.add_argument("--endpoint", default="http://127.0.0.1:11434")
    investigate_cmd.add_argument("--method", default="ETGI")
    investigate_cmd.add_argument("--modality", default="both", choices=MODALITY_PRESETS)
    investigate_cmd.add_argument("--max-tool-calls", type=int)
    investigate_cmd.add_argument("--max-llm-calls", type=int)
    investigate_cmd.add_argument("--necessity-repeats", type=int)
    investigate_cmd.add_argument("--max-necessity-relations", type=int)
    investigate_cmd.add_argument("--num-predict", type=int)
    investigate_cmd.add_argument("--action-interface", choices=("native_tools", "json_action"))
    investigate_cmd.add_argument("--no-gap-fallback", action="store_true")
    investigate_cmd.add_argument("--investigation-memory", action="store_true")
    investigate_cmd.add_argument("--subgoal-planning", action="store_true")
    investigate_cmd.add_argument("--num-ctx", type=int)
    suite = commands.add_parser("suite")
    suite.add_argument("--db", type=Path, required=True)
    suite.add_argument("--out", type=Path, required=True)
    suite.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    suite.add_argument("--endpoint", default="http://127.0.0.1:11434")
    suite.add_argument("--methods", default="B0,B1,B2,B3,ETGI")
    suite.add_argument("--modality", default="both", choices=MODALITY_PRESETS)
    suite.add_argument("--max-tool-calls", type=int)
    suite.add_argument("--max-llm-calls", type=int)
    suite.add_argument("--necessity-repeats", type=int)
    suite.add_argument("--max-necessity-relations", type=int)
    post = commands.add_parser("postalert")
    post.add_argument("--db", type=Path, required=True)
    post.add_argument("--out", type=Path, required=True)
    post.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    post.add_argument("--endpoint", default="http://127.0.0.1:11434")
    post.add_argument("--methods", default="B4")
    post.add_argument("--num-predict", type=int, default=512)
    post.add_argument("--num-ctx", type=int, default=8192)
    protocol = commands.add_parser("postalert-protocol")
    protocol.add_argument("--protocol", type=Path, required=True)
    protocol.add_argument("--out", type=Path, required=True)
    protocol.add_argument("--endpoint", default="http://127.0.0.1:11434")
    pb = commands.add_parser("position-bias")
    pb.add_argument("--out", type=Path, required=True)
    pb.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    pb.add_argument("--endpoint", default="http://127.0.0.1:11434")
    pilot = commands.add_parser("pilot-pool")
    pilot.add_argument("--out", type=Path, required=True)
    peval = commands.add_parser("pilot-eval")
    peval.add_argument("--pilot-dir", type=Path, default=Path("runs/etgi/t3-pilot-pool-20261015"))
    peval.add_argument("--out", type=Path, required=True)
    peval.add_argument("--endpoint", default="http://127.0.0.1:11434")
    recon = commands.add_parser("reconstruct")
    recon.add_argument("--db", type=Path, required=True)
    recon.add_argument("--out", type=Path, required=True)
    recon.add_argument("--model", default="qwen3.5:9b-q4_K_M")
    recon.add_argument("--endpoint", default="http://127.0.0.1:11434")
    recon.add_argument("--no-llm", action="store_true")
    recon.add_argument("--num-predict", type=int, default=512)
    recon.add_argument("--num-ctx", type=int, default=8192)
    args = parser.parse_args(argv)
    if args.command == "reconstruct":
        from .reconstruction.engine import reconstruct_incident
        conn, meta = open_indexed(args.db)
        start = float(meta["incident_start"])
        end = float(meta["incident_end"])
        bg_start = start - float(meta.get("context_seconds") or 15.0)
        db = EvidenceDB(conn, incident_start=start, incident_end=end)
        llm_client = None if args.no_llm else OllamaClient(args.model, endpoint=args.endpoint)
        result = reconstruct_incident(
            db, start, end, background_start=bg_start, background_end=start,
            llm=llm_client, num_predict=args.num_predict, num_ctx=args.num_ctx,
            seed=1, out_dir=args.out,
        )
        conn.close()
        print(json.dumps({
            "out": str(args.out),
            "code_sha256": result["manifest"]["code_sha256"],
            "transactions": result["transactions"]["transaction_count"],
            "graph_nodes": result["event_graph"]["node_count"],
            "graph_edges": result["event_graph"]["edge_count"],
            "storylines": result["storylines"]["storyline_count"],
            "lineage_bundle": result["lineage_bundle_summary"],
        }, indent=2))
        return
    if args.command == "pilot-eval":
        from .postalert.author_pilot_eval import run_author_validated_pilot_evaluation
        summary = run_author_validated_pilot_evaluation(args.pilot_dir, args.out, endpoint=args.endpoint)
        print(json.dumps({"out": str(args.out), "code_sha256": summary["code_sha256"],
                          "failure_cases": summary["failure_case_count"]}, indent=2))
        return
    if args.command == "position-bias":
        from .postalert.position_bias import run_position_bias_suite
        cases = [
            {"name": "supplied-ev0961", "db": "runs/etgi/basic-ev0961/evidence.sqlite"},
            {"name": "preceding-ev0961", "db": "runs/etgi/basic-ev0961/evidence.sqlite", "window": "preceding", "preceding_seconds": 15},
            {"name": "supplied-ev12", "db": "runs/etgi/memory-comparison-20261014/ev_12dcd56b2f5e78144cfb/evidence.sqlite"},
        ]
        summary = run_position_bias_suite(cases, args.out, model=args.model, endpoint=args.endpoint)
        print(json.dumps({"out": str(args.out), "code_sha256": summary["code_sha256"]}, indent=2))
        return
    if args.command == "pilot-pool":
        from .postalert.pilot_pool import build_pilot_package
        windows = [
            {
                "episode_id": "ev_3e4d36008b29595ef246",
                "scenario": "01-Basic",
                "recording": "test",
                "start": 1742959890.1894352,
                "end": 1742959950.3827677,
                "db": "runs/etgi/memory-comparison-20261014/ev_3e4d36008b29595ef246/evidence.sqlite",
            },
            {
                "episode_id": "ev_3e4d36008b29595ef246_post15s",
                "scenario": "01-Basic",
                "recording": "test",
                "start": 1742959950.3827677,
                "end": 1742959965.3827677,
                "db": "runs/etgi/memory-comparison-20261014/ev_3e4d36008b29595ef246/evidence.sqlite",
            },
        ]
        summary = build_pilot_package(windows, args.out)
        print(json.dumps(summary, indent=2, default=str))
        return
    if args.command == "postalert-protocol":
        from .postalert.runner import run_protocol
        summary = run_protocol(args.protocol, args.out, endpoint=args.endpoint)
        print(json.dumps({"out": str(args.out), "code_sha256": summary["code_sha256"],
                          "bundles": summary["bundles"]}, indent=2, default=str))
        return
    if args.command == "index":
        meta = index_window(
            args.archive, scenario=args.scenario, recording=args.recording, start=args.start,
            end=args.end, out=args.out, context_seconds=args.context_seconds, modalities=args.modalities,
        )
        print(json.dumps({"out": str(args.out), "counts": meta["counts"], "cross_check": meta["cross_check"],
                          "limitations": meta["limitations"]}, indent=2))
        return
    if args.command == "postalert":
        _postalert(args)
        return
    conn, meta = open_indexed(args.db)
    db = EvidenceDB(conn, modality=args.modality, incident_start=meta["incident_start"], incident_end=meta["incident_end"])
    llm = OllamaClient(args.model, endpoint=args.endpoint)
    if args.command == "investigate":
        flags = preset(args.method)
        flags.method = args.method if args.method == "ETGI" else flags.method
        _apply_budget(flags, args)
        result = investigate(
            db, llm, incident_start=meta["incident_start"], incident_end=meta["incident_end"],
            out=args.out, flags=flags, limitations=meta.get("limitations") or [],
        )
        report = write_report(result, db, args.out, llm=llm)
        print(json.dumps({"completion": report["completion"], "relations": len(report["relations"]),
                          "out": str(args.out)}, indent=2))
        return
    questions = build_questions(db, meta["incident_start"], meta["incident_end"])
    (args.out / "questions.json").parent.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "questions.json").write_text(json.dumps(questions, indent=2), encoding="utf-8")
    summaries = []
    for name in [part.strip() for part in args.methods.split(",") if part.strip()]:
        flags = preset(name)
        _apply_budget(flags, args)
        # run_named loads its own preset; apply budget by wrapping investigate through a patched preset
        summary = _run_with_budget(
            db, llm, name, args.out / name, limitations=meta.get("limitations") or [],
            questions=questions, args=args,
        )
        summaries.append(summary)
        print(json.dumps({"method": summary["method"], "completion": summary["completion"],
                          "evidence_sufficiency": summary["questions"].get(
                              "evidence_sufficiency_for_question_reconstruction"),
                          "answer_accuracy": (summary.get("investigation_question_answering") or {}).get(
                              "investigation_question_accuracy"),
                          "unsupported_relation_rate": summary["graph"]["unsupported_relation_rate"]}, indent=2),
              flush=True)
    (args.out / "suite.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")


def _postalert(args) -> None:
    from .postalert.evaluate import gold_facts, score_run
    from .postalert.pipeline import prepare, write_run
    conn, meta = open_indexed(args.db)
    start = float(meta["incident_start"])
    end = float(meta["incident_end"])
    db = EvidenceDB(conn, incident_start=start, incident_end=end)
    background_start = start - float(meta.get("context_seconds") or 0)
    prepared = prepare(db, start, end, background_start=background_start, background_end=start)
    gold = gold_facts(db, start, end)
    llm = OllamaClient(args.model, endpoint=args.endpoint)
    rows = []
    for level in [part.strip() for part in args.methods.split(",") if part.strip()]:
        result = write_run(
            db, llm, prepared, args.out / level, level=level,
            num_predict=args.num_predict, num_ctx=args.num_ctx, seed=1,
        )
        scored = score_run(prepared, result, gold)
        rows.append({"level": level, **scored, **result["trace"]})
        print(json.dumps(rows[-1], default=str), flush=True)
    (args.out / "comparison.json").write_text(json.dumps({"gold": gold, "rows": rows}, indent=2, default=str), encoding="utf-8")


def _apply_budget(flags: Flags, args) -> None:
    if getattr(args, "max_tool_calls", None) is not None:
        flags.max_tool_calls = args.max_tool_calls
    if getattr(args, "max_llm_calls", None) is not None:
        flags.max_llm_calls = args.max_llm_calls
    if getattr(args, "necessity_repeats", None) is not None:
        flags.necessity_repeats = args.necessity_repeats
    if getattr(args, "max_necessity_relations", None) is not None:
        flags.max_necessity_relations = args.max_necessity_relations
    if getattr(args, "num_predict", None) is not None:
        flags.num_predict = args.num_predict
    if getattr(args, "action_interface", None):
        flags.action_interface = args.action_interface
    if getattr(args, "no_gap_fallback", False):
        flags.allow_gap_fallback = False
    if getattr(args, "investigation_memory", False):
        flags.investigation_memory = True
    if getattr(args, "subgoal_planning", False):
        flags.subgoal_planning = True
    if getattr(args, "num_ctx", None) is not None:
        flags.num_ctx = args.num_ctx


def _run_with_budget(db, llm, name, out, *, limitations, questions, args) -> dict:
    """Run a named method and overlay only the budgets the caller set explicitly."""
    from .evaluation import harness
    original = harness.preset

    def patched(requested):
        flags = original(requested)
        _apply_budget(flags, args)
        return flags

    harness.preset = patched
    try:
        return run_named(db, llm, name, out, limitations=limitations, questions=questions)
    finally:
        harness.preset = original


if __name__ == "__main__":
    main()
