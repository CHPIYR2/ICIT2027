"""Paper-facing definitions and offline readiness checks, not execution authority."""
from .contracts import METRICS,ALIASES

DEFINITIONS={
'evidence_completeness':('unique correctly recovered positive full-EN facts','unique G_e positive facts common to every view'),
'view_conditional_completeness':('unique correctly recovered G_ev facts','unique G_ev facts fixed from complete view before retrieval/output'),
'retrieval_recall':('G_ev facts with at least one complete acceptable support set in actual bundle','unique G_ev facts'),
'citation_precision':('visible existing atomic assertion/evidence ID pairs supporting assigned role','all cited atomic assertion/evidence ID pairs'),
'complete_support_rate':('substantive assertions with complete required support in generated cited set','all substantive assertions'),
'unsupported_security_claim_rate':('unsupported security-sensitive substantive assertions judged from actual text','all security-sensitive substantive assertions'),
'numerical_consistency':('numerical assertions passing cited-value, transformation, unit, channel/asset scope and approved tolerance checks','all numerical substantive assertions'),
'asset_consistency':('asset assertions passing observation identity, approved mapping and scope checks','all asset substantive assertions'),
 'temporal_consistency':('temporal assertions passing exact timestamps, ordering, scope and required mapping checks','all temporal substantive assertions'),
'q1_q6_substantive_coverage':('Q1-Q6 each having at least one adequately supported substantive assertion; Q6 requires human relevance judgment','six questions; Q7 excluded'),
'required_withholding_recall':('fixed required opportunities with explicit correct action AND scope AND reason','all predeclared view-applicable qualify/withhold opportunities in H_e'),
'withholding_precision':('human-confirmed explicit qualify/withhold actions with correct action AND scope AND reason','all explicit qualify/withhold actions, including actions outside H_e'),
'schema_compliance':('delivered outputs passing frozen structural/local conformance checks','delivered assessed outputs; diagnostic only')}

def metric_contract():
 return {'version':'chapter5-offline-v1','status':'CANDIDATE_NOT_FROZEN','metric_aliases':ALIASES,
 'metrics':{m:{'numerator':DEFINITIONS[m][0],'denominator':DEFINITIONS[m][1],
 'zero_denominator':'NA, never 0 or 1','aggregation':'repetition ratios, mean of defined repetitions per event, mean of defined events; pooled counts supplementary',
 'alias_policy':'Only R1-approved direct semantic aliases; collapse once; conflicting support/consistency variants cannot collapse; raw types preserved',
 'guardrail_policy':'H_e disjoint from positive G_e; only RWR fixed opportunity denominator; explicit actions feed WP',
 'withheld_policy':'No positive fact or substantive coverage credit for pure withholding; explicit correct actions can earn RWR/WP',
 'unusable_output_policy':'Valid delivery with no usable substantive assertions: zero fixed EC/VCC/Coverage/RWR opportunities, NA claim-conditioned metrics; retrieval independent. Invalid provider delivery excluded, reason and opportunity counts retained',
 'direction':'lower' if m=='unsupported_security_claim_rate' else 'diagnostic' if m=='schema_compliance' else 'higher'} for m in METRICS},
 'primary_by_RQ':{'RQ1':['evidence_completeness'],'RQ2':['citation_precision','complete_support_rate','unsupported_security_claim_rate'],'RQ3':['unsupported_security_claim_rate']},
 'primary_companions':{'RQ1':['q1_q6_substantive_coverage'],'RQ3':['q1_q6_substantive_coverage']},
 'rq3_withholding_table_policy':'RWR/WP shown for V1 publication; raw comparison structurally not applicable (em dash). Raw explicit decisions may still be scored and counted descriptively.',
 'rq3_success':'Joint USCR, Coverage and Completeness interpretation; no post-hoc loss threshold',
 'supportability':'G_ev before retrieval/output; G_evr from complete support sets intersecting actual visibility; no hidden repair',
 'duplicates':'Gold aliases and output duplicates are separate reviewed equivalence relations; same evidence ID repeated within an atomic assertion counts one pair. Inherited r5 reviewed proposition duplicate handling retained.',
 'required_withholding_dedup':'One numerator credit per fixed opportunity, even if several explicit actions address it. All distinct explicit actions remain in WP.',
 'pair_population':'Only events with defined event means in both conditions; retain/disclose omitted IDs, counts, strata, full planned population and NA slots',
 'provider_exclusion':'Receipt-driven only; schema/citation/quality failure cannot exclude a delivered recoverable response. Unclassified implementation/model/rate blockers require author review.',
 'natural_language_similarity_primary':False,'no_new_primary_metrics':True}

