# Proposed system-vs-gold matching policy

Draft only. No matcher or research scoring is implemented in Phase 2A. Final
tolerances, question rules, metric denominators and adjudication need approval.

1. **Version/event/view gate.** Match only within the frozen event, evidence version,
   view, policy and gold version. Check opaque reference namespaces and exact IDs
   against full eligible evidence, then against the actual production bundle.
   A known full-universe ID missing from the bundle is not an accessible citation.
   Distinguish unknown ID, wrong-event ID, hidden-view ID, unavailable retrieval,
   missing ancestry and insufficient joint support.
2. **Typed proposition and reference roles.** Parse and validate the claimed type,
   operation, direction, scope and exact supporting roles. At least one complete
   human-approved alternative minimal support set must be satisfied for cited
   complete support. Mere overlap with one ID is insufficient. Numeric e IDs cannot
   be replaced by a/m/p IDs; static M alone does not prove an observed event.
3. **Numerical checks.** First require exact observation IDs, channel, quantity,
   pair direction, unit and quality eligibility. Compare finite numbers using
   `abs(pred-gold) <= max(abs_tolerance[unit], rel_tolerance[unit]*abs(gold))`.
   Both tolerances are explicitly PENDING per unit and operation; scoring must fail
   closed until approved. Percent change uses the approved absolute-baseline formula;
   zero baseline is unavailable, never zero percent. Booleans are exact, not numeric
   0/1 tolerances. No new unit conversion or omitted-quality tolerance is implied.
4. **Asset checks.** Exact opaque asset identity plus correct mapping roles.
   Strengthened request requires the exact visible m→a→control M chain. Same-asset
   N/E additionally requires the E channel M; both assets must agree. Null is not a
   wildcard. Endpoint identity does not automatically establish an asset identity.
5. **Temporal checks.** Match endpoint identities, direction and relation exactly.
   Recompute order/delta from capture timestamps. Same timestamp is not precedes;
   same_capture_time is not physical simultaneity. Delta rendering tolerance is
   PENDING; it must never change strict order/equality decisions. Episode-only and
   same_observed_asset are distinct scopes. No matching rule upgrades ordering to
   execution or causation; no true-measurement-time assumption.
6. **Fact-key equivalence.** Use exact canonical proposed keys or explicit human
   alias mappings within the event to propose a match; then validate the entire
   typed content and supporting evidence. A matching key cannot excuse a wrong
   value, missing asset edge, stronger interpretation or malformed citation. One
   gold fact counts at most once. Each atomic system proposition matches at most
   one gold fact; split multi-proposition text before judging. Difference vs percent
   may be alternate gold renderings only when adjudicated; reported_change and
   electrical_change for one underlying pair/quantity never count twice.
7. **Free-text semantic review.** A human reviews stronger interpretations in all
   raw and final text, including text hidden under another claim_type. A correct
   typed payload cannot legalize execution, causal, intent, attribution, compromise
   or safe-from-absence language. Weak review_required needs an explicit human
   determination of relevance. No embedding/edit-distance/generic similarity score
   is the main correctness criterion. Human disagreements use the pending reviewer
   and adjudication policy, independently of future verifier statuses.
8. **Availability versus recovery.** Report eligible_in_view,
   retrieved_in_production_bundle and recovered_by_system separately. Full-view
   answerability comes from gold, not production top-k. Recovery remains unscored in
   Phase2A. Later B1 content correctness without citations may be independently
   judged by humans but never earns cited complete-support credit by filling in
   citations on its behalf. Under-citation is a system defect, not proof the fact
   was unavailable. No factual support inferred from absence in top-k.
9. **Question and failure handling.** Human Q1–Q7 answerability is distinct from
   fact-level matching; Q7 guardrails do not create substantive Q1–Q6 coverage.
   Optional reported_state_change is never a minimum requirement. Preserve invalid,
   truncated and failed generations as attempts in the future approved denominators.
   Empty denominators produce NA with counts, never a perfect score. No performance
   metrics are computed now; metric definitions are a proposal in the freeze config.

Candidate numeric/time tolerances, free-text adjudication, alias treatment across
alternative support sets, and minimum Q5/Q6 requirements must be approved before
any scoring. Final evaluation-gold errors must not tune this policy within the same
frozen evaluation version; see the isolation rule.
