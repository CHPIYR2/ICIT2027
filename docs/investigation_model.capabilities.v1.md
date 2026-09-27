# Selected model capability report — development candidate

Candidate: **OpenAI `gpt-4.1-2025-04-14`**, via the Responses API. Final author model
approval and account access verification remain pending. No provider call was made.
Selection used documented capabilities and experimental control requirements, not
Sherlock answers, gold, scores, or a model leaderboard.

| Requirement | Candidate capability / limitation |
|---|---|
| Provider | OpenAI |
| Exact callable identifier | `gpt-4.1-2025-04-14`, not the moving `gpt-4.1` alias |
| Endpoint | `POST https://api.openai.com/v1/responses` |
| Dated snapshot | Published by the provider. The model page lists this exact snapshot. |
| Immutable reproducibility | A dated pin does not guarantee bit-identical execution, permanent availability, or immutable provider infrastructure. No stronger reproducibility guarantee is claimed. |
| Temperature | Responses documents 0–2; candidate uses 0 for this non-reasoning model. Account/runtime compatibility remains untested. Unsupported-parameter errors are terminal, not silently emulated or removed. |
| Seed | No seed request parameter in the selected Responses endpoint. Omit it; do not emulate deterministic sampling. The statistical bootstrap seed is unrelated. |
| Tokenizer | Local `tiktoken==0.12.0`; its mapping for the exact model resolves to `o200k_base`. The vocabulary cache hash is recorded. |
| Context | 1,047,576 tokens, as documented for the snapshot. |
| Maximum output | 32,768 tokens. Proposed output cap uses this published maximum, not observed answer quality. |
| Request isolation | New independent request per repetition; no conversation, previous response, tools, additional retrieval, or API-side truncation. |
| Local token-count scope | Exact tokenizer count of the production evidence string and prompt text. Provider message framing is not claimed to be counted exactly. Actual API usage will be retained after later authorization. |

The candidate supports the structured, finite investigation task and the requested
temperature setting without introducing a hidden reasoning-token control. This is
one defensible baseline model choice, not a claim that it is the newest or best
performer. B1–B3 share it; B4 verifies the corresponding stored B3 output.

Reproducibility records include requested/returned model, response ID, provider
created_at/status/usage/error/incomplete details/service tier, returned controls,
HTTP status and request IDs, local start/end timestamps, repetition and attempt,
request/response/output hashes, prompt/bundle/receipt/configuration/code hashes.
Record `system_fingerprint` only if returned; absence stays null. API credentials
are never placed in run artifacts. `store=false` and `truncation=disabled` are explicit.

Official sources checked for this candidate:

- [GPT-4.1 model and snapshot details](https://developers.openai.com/api/docs/models/gpt-4.1)
- [Responses create reference](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Official token-counting example](https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken)

Fetch metadata, reference digest, and local tokenizer/dependency versions are in
`results/investigation-development-v1/official_source_receipts.json` and
`dependency_versions.json`. These are retrieval receipts, not provider-signed
immutability guarantees. Model approval is still required before live API use.
