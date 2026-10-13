"""CLI that is usable on synthetic smoke data or Sherlock ZIP members."""
import argparse
import json
from pathlib import Path
import sys
import torch
from .archive import inspect_archive, load_selected
from .fixture import generate
from .features import build_matrix, load_matrix, save_matrix
from .model import (train_model, save_checkpoint, load_checkpoint,
                    infer_graph, evaluate_forecast)
from .graph import graph_dict, save_graph
from .ipal import unix_seconds
from .report import explain_graph
from .types import Observation


def _jsonl(path: Path):
    with path.open(encoding='utf-8') as f:
        for line in f:
            if line.strip():
                obj = json.loads(line)
                yield Observation(**obj)


def main(argv=None):
    p = argparse.ArgumentParser(prog='mirage-ot', description='Self-supervised OT incident relation graph prototype')
    cmd = p.add_subparsers(dest='command', required=True)
    fixture = cmd.add_parser('synthetic-fixture', help='Create a smoke fixture, NOT evaluation data')
    fixture.add_argument('--out', type=Path, required=True)
    fixture.add_argument('--bins', type=int, default=64)
    arch = cmd.add_parser('inspect-archive')
    arch.add_argument('--archive', type=Path, required=True)
    prep = cmd.add_parser('prepare', help='Create feature tensor from a ZIP or synthetic JSONL')
    source = prep.add_mutually_exclusive_group(required=True)
    source.add_argument('--archive', type=Path)
    source.add_argument('--jsonl', type=Path)
    prep.add_argument('--state-member', help='Exact archive member name (try inspect-archive)')
    prep.add_argument('--pcap-member', action='append', default=[], help='Repeat for each observation vantage point')
    prep.add_argument('--start', help='Epoch seconds or timezone-aware ISO 8601')
    prep.add_argument('--end', help='Exclusive end; epoch or ISO 8601')
    prep.add_argument('--bin-seconds', type=float, default=10)
    prep.add_argument('--max-network-nodes', type=int, default=24)
    prep.add_argument('--max-physical-nodes', type=int, default=24)
    prep.add_argument('--max-state-rows', type=int)
    prep.add_argument('--max-packets', type=int)
    prep.add_argument('--out', type=Path, required=True)
    fit = cmd.add_parser('fit', help='Train on TRAIN data only; no labels used')
    fit.add_argument('--train', type=Path, required=True)
    fit.add_argument('--out', type=Path, required=True)
    fit.add_argument('--epochs', type=int, default=6)
    fit.add_argument('--window', type=int, default=12)
    fit.add_argument('--hidden', type=int, default=48)
    fit.add_argument('--max-steps', type=int, default=128)
    fit.add_argument('--no-graph', action='store_true')
    fit.add_argument('--device', choices=['cpu','mps'])
    evaluate = cmd.add_parser('evaluate')
    evaluate.add_argument('--checkpoint', type=Path, required=True)
    evaluate.add_argument('--data', type=Path, required=True)
    plot = cmd.add_parser('graph')
    plot.add_argument('--checkpoint', type=Path, required=True)
    plot.add_argument('--data', type=Path, required=True)
    plot.add_argument('--out', type=Path, required=True)
    plot.add_argument('--top-k', type=int, default=2)
    report = cmd.add_parser('report', help='Optional local Ollama: NOT executed automatically')
    report.add_argument('--graph-json', type=Path, required=True)
    report.add_argument('--model', default='qwen3.5:9b-q4_K_M')
    report.add_argument('--endpoint', default='http://127.0.0.1:11434')
    report.add_argument('--out', type=Path, required=True)
    args = p.parse_args(argv)
    # Mac MPS still used by default when available. Limit excessive CPU threads.
    torch.set_num_threads(min(4, torch.get_num_threads()))
    if args.command == 'synthetic-fixture':
        generate(args.out, bins=args.bins)
        print(f'SYNTHETIC ONLY: {args.out}')
    elif args.command == 'inspect-archive':
        print(json.dumps(inspect_archive(args.archive), indent=2))
    elif args.command == 'prepare':
        if args.archive:
            if not args.state_member and not args.pcap_member:
                p.error('For archive input, set --state-member and/or --pcap-member')
            obs = list(load_selected(args.archive, state_member=args.state_member,
                         pcap_members=args.pcap_member,
                         start=unix_seconds(args.start) if args.start else None,
                         end=unix_seconds(args.end) if args.end else None,
                         max_rows=args.max_state_rows,
                         max_packets=args.max_packets))
        else:
            obs = list(_jsonl(args.jsonl))
        matrix = build_matrix(obs, bin_seconds=args.bin_seconds,
                  max_network_nodes=args.max_network_nodes,
                  max_physical_nodes=args.max_physical_nodes,
                  start=unix_seconds(args.start) if args.start else None,
                  end=unix_seconds(args.end) if args.end else None)
        matrix.metadata['input_type'] = 'sherlock_zip' if args.archive else 'synthetic_jsonl'
        if args.max_state_rows or args.max_packets:
            matrix.metadata['CAPPED_INPUT_EXPLORATORY_ONLY'] = True
        save_matrix(matrix, args.out)
        print(json.dumps({'shape': list(matrix.data.shape), 'nodes': matrix.metadata['node_counts'],
                          'out': str(args.out)}, indent=2))
    elif args.command == 'fit':
        data = load_matrix(args.train)
        model, meta = train_model(data, epochs=args.epochs, length=args.window,
                                 hidden=args.hidden, use_graph=not args.no_graph,
                                 max_steps_per_epoch=args.max_steps, device=args.device)
        meta['trained_on_path'] = str(args.train)
        meta['trained_on_input_type'] = data.metadata.get('input_type', 'unknown')
        save_checkpoint(model, meta, args.out)
        print(json.dumps({'checkpoint': str(args.out), 'final_loss': meta['training_losses'][-1],
                          'warning': 'No attack labels or edge ground truth used.'}, indent=2))
    elif args.command == 'evaluate':
        model, meta = load_checkpoint(args.checkpoint)
        print(json.dumps(evaluate_forecast(model, load_matrix(args.data), meta), indent=2))
    elif args.command == 'graph':
        model, meta = load_checkpoint(args.checkpoint)
        matrix = load_matrix(args.data)
        adjacency, predictions = infer_graph(model, matrix, meta)
        meta_slim = {k: meta[k] for k in ('seed','length','hidden','use_graph')}
        bundle, g = graph_dict(matrix, adjacency, top_k=args.top_k, model_metadata=meta_slim)
        save_graph(bundle, g, args.out)
        print(json.dumps({'nodes': len(bundle['nodes']), 'edges': len(bundle['edges']),
                          'output': str(args.out), 'raw_scores_not_probabilities': True}, indent=2))
    elif args.command == 'report':
        graph = json.loads(args.graph_json.read_text(encoding='utf-8'))
        content = explain_graph(graph, model=args.model, endpoint=args.endpoint)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content, encoding='utf-8')
        print(f'Report saved: {args.out}')


if __name__ == '__main__':
    main()
