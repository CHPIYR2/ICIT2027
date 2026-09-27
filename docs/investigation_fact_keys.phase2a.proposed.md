# Fact-key / deduplication proposal

Status: PROPOSED, author review pending. Implementation:
`src/investigation/fact_keys_phase2a.py`. No automatic fact merging.

Key format: `fk_` + SHA256 of canonical JSON containing key version, event ID,
normalized kind and the typed identity fields below. IDs are opaque and event-scoped.
Sort unordered mapping/support ID sets; preserve causal-neutral chronological roles.
Never hash arbitrary free text to decide semantic equivalence.

| Kind | Identity |
|---|---|
| weak command observation | m ID |
| mapped command observation | m + a + control M + control point + asset IDs |
| reported value | e ID |
| numerical difference / percent | ordered before/after e IDs + quantity + unit |
| state change | ordered before/after e IDs |
| command-address asset relation | m + a + control M + asset |
| observation-channel asset relation | observed e + channel M + channel + asset |
| same mapped asset relation | unordered e IDs + mapping IDs + asset |
| packet endpoint pair | p + directional source/destination endpoints |
| temporal relation | actual endpoint IDs + relation + scope + static mapping IDs + asset or null |
| network primitive / acknowledgement | observed p/m + activity/kind |
| captured gap | complete query d ID + population + bounds |

`electrical_change` normalizes to `reported_change` only for the same ordered pair,
quantity and unit. Difference and percent change remain distinct quantities;
reviewers may model them as alternative renderings of one salient fact with an
explicit adjudicated alias, not an automatic key collapse. Timestamp-equality
relations normalize endpoint order; `precedes` keeps direction.

Typed identity keys do not validate claimed numeric values, timing, metadata,
causality, salience, or truth. These are separate evidence checks / human judgments.
Same m with and without a target is a different proposition strength; same E pair
with a causal interpretation is not the same numerical claim.

Override workflow: preserve proposed_fact_key and its descriptor; fill fact_key,
key_override_reason, alias_decision, alias_of and alias_rationale. Merge only after
human review. Alias targets must be within one event; cycles, duplicate unresolved
keys, divergent view decisions and double-counting a numerical pair/quantity are
errors. Alternate evidence sets for the same human fact may require a reviewed
canonical key; automatic record identity alone cannot discover semantic equivalence.

Free-text weak review interpretations and insufficiency opportunities need a
human-defined key and rationale. No generic text-similarity merge and no generated
positive security gold. Multiple candidate records or shared ancestry are not
independent gold units. Candidate groups remain DRAFT_UNREVIEWED until reviewed.
