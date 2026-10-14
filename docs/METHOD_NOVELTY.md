# Method novelty

ETGI is a candidate method, not a list of firsts.

## Not claimed

- Iterative tool use. PROVSEEK and CyberSleuth already do this.
- A graph that guides where an agent looks. GALA+ does this with a service topology. GraphRAG and HippoRAG 2 do it for documents.
- A temporal graph. Graphiti invalidates facts over time.
- Grounded question scoring. ExCyTIn-Bench, FActScore, and RAGChecker already separate the writer from the score.
- Prompt search, few-shot libraries, or CVE-specific instructions. The task text and the tool schema are fixed. The experiment changes the workflow switches.

## Candidate claims

1. Hypothesis-driven investigation of one OT window. The model chooses evidence queries over flows, IEC-104 ASDUs, and network-reported electrical state. Record-link edges are built from the index; inferred edges come from the model. Either set may be empty.
2. Source-aware revision. A supported edge must be a communication, a shared frame, a shared CA/IOA report, or two attributes of one device. Shared-source pairs are one independent group. Revision is appended. The previous proposal stays in the edge history.
3. Evidence-necessity testing. The judgment prompt contains only the cited cards. Ablation removes the card and any row with the same frame hash or parent packet, and the tools stay disabled so the row cannot re-enter. Repeats use temperature 0 and a fixed seed. Sensitivity is reported as model dependence.

## What would count as support

On the same window, model, and budget, full ETGI should retrieve at least as much of the SQL gold as B0–B3, publish fewer supported edges that fail the record-link check, and show a lower source-dependency error count than the ablation that disables that audit. Necessity should flag citations whose removal changes a stable judgment, and it should not be described as proof.

## What would count against the claim

- The model never calls a tool, so the gap fallback does the searching.
- Disabling necessity, contradiction search, or revision leaves question coverage and unsupported edges unchanged.
- Cross-modal edges remain supported after the source audit is removed, because the model and the checker are both reading the same IEC-104 value twice.
- Frame hashes never match across vantages, so the same-frame test has nothing to find. That result is reported, not patched.
- The narrative has to be discarded because it cites ids or numbers that are not in the findings.

The implementation can be finished while any of these is true. A finished program is not a confirmed hypothesis.
