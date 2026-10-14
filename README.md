# MIRAGE-OT

The current method is ETGI, Evidence-Seeking Temporal Graph Investigation.
A local model queries a Sherlock window, proposes relations, and a record
check decides whether each relation is supported, disputed, or unresolved.
Electrical values stay marked as network-reported. The method specification
is `docs/ETGI_RESEARCH_SPEC.md`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
pytest -q
etgi index --archive data/raw/sherlock/v3/01-Basic.zip \
  --scenario 01-Basic --recording test \
  --start 1742961051.1897168 --end 1742961125.4603136 \
  --out runs/etgi/basic-ev0961/evidence.sqlite
etgi investigate --db runs/etgi/basic-ev0961/evidence.sqlite \
  --out runs/etgi/basic-ev0961/etgi-qwen --model qwen3.5:9b-q4_K_M
```

The GRU forecast prototype below is the earlier negative result. ETGI does
not import it. Attack labels and `physical.zip` are not investigation inputs.

**Brand-new implementation, intentionally unrelated to earlier EBRL code.**
The prototype below learns within-network, within-electrical, and
network–electrical statistical dependencies. Attack-specific recognition
rules are not used. An optional Ollama interface explains the frozen learned graph.

**Status:** Working **synthetic smoke-test prototype**, **NOT** a validated
Sherlock v3 result, nor an established relation confidence estimator.
The current data adapter for Sherlock is preliminary and needs validation against
the actual ZIP layout and a full IEC-104/PCAP transcriber on the user's Mac.

## Requirements

Python 3.10+ and PyTorch 2.2+. On Apple Silicon, PyTorch can use the MPS backend.
Only `numpy`, `torch`, `networkx` are necessary for core training and graph
exports. Optional Ollama report uses Python standard library `urllib`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

## End-to-end synthetic smoke test (do NOT report as efficacy)

```bash
mirage-ot synthetic-fixture --out runs/toy/synthetic.jsonl
mirage-ot prepare --jsonl runs/toy/synthetic.jsonl --out runs/toy/train.npz
mirage-ot fit --train runs/toy/train.npz --epochs 2 --max-steps 16 \
  --out runs/toy/model.pt
mirage-ot evaluate --checkpoint runs/toy/model.pt --data runs/toy/train.npz
mirage-ot graph --checkpoint runs/toy/model.pt --data runs/toy/train.npz \
  --out runs/toy/graph
open runs/toy/graph/graph.html  # macOS
```

The smoke test uses **the same toy data for training and inference** only to
confirm the pipeline runs; it is NOT generalization evidence.
The graph HTML is fully self-contained and works offline.

## Sherlock v3 adapter (without extracting large ZIP archives)

Check the [Sherlock documentation](https://sherlock.wattson.it/data-format/).
Sherlock v3 contains `01-Basic.zip`, `02-Semiurban.zip`, and `03-Rural.zip`.
The `.state.gz` data exposes grid state as reported in IEC-104/IPAL; it is
**not independent physical ground truth**.

On the user's Mac, keep original ZIPs at:
`/Users/potinglu/Documents/ICIT2027/data/raw/sherlock/v3`.
The new worktree may use a **read-only convention** symlink at
`data/raw/sherlock/v3` instead of copying ~8.9 GB of archives.

```bash
mirage-ot inspect-archive --archive data/raw/sherlock/v3/01-Basic.zip
```

Find the exact `.state.gz` and `.pcap`/`.pcap.gz` paths *inside the archive*,
then pass them **explicitly** (example placeholders, do not copy literally):

```bash
mirage-ot prepare \
  --archive data/raw/sherlock/v3/01-Basic.zip \
  --state-member 'ACTUAL/PATH/train.n302.state.gz' \
  --pcap-member 'ACTUAL/PATH/train.n302.pcap.gz' \
  --start '2024-01-01T00:00:00+00:00' \
  --end   '2024-01-01T01:00:00+00:00' \
  --out runs/basic-train/features.npz
```

Use actual, disjoint train/test time scopes. Do **not** feed the attack event
label or its descriptive text to the model; event metadata is evaluator-only.
Do not load `physical.zip` in the normal inference path (loader blocks it).
`--max-state-rows` and `--max-packets` are optional exploratory caps and
must be disclosed as sampling. Archive parsing streams records from ZIP.
**However, feature preparation currently collects window observations into RAM**:
use a bounded time window on large captures.

### Parser limitations (critical before full real experiments)

The bundled PCAP decoder handles classic Ethernet/IPv4/TCP/ARP, not PCAPNG,
IPv6, IP fragmentation, TCP retransmission deduplication, TCP stream
reassembly, or complete IEC-104 transaction semantics. IEC104 port 2404 is
tracked only as a *candidate*, not a decoded command type. Multiple PCAP
vantage points may duplicate the same flow; this must be reconciled before
claimed incident findings. Sherlock state records can include already parsed
network-reported measurements. A state snapshot and its underlying PCAP
should not be assumed to be two independent evidential sources.

**Cursor should replace/validate these adapters with the dataset's IPAL
transcriber and a robust IEC104 parser before paper-scale runs.**

## Method

For each time bin and network flow / process-value channel, construct a feature
vector (without attack-class rules). A shared GRU encoder learns temporal
features, and query/key projections learn row-normalized graph attention.
The model forecasts the next time bin using same-node and relational
information. Relation edges are exported with their **source record IDs**.

**The edge score is a learned attention weight, NOT a likelihood of a real
relationship and NOT evidence of causality or attack success.** Edges are
ranked for visualization (`--top-k`), not classified by attack-specific rules.

## Baselines and fair evaluation

A first executable ablation uses `--no-graph` in `fit`. Train it **separately**,
using the same train features and hyperparameters, then evaluate both on a
**different, disjoint** test scenario/time interval with `evaluate`.

```bash
mirage-ot fit --train runs/basic-train/features.npz --out runs/graph.pt
mirage-ot fit --train runs/basic-train/features.npz --out runs/no-graph.pt --no-graph
mirage-ot evaluate --checkpoint runs/graph.pt --data runs/rural-test/features.npz
mirage-ot evaluate --checkpoint runs/no-graph.pt --data runs/rural-test/features.npz
```

This is a **forecasting utility** comparison, not an edge precision estimate.
Further baselines, true experiment splits, N/P ablations, multiple seeds,
confidence calibration and relation evaluation require additional work.
See `docs/RESEARCH_PROTOCOL.md`.

## Local Qwen/Gemma reporting (optional)

```bash
mirage-ot report --graph-json runs/toy/graph/graph.json \
  --model qwen3.5:9b-q4_K_M --out runs/toy/report.md
```

Requires Ollama at `http://127.0.0.1:11434`. **Reporting does not change graph
edges or scores**. LLM text is not automatically factual; citations must be
audited prior to use in papers.

## Research environment and handoff

- Suggested new branch: orphan `mirage-ot` with new Git worktree
  `/Users/potinglu/Documents/ICIT2027-mirage`.
- All new code is in this ZIP; nothing from the old EBRL was imported.
- Original Sherlock v3 dataset should be mounted as a path, not copied or pushed.
- See `docs/CURSOR_HANDOFF_zh-TW.md` for precise next actions on macOS.
- References: Sherlock v3 https://doi.org/10.5281/zenodo.18467070;
  Neural Relational Inference https://proceedings.mlr.press/v80/kipf18a.html;
  Temporal Graph Networks https://arxiv.org/abs/2006.10637;
  TS2Vec https://ojs.aaai.org/index.php/AAAI/article/view/20881.
