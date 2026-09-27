# r5 canonical metrics and review contract

OFFLINE CANDIDATE; NOT FROZEN. No research scores computed. Based on the author's canonical vocabulary and historical `docs/investigation_protocol.md` metric definitions. R1 is the single reviewer; human support judgments are independent of verifier decisions, not made by a second independent reviewer.

## Common units and rules

G_e: canonical unique positive full-EN gold facts for event e. H_e: separate unique guardrails. G_ev: members of G_e supportable from complete approved view v. T_ev: G_ev whose approved minimal complete support set is present in actual retrieved input. Recovered R_evr is a subset of T_ev, requiring correct content, interpretation, numeric specialization B and actual accessible support.

Primary Evidence Completeness denominator G_e is identical across E/N/EN. Report view ceiling |G_ev|/|G_e|. Distinguish G_e minus G_ev (source unavailable), G_ev minus T_ev (supportable, not retrieved), T_ev minus R_evr (retrieved, not recovered). Full-view insufficiency differs from operational withholding caused by retrieval shortfall.

Retain raw and published layers. Deduplicate true same-proposition/support aliases only; conflicting or incorrect variants remain distinct. One assertion matches at most one gold unit; one gold unit earns at most one recall credit. Guardrails never enter the positive denominator. Correct weaker qualified content is assessed at its actual strength. Pure limitations/withholds are not positive assertions; stronger assertions hidden in disclaimers still count. No invented citation credit for G0. Pending review blocks scoring. Zero denominator is NA with integer numerator/denominator and defined event/run counts.

## Canonical metric definitions

| Canonical metric / field | Numerator | Denominator and treatment |
|---|---|---|
| Evidence Completeness / Gold Fact Recall (`evidence_completeness`) | Unique correctly recovered R_evr | |G_e|, shared across views; silence/withhold does not recover positives |
| View-conditional completeness (`view_conditional_completeness`) | Recovered members of G_ev | |G_ev|; report view ceiling beside it, never replace primary denominator |
| Retrieval Recall (`retrieval_recall`) | |T_ev| | |G_ev|; independent of generated output and no score-based retrieval changes |
| Citation Precision (`citation_precision`) | Supporting visible citation pairs | All (atomic assertion, distinct cited evidence ID) pairs, including false/hidden/wrong-role/irrelevant references; duplicate IDs within assertion count once; limitations with citations are included under their actual role |
| Complete-support rate (`complete_support_rate`) | Substantive assertions whose cited set completely supports the typed proposition and interpretation | All unique substantive assertions; no citations cannot earn support credit; preserve existing requirement that cited references are valid, not merely a supporting subset with erroneous extra citations |
| Unsupported Security-Claim Rate (`unsupported_security_claim_rate`) | Unsupported substantive security assertions, including causal/intent/success/attribution/safety claims anywhere in text | All such substantive security assertions; inspect text regardless of declared claim type; no security assertions → NA, not zero |
| Numerical Accuracy (`numerical_accuracy`) | Numeric assertions with correct values/operation/unit/pair/scope | All substantive numeric assertions, independently reviewed; no numeric assertion → NA |
| Asset Consistency (`asset_consistency`) | Correct asset/channel/endpoint-role relationship assertions | All substantive assertions in that applicable category; unknown identities are not wildcards |
| Temporal Consistency (`temporal_consistency`) | Correct capture order/equality/delta/scope assertions | All substantive temporal assertions; never substitute physical actuation time |
| Required Withholding Recall (`required_withholding_recall`) | Required QUALIFY/WITHHOLD opportunities with exact appropriate action, retained scope and reason | All predeclared Q1–Q7 and guardrail opportunities whose reviewed operational action requires QUALIFY/WITHHOLD; missing/unaddressed is not success |
| Withholding Precision (`withholding_precision`) | Explicit QUALIFY/WITHHOLD decisions whose action, scope and reason are justified | All explicit such decisions, including ones outside fixed opportunities; deduplicate only reviewed identical propositions/actions; unjustified refusal lowers this value |
| Action Accuracy (`action_accuracy`) | Fixed opportunities with correct ASSERT/QUALIFY/WITHHOLD action, scope and reason | Fixed Q1–Q7 plus unique H_e opportunities; missing is incorrect; report question/guardrail strata separately |
| Q1–Q6 Substantive Coverage (`q1_q6_substantive_coverage`) | Questions meeting the frozen substantive minimum with supported retained content | Six opportunities per event/repetition; Q7, disclaimer-only and pure withholds earn no credit |
| Schema Compliance (`schema_compliance`) | Scheduled reports passing full local schema and context/link requirements | Scheduled output positions at the measured layer; failures/truncations remain zero; separate per-transport-attempt delivery diagnostics so retries do not change scientific denominators |

