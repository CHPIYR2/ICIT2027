# Investigation Protocol v1 — authorized development dry run, r4

Status: **NOT FROZEN**. This additive revision implements the Final Development Dry Run Authorization. The r1–r3 packages, reviewed pilot annotations, and gold snapshot remain unchanged. The local API credential is excluded from Git and from every research manifest and request artifact.

## Controlled scope

The existing 16 development events receive B1, B2, and B3 at repetitions 1–3 (144 retained generation cells). B4 consumes the corresponding stored B3 bytes (48 replay records); incomplete/refused/absent B3 delivery yields an explicit unavailable replay, never regeneration or repair. B0 has one existing deterministic EN timeline per event and three references, not three independent outputs. The 32 evaluation events are denied before evidence access. This dry run cannot freeze the protocol or authorize evaluation.

OpenAI Responses, `gpt-4.1-2025-04-14`, temperature 0, no unsupported seed, `max_output_tokens=4096`, `store=false`, no tools, no conversation state, and API input truncation disabled. Temperature zero is not a determinism guarantee. Every attempt retains the request hash, response bytes/hash, response ID, returned model, status, incomplete reason, usage where returned, headers, client request ID, and timestamps. Retries remain transport/delivery-only, at most three total attempts; malformed or incorrect claim content, missing citations, verifier rejection, refusal, and output-limit truncation do not trigger another model response.

## Narrow single-observation mapping amendment

Only the existing `asset_relationship` payload gains relation `observation_channel_maps_to_asset` in the versioned v3 schemas. Its payload contains exactly one E record ID, one approved channel metadata ID, and a non-null mapped asset ID. Common `channel_ids` and `asset_ids` contain the exact singleton channel and asset; `endpoint_ids` is empty.

The verifier checks visible E evidence, valid quality, exact metadata identity, matching channel/asset/family/unit/attribute/context, opaque lineage identity, and evidence membership in the approved, hash-bound production bundle. The opaque lineage check binds the public record to its original export identity; it does not expose hidden packet ancestry or establish independence of E and N. B3/B4 must also cite both E and M. Optional citations in B1/B2 do not relax the support requirements.

The proposition is only: an observed record is associated with channel C, and approved static metadata maps C to asset A. It does not prove physical state truth or change, command execution or effect, causation, malicious intent, compromise, or attribution. Free text asserting such stronger propositions is not accepted merely because its typed mapping is correct.

The key remains the already reviewed `observation_channel_maps_to_asset` recipe with `record_id`, `mapping_id`, `channel_id`, `asset_id`. Original raw claim types and gold files are unchanged. No new alias, denominator adjustment, or retrieval expansion is introduced. Conformance fixtures for all four gold facts use sealed development evidence; this is not a claim that production retrieval recovered those facts.

## Responses Structured Outputs

The authoritative schema is `schemas/investigation_claim.v3.json`. The API wire schemas are the required-citation and optional-citation forms of `schemas/investigation_response.v3.*.json`, with strict mode enabled. Claim-type, relation, and assertion conditionals are compiled into tagged `anyOf` alternatives rather than unsupported `allOf`/`if`/`then` constructs. Every wire object is closed and all properties required. The unknown branch remains insufficient only.

Array uniqueness and exclusive numeric bounds remain mandatory in the authoritative local validator, because they are not used in the supported API subset. A valid API-shaped response is therefore not automatically a valid experiment response or supported claim. Local schema violations are retained and reported, not retried. The old schemas and unrelated claim definitions are preserved.

Official source: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs). The API status `incomplete` with `incomplete_details.reason=max_output_tokens` is the evidence required for a proposed increase to 8192. An increase still requires author approval and is never applied by this runner.

## Evidence safety ceiling

The ceiling is 16,384 evidence tokens, independently of the observed development maximum of 11,162. The production N=64 and EN=32+32 quotas, ordering, serialization, approved source hashes, and 48,000-byte limit are unchanged. Overflow is a retained preflight failure; there is no trimming, extra retrieval, reranking, or adaptive increase. The actual serialized evidence count is recorded per generation cell. Local text/schema token counts and provider-reported usage are separate quantities.

## Custody, statistics, and matching

Reviewer: R1. Custodian: Author/R1. Method: logical, filesystem, access-control, and hash-based isolation. No independent second custodian, dual annotation, adjudication, or inter-annotator agreement is claimed. The application allowlist and access chains are implemented. External gold storage, separate OS/account ACL enforcement, and custodian access logging still require verified provisioning before formal freeze; an application gate is not a claim of OS-level isolation.

Scenario strata are extracted only from the exact historical event-selection artifact committed by `configs/investigation_events.v1.lock.json`. No model score defines or changes a stratum. The strata file is custodian/statistics metadata, not a model input. The event-level, three-repetition, paired 2,000-bootstrap plan is retained without calculating research results.

Q5/Q6, specialization B, numeric projection, numeric atol 0 / rtol 5e-8, displayed Δt atol 5e-7 seconds, exact timestamp order, and all metric/alias/denominator policies remain as approved. Finite verifier conformance is not an independent human oracle. No Gold Fact Recall, Supported Claim Precision, or verifier accuracy is calculated without the required human review ledger.

## Before formal freeze

Complete and inspect the full development conformance report; resolve implementation defects separately from model limitations; decide on 8192 only if actual output-limit truncation is demonstrated; verify custody/access controls; accept the exact final inventory and remaining limitations; then obtain explicit author freeze approval. Any later change after evaluation gold/results inspection requires a new exploratory protocol version.
