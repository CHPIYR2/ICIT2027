# Command-address namespace audit v2

The active versioned schemas live in `schemas/`; old `docs/*.proposed.json` files
are preserved historical proposals. Tests: `tests/test_investigation_v2.py`.

| Location | Allowed role | Does `a_` pass? |
|---|---|---|
| claim.evidence_ids | p / m / e / a / d / meta citations | Yes |
| command.record_id | command message m | No |
| command.address_evidence_id | address a, or null for weak request | Yes |
| command.mapping_evidence_id | static meta, or null | No |
| command_address_observation.parent_ids | exactly one m | No |
| command-address asset relation record_ids | m + a; exactly supported static M edge | Yes |
| same_mapped_asset record_ids | e observations | No |
| packet_endpoint_pair record_ids | p observations | No |
| temporal earlier/later | p / m / e / a actual observations | Yes |
| same_observed_asset temporal scope | a + e, both static M edges and same asset | Yes |
| network / acknowledgement record_id | p / m | No |
| reported_value, numeric/state before/after | e | No |
| gap left/right | p or null | No |
| scope / gap coverage | d | No |
| security basis | p / m / e / d; no blind broadening | No |
| retrieval records | p / m / e / a / derived d | Yes |
| visibility original records | p / m / e / a | Yes |
| visibility address_parents | a keys → visible m values | Keys only |

Both claim and verification schemas use the corrected `$defs`. The finite
schema validator checks field shapes, citations and role-specific cross-field
constraints. Export and retrieval validation additionally enforce actual parent
presence, matching type/COT/capture time, exact control mapping, view visibility,
and matching E channel metadata. B0 support checks require complete m+a+M for
the strengthened request and both mapping edges for same-asset time ordering.

`support_v2.py` accepts only canonical B0 amendment text with exact supported
payloads. This rejects replacing a supported temporal sentence with execution,
causation or malicious-intent language. It is not an arbitrary-language verifier
and does not implement the future B3 baseline.

`retrieval_ids.v2.json` and `visibility_ids.v2.json` are namespace envelopes,
not complete standalone schemas for all evidence content. Their runtime
validators perform reference/closure and view consistency checks against the
actual evidence and bundle. All 144 generated conditions pass deterministic
replay and independent evidence/metadata/time checks.
