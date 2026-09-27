# r5 planned development validation and proposed transport policy

OFFLINE ONLY. 8192 output tokens is NOT YET VALIDATED and NOT FROZEN. 4096 remains the executed r4 setting and is rejected as the intended final setting because 55/144 positions ended specifically at that output ceiling. 16384 is the unchanged INPUT EVIDENCE SAFETY CEILING, not a proposed output cap.

## Exact 64-position manifest

`results/investigation-r5/validation_manifest.json` binds each event/cell/repetition, view, citation mode, bundle, receipt and request hash. The 40 capacity positions additionally bind original completed manifest, request, provider attempt, response ID and original output hash.

- G0: 19 prior B2 output-cap truncations. Prompt and complete request are unchanged except 4096→8192.
- G1-EN: 21 prior B3 output-cap truncations. Same exact request-diff restriction.
- G1-E: the four already reviewed pilots × 3 repetitions = 12.
- G1-N: the same pilots × 3 repetitions = 12; required citations, not old B1 behavior.
- V1-EN: 21 corresponding replay positions, zero model calls; missing/incomplete source yields unavailable, not regenerated JSON.

Exclude all 15 historical B1 truncations and the one terminal B3 ConnectionResetError position from this 64-position manifest. Preserve every original/recovery/unknown/truncated r4 record. New outputs, if later authorized, are separate validation artifacts and never replace r4 or form a mixed-limit performance matrix.

Offline input audit covers all 16 development E bundles, plus N/EN counterparts, for schema, view, necessary metadata, entry/48,000-byte budgets, 16,384 input-token ceiling and receipt/hash binding. E maximum observed is 12,870 evidence tokens. It is not used to redefine the safety ceiling. No evaluation evidence is read.

## Acceptance (pure function in acceptance.py)

1. Zero responses terminated specifically by max_output_tokens.
2. All otherwise delivered new-condition smoke responses pass strict output/local schema, context/links and view/reference visibility checks.
3. Requests match the declared manifest/diffs.
4. All protocol/input/gold/prompt/retrieval/matching/verifier/metric bindings stay unchanged during the future run.

Any output-cap truncation is retained and causes FAIL_OUTPUT_CAP_STOP_AUTHOR_REVIEW: stop capacity acceptance, no automatic retry and no output-limit increase. Transport failures, rate limits, refusals and other no-delivery outcomes are separate, neither positive nor negative evidence about output capacity; pending/no-delivery makes overall acceptance inconclusive. The candidate is not automatically frozen even if development passes. Content errors, weak answers and verifier rejection never trigger retries or cap changes.

## Proposed exact transport policy — requires author review before live use

- Same request body and output cap across attempts; maximum 3 attempts per position (2 retries).
- Single flight. At least 60 seconds between request starts; honor Retry-After when it requires a longer wait (numeric seconds or HTTP date). Request timeout 120 seconds. One pacing scheduler must span positions as well as within-position retries; the offline fixture utility tests retry spacing only and is not a live batch scheduler.
- Retry HTTP 408/429/500–599; no automatic additional recovery after the third attempt.
- Retry ConnectionError subclasses including ConnectionResetError, ConnectionAbortedError, BrokenPipeError, ConnectionRefusedError; TimeoutError/socket.timeout; RemoteDisconnected; IncompleteRead; narrowly allowlisted OSError errno ECONNRESET/ECONNABORTED/ECONNREFUSED/EPIPE/ETIMEDOUT/ENETUNREACH/EHOSTUNREACH. URLError is retryable only when its underlying exception is in this allowlist.
- Never treat every OSError/URLError as retryable: local file errors, permissions, certificate/TLS configuration errors and unclassified exceptions remain terminal for review.
- Preserve the existing delivery-envelope boundary: retry malformed provider envelopes or completed responses without a recoverable claims/questions object; retain recoverable schema-invalid objects without retry.
- Never retry provider refusal, provider incomplete/output-cap stop, wrong model, nonretryable HTTP, low quality, absent citations, invisible references, numerical/semantic errors, low score or verifier disposition.
- Every attempt has create-once request hash, attempt/status/reason, raw body where available, provider IDs/usage where available and retry decision. Unknown response delivery consumes an attempt; usage remains unknown, not zero. Never overwrite historical attempts or choose best-of.

ConnectionResetError was caught as terminal implementation failure in r4. r5's proposed narrow classification is tested on synthetic exceptions only; historical status is unchanged. No real adapter or credential loading exists in the r5 candidate; `generate()` fails closed. Only a built-in finite synthetic reply fixture may exercise the offline retry utility.

## Account pacing limitation before future execution

The account last observed 30,000 TPM. r4 recorded provider input up to 21,336 tokens; new E view's exact provider accounting at 8192 has not been observed. Local text+strict-schema+output-reservation counts are conservative and are not the provider's exact TPM estimator (the prompt itself embeds schema). Store and disclose these estimates; do not claim the new requests have already been proven to fit the account rate limit. Confirm sufficient per-request/headroom and rate-aware scheduling before future live authorization. Waiting cannot solve a provider-declared request larger than its allowed request/window capacity; report that condition instead of launching repeated parallel attempts. No account limit was changed here.

Final 32-event matrix: G0/G1-E/G1-N/G1-EN each 96 positions = 384 generation positions; V1-EN 96 replay positions; D0 32 deterministic references. Development plan 64 positions plus final evaluation 384 = 448 generation positions before transport retries. No costs or model quality scores are estimated in r5.