DISAGREEMENTS=[
 {'id':'D1','historical':'r5 scorer and stats require_development; four-pilot gold loader','resolution':'New pure-data scorer, metadata-only final manifests; legacy guards unchanged'},
 {'id':'D2','historical':'numerical_accuracy / Numerical Accuracy','resolution':'Canonical numerical_consistency / Numerical Consistency; alias only, same correctness requirements'},
 {'id':'D3','historical':'r5 metrics config RQ2 primary list omits USCR; RQ3 groups joint tradeoff metrics','resolution':'Chapter-5/user primary and companion labels authoritative; no formula-driven result tuning'},
 {'id':'D4','historical':'r5 withholding opportunity set automatically unions question:Q1-Q7 and guardrails','resolution':'Explicit precommitted H_e controls RWR, no automatic seven-question addition; question associations remain metadata'},
 {'id':'D5','historical':'Human ledger lacks explicit stage, exhaustive text surfaces, separate overclaim flags, required support sets and complete-view evidence inventory','resolution':'New evaluator-only schema; byte-bound raw/published review and R1 completeness attestation'},
 {'id':'D6','historical':'r5 aggregate attempts all contrasts for all metrics including raw RWR/WP','resolution':'Table6 RWR/WP raw delta/CI structurally not applicable; no invented raw comparison'},
 {'id':'D7','historical':'D0 requires three aligned references in r5 stats','resolution':'One D0 execution/row per event, no repeated micro opportunities'},
 {'id':'D8','historical':'r5 has no full Tables4-7/Figure2/funnel export','resolution':'Strict machine-readable schemas and synthetic end-to-end exports'},
 {'id':'D9','historical':'r5 failure_scores emits fixed zeros broadly; Chapter5 exempts invalid provider delivery','resolution':'Receipt-driven invalid provider deliveries NA/excluded and explicitly reported; valid empty/unusable outputs keep fixed zeros; no quality-based exclusion'}]

def custody_checklist():
 fields=['author_R1_custodian','single_reviewer_disclosure','OS_account_ACL_verified',
 'generation_identity_denied_gold_truth_review_ledgers','scoring_identity_least_privilege',
 'evaluation_access_logging_verified','gold_manifest_version_hash_committed',
 'generation_manifest_committed','scenario_strata_commitment_evaluator_only',
 'run_receipt_and_gold_commitment_loader_authenticated','final_output_ingestion_adapter_reviewed',
 'preexisting_layout_migration_acknowledged','explicit_protocol_freeze','separate_evaluation_run_authorization']
 return {'status':'NOT_PROVISIONED_NOT_FROZEN','custodian':'Author/R1','model_calls':0,
 'checks':[{'check':k,'status':'PENDING','evidence':None} for k in fields],
 'positive_negative_ACL_tests':['Generation identity can read only approved evidence/config/prompt/schema inputs',
 'Generation identity read attempts against gold/truth/review ledgers fail under OS/account ACLs',
 'Scoring identity can read only committed gold, stored outputs, retrieved receipts and R1 review ledgers',
 'Attempted/allowed/denied access produces immutable actor/path/time/decision logs'],
 'generation_allowlist':['event_id','cell_id','view','repetition','approved prompt bytes','approved compiled schema',
 'retrieved evidence and approved view metadata','model/decoding parameters'],
 'generation_denylist':['gold','truth','attack labels','scenario strata labels','human review ledgers','metric scores'],
 'loader_requirements':['Match selected 32 event IDs and all generation/replay positions',
 'Authenticate output, bundle, delivery receipt and ledger hashes against committed manifests before arithmetic',
 'Verify gold commitment timestamp precedes output review; R1 review complete; no pending decisions',
 'Verify identical raw G1-EN source for every V1-EN position; no regeneration or invented missing content',
 'Mark synthetic/dev inputs ineligible for final paper tables',
 'Bind final scoring code/schema hashes at freeze; do not permit post-result edits'],
 'no_access_provisioned_this_turn':True}