View ceiling (`view_ceiling`) is a denominator diagnostic, not an extra primary metric. Applicability of Numerical/Asset/Temporal fields is reviewed for every unique atomic assertion, with null only for not-applicable. For a qualified publication, assess the retained assertion; for raw stronger text, assess the raw assertion. Gold truth alone does not establish retrieved support.

## Withholding opportunities and ledger

Disjoint fixed keys are `question:Q1` through `question:Q7`, plus `guardrail:<canonical_gold_id>` for H_e. The namespaces prevent an accidental ID collision; report question and guardrail strata to expose their different units. They do not add new gold facts or aliases. The historical r4 G_e∪H_e fixed-opportunity diagnostic has a different denominator and is NOT relabeled as canonical Action Accuracy.

R1 completes a hash-bound per-output operational review ledger. Each question retains its existing human full-view answerability from sealed gold. Review records actual retrieved support, expected operational action, system action and whether retained scope/reason are correct. Guardrail propositions cannot require asserting the prohibited stronger conclusion. Explicit qualifying/withholding decisions across the whole output are reviewed even outside fixed opportunities. Each explicit fixed-slot action must agree with its decision record. Missing decisions do not count as successful withholding. Pending assessments fail closed.

Full-view answerability is never inferred from B4/V1 dispositions. The operational oracle may require withholding due to retrieval omission even when the full view is answerable. Q7's supported limitations are handled as explaining limits; its omitted substantive assertions do not inflate Q1–Q6 coverage. No new gold is generated; the four sealed pilot files already contain all three view accountings and Q judgments. Existing null retrieval accounting for excluded facts/guardrails remains null (not applicable), not a new false human judgment. Eligible positive facts require explicit Boolean retrieval accounting; missing review still blocks scoring. Other development events have no pilot gold contract and must not receive fabricated recall denominators.

## Historical names and implementation-policy findings

- `citation_validity` maps to Citation Precision. r4's policy already required role support, not ID existence, but the ledger exposed only a generic `valid` Boolean. r5 requires `exists_in_event`, `visible_in_bundle`, `supports_claim_role` and computes their conjunction; conflicting historical `valid` is rejected. This is explicit contract enforcement, not a new metric or changed gold.
- `gold_fact_recall`, `view_conditional_recall`, `question_coverage`, `security_unsupported_claim_rate`, `cited_complete_support_rate` map respectively to the canonical fields above. No duplicate primary columns.
- `supported_claim_precision`, broad `unsupported_claim_rate` and sufficiency component fields remain labeled historical diagnostics outside the canonical `metrics` result; they are not newly introduced primary metrics.
- Verifier disposition accuracy and false-withhold rate are not primary r5 metrics. Their historical r4 definitions/artifacts are retained, not silently mapped to withholding metrics with different denominators.
- Withholding, consistency and retrieval metrics appeared in earlier approved vocabulary but were missing from the r4 scoring implementation. r5 supplies them using completed independent-of-verifier human ledgers and existing accounting, not model-generated annotations.

## Aggregation, failure and RQ3

Per repetition ratio → mean within event → equal-weight event macro, with supplementary pooled micro. All three repetitions are retained. Fixed denominator failures score zero; assertion metrics require a separate review of recoverable raw text, otherwise NA with failure disclosure. Do not silently omit unsuccessful positions. Retrieval Recall remains a property of the bundle even if generation fails. D0's one deterministic artifact contributes once to micro counts.

Use approved paired scenario-stratified event bootstrap (2,000, seed 20270922). No new numerical coverage-loss margin. RQ3 jointly reports paired changes in unsupported security claims, Q1–Q6 coverage, completeness, Required Withholding Recall and Withholding Precision. Always-withhold: substantive coverage 0, security rate NA when no security assertions. No publication-filter victory based on unsupported-claim reduction alone.
