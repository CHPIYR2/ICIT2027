# Research protocol draft — v0.1 (not registered, not validated)

## Task

Given an already flagged OT event and a specified time interval, extract
network and IEC104-reported electrical telemetry. Learn an **associational**
N–N/P–P/N–P graph and generate a qualified event account from its evidence.
Neither attack-class labels nor domain-specific attack count cutoffs determine
edges. Edges are not ground-truth causal pathways.

## Experimental tracks

1. **Self-supervised forward prediction:** train on explicitly disjoint
   attack-free Basic and Semiurban training data. Evaluate on identified test
   segments in Basic and Semiurban, and cross-scenario Rural. Do not let test
   content update normalization or model weights.
2. **Graph contribution:** compare same model capacity with graph messaging
   enabled/disabled, trained separately. Add random, shuffled and permuted-edge
   controls; report paired per-event MAE with uncertainty intervals.
3. **Multimodal value:** network-only, process-only, both; equalize training
   steps and selection budget. Avoid double-counting IPAL process telemetry
   already included in PCAP as independent physical ground truth.
4. **Downstream investigation:** event-level fact retrieval from observed
   sources and Sherlock official event descriptions **for scoring only**.
   Do not pass attack labels into any model input or prompt.
5. **Graph edge faithfulness:** without independent expert/ground-truth
   relational edge labels, do not report edge precision/recall or causal
   correctness; use predictive utility, reproducibility, predictive ablation
   and data-source checks as clearly limited proxies.
6. **Uncertainty:** current attention weights are not calibrated. Evaluate
   prediction intervals/ensemble variance and held-out forecast NLL before
   claiming any probabilistic confidence. A claim about '90% correct link'
   requires independent edge-level labels or a carefully justified alternate
   target definition.

## Critical leakage risks

- Same physical quantity can be visible in both IPAL and PCAP: observed
  multi-view reporting is not independent physical evidence.
- Archive/test names and attack event metadata are never model inputs.
- Cross-scenario feature normalization is fit only on train. Prefer entity-
  independent encoder and avoid learning fixed asset IDs as class proxies.
- Sherlock 84 previously inspected events were used in earlier research;
  do not call this an untouched confirmatory test.
- Multiple switch vantage points can capture the same packet repeatedly.
  Deduplication/observation-point awareness is required before claims.
- The current bounded-window PCAP parser cannot read all TCP/IEC104 detail.
  Verify basic packet counts, timestamps, CA/IOA, and sampled source rows
  against a proper transcriber before experimental evaluation.
- Repeated time windows from one scenario are statistically dependent.
  Bootstrap by event or recording, not individual time bins.

## Current milestone definition

`pytest -q` succeeds; a synthetic smoke sample can be prepared, trained, and
rendered into graph.json/graph.graphml/graph.html. No publication metric,
Sherlock-specific accuracy, or generalization claim is implied.
