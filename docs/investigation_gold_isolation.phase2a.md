# Gold isolation rule prepared for Investigation Protocol v1

The four frozen development pilots may inform annotation instructions, prompt
design and future verifier implementation. Phase2A scripts have an explicit pilot
allowlist and never open an evaluation-gold directory.

The 16 development / 32 evaluation event IDs are already frozen. Their existing
evidence and B0 have been inspected; they are not an untouched test set. Do not
select new evaluation events based on gold or system performance.

Before final scoring, freeze the 32-event selection, system code, retrieval,
prompts, model/sampling, schemas, evidence policy, matching tolerances, annotation
guidelines, metrics and final gold version with hashes. An independent annotation
role may prepare evaluation gold using the approved evidence and guidelines;
development tools and prompt/verifier authors must not inspect finalized evaluation
gold or its error analyses during development. Gold custodians, access controls,
publication/signoff roles and the final storage location remain PENDING author
approval. This document is a rule, not a claim that filesystem ACL isolation already
exists on the shared workstation.

Suggested operational sequence (pending custodians):

1. Complete and adjudicate development/pilot annotations and annotation rules.
2. Finalize evaluation gold under the fixed rules in a custodian-controlled store.
3. Record its version/hash without exposing its content to system development.
4. Record and seal the approved system/protocol snapshot before a scoring-only job
   receives gold access; preserve raw outputs and immutable scoring receipts.
5. If finalized evaluation-gold errors motivate prompt, retrieval, verifier, policy
   or matching changes, create a new exploratory version and record what was seen.
   Do not report the modified system as the same frozen evaluation or retroactively
   replace the original result. Any new confirmatory evaluation needs separate
   authorization and a defensible evaluation design.

Phase2A creates no evaluation gold, no evaluation-gold paths, no LLM implementation,
and no research performance metrics. Gold finalization and access-control setup
are future author decisions.
