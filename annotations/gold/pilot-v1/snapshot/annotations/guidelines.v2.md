# Phase 1 command-target amendment review

Use the four directories in `annotations/events-v2/`. Each is `DRAFT_UNREVIEWED`;
the earlier `annotations/events/` packets remain historical. No human gold exists yet.

1. Review the complete allowed EN evidence and the explicit lineage, then compare each
   E/N/EN retrieval bundle. Do not infer full-window absence from a top-k omission.
2. Select meaningful atomic facts, identify aliases and duplicate facts, and record
   alternative minimal support sets. Multiple address objects may share a message;
   `reported_change` and `electrical_change` may express the same numerical fact.
3. A mapped request needs m+a+static control M. A same-asset temporal statement
   additionally needs quality-valid E and its channel M, with identical opaque asset.
   A channel/asset appearing only in static metadata is not an observed fact.
4. Reject stronger claims of execution, physical effect, causation, malicious intent,
   success, or attribution. A later boolean `true` is a reported value, not proof
   that a command executed, nor a before/after state transition.
5. Review unknowns and insufficiency reasons, including missing mappings, no command,
   no later same-asset E, and retrieval truncation. Missing does not mean benign.
6. State change is optional: it is never required for event coverage or minimum
   question sufficiency. Only two valid same-channel strictly ordered unequal booleans
   can support this type. Initial/configuration values are excluded.
7. Record mechanical verifier feasibility independently of semantic usefulness.
   B0 finite consistency checks and draft inventory counts are not human judgments.

Fill the draft annotation, reviewer identity, notes and signoff only after actual
human review. Keep all existing draft outputs for provenance; do not rename an
automatically generated candidate file to gold.
