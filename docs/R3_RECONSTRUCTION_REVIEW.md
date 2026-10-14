# R3 reconstruction review pack

Local run directory: `runs/etgi/reconstruction-r3-20261015/`.
R1 and R2 directories were not overwritten.
Code SHA-256 of `postalert/*.py` plus `reconstruction/*.py`: `ba06d033607dea894bd1fff18f9e19e13fc5eceee8bb77beaf2b81a1493d7ff3`.
LLM was not called (`--no-llm`). The indexed Sherlock databases are the same ones used for R2.

The full `transactions.json`, `event_graph.json`, `storylines.json`, `run_manifest.json`, and `evidence_audit_bundle.json` remain in that run directory. They are not committed: the audit bundles are 158–330 KB of indexed evidence rows, and `runs/` is outside the review commit.

## Checks

- Every `supported_inference` edge is absent. The two R2 inferences fail `pre_quality_unknown` and `post_quality_unknown`, matching the transaction gate.
- Every storyline reports `spine_is_contiguous_directed_path=true`, and each step joins the adjacent spine facts.
- IPAL rows attached to transactions use `source_binding=unconfirmed_temporal_correspondence`, `counts_as_independent_source=false`, and their own `SRC-IPAL-...` id. Derivation edges that previously copied `facts[-1]` are gone.
- Lineage export: requested, expected, and exported counts match, with `missing_ids=[]` and `row_check_failures=[]`.

## ev_0961f1c2da8a257e3ebc

Window `1742961051.1897168`–`1742961125.4603136`. Lineage 312/312.

| Transaction | Acceptance | State status | Gate |
| --- | --- | --- | --- |
| TX001 `switch.23:closed` | confirmation_observed_acceptance_unknown | state_report_observed_value_unknown | value unknown, no pre baseline |
| TX002 `switch.24:closed` | confirmation_observed_acceptance_unknown | state_report_observed_value_unknown | value unknown, no pre baseline |
| TX003 `switch.25:closed` | confirmation_observed_acceptance_unknown | state_report_observed_value_unknown | value unknown, no pre baseline |
| TX004 `sgen.6:target_active_power` | confirmation_observed_acceptance_unknown | measurement_observed_transition_unverified | `pre_quality_unknown`, `post_quality_unknown` |

Graph: 34 nodes, 45 edges, `supported_inference=0`, unresolved command-effect candidates=4, temporal co-occurrence=16.
Storylines: SL001–SL003 are command → confirmation → COT=3 report (3 independent sources). SL004 is command → confirmation → IPAL setpoint update (2 independent sources). SL005–SL006 are same-device electrical chains with no control command.

## ev_3e4d36008b29595ef246

Window `1742959890.1894352`–`1742959950.3827677`. Lineage 228/228.

| Transaction | Acceptance | State status |
| --- | --- | --- |
| TX001 `switch.31:closed` | confirmation_observed_acceptance_unknown | state_report_observed_value_unknown |
| TX002 `switch.30:closed` | confirmation_observed_acceptance_unknown | no_state_change_observed |
| TX003 `switch.27:closed` | confirmation_observed_acceptance_unknown | state_report_observed_value_unknown |

Graph: 29 nodes, 59 edges, `supported_inference=0`.
Storylines: SL001 and SL003 are command → confirmation → COT=3 report. SL002 is command → confirmation only. SL004–SL006 are same-device electrical chains.

## ev_12dcd56b2f5e78144cfb

Window `1742949082.2307525`–`1742949112.2784526`. Lineage 149/149.

| Transaction | Acceptance | State status | Gate |
| --- | --- | --- | --- |
| TX001 `sgen.10:target_active_power` | confirmation_observed_acceptance_unknown | measurement_observed_transition_unverified | `pre_quality_unknown`, `post_quality_unknown` |

The observed numbers remain 309980.938 → 269971.625 against setpoint 270000.0. They are not a `supported_inference` because quality was not decoded.
Graph: 29 nodes, 40 edges, `supported_inference=0`.
SL001 spine: command → confirmation → IPAL target update → IPAL active-power update, with `independent_source_container_count=2`. SL002–SL006 are electrical chains without a control command.

## Still limited

- These three indexes predate the quality and Select/Execute fields, so real-window quality stays unknown and Select/Execute is not exercised on them. The counterexample tests cover those fields.
- IPAL rows in these indexes have no parent evidence id, so none can be promoted from temporal correspondence to a shared packet source.
- Events without a control command still have no dedicated reconstruction algorithm. Same-device supported couplings can form a spine; cross-entity proximity stays unresolved.
