"""Finite JSON Schema contracts for evaluator-only inputs and report products.

These extend the evaluator ledger, never the model-facing claim schema.
"""
import hashlib
import json
from investigation_dryrun.schema import check

VERSION = 'chapter5-offline-v1'
CELLS = ('G0', 'G1-E', 'G1-N', 'G1-EN', 'V1-EN')
VIEWS = {'D0':'EN','G0':'EN','G1-E':'E','G1-N':'N','G1-EN':'EN','V1-EN':'EN'}
METRICS = ('evidence_completeness','view_conditional_completeness','retrieval_recall',
 'citation_precision','complete_support_rate','unsupported_security_claim_rate',
 'numerical_consistency','asset_consistency','temporal_consistency',
 'q1_q6_substantive_coverage','required_withholding_recall','withholding_precision','schema_compliance')
TABLE_ROWS = {
 'table4': list(METRICS[:3])+['q1_q6_substantive_coverage','citation_precision','complete_support_rate'],
 'table5': ['citation_precision','complete_support_rate','unsupported_security_claim_rate','evidence_completeness','q1_q6_substantive_coverage','numerical_consistency','asset_consistency','temporal_consistency'],
 'table6': ['unsupported_security_claim_rate','evidence_completeness','q1_q6_substantive_coverage','citation_precision','complete_support_rate','numerical_consistency','asset_consistency','temporal_consistency','required_withholding_recall','withholding_precision']}
ALIASES = {'gold_fact_recall':'evidence_completeness','citation_validity':'citation_precision',
 'numerical_accuracy':'numerical_consistency','view_conditional_recall':'view_conditional_completeness',
 'question_coverage':'q1_q6_substantive_coverage','security_unsupported_claim_rate':'unsupported_security_claim_rate',
 'cited_complete_support_rate':'complete_support_rate'}

def dumps(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def digest(x): return hashlib.sha256(dumps(x).encode()).hexdigest()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def obj(**properties): return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
def array(items, minimum=0, unique=False): return {'type':'array','items':items,'minItems':minimum,'uniqueItems':unique}
def enum(*values): return {'enum':list(values)}
def nullable(x): return {'anyOf':[x,{'type':'null'}]}
S={'type':'string','minLength':1}; TEXT={'type':'string'}; B={'type':'boolean'}; N={'type':'integer','minimum':0}
HASH={'type':'string','pattern':'^[0-9a-f]{64}$'}
STRINGS=array(S, unique=True); QUESTIONS=array(enum(*(f'Q{i}' for i in range(1,8))), unique=True)
STAMP={'type':'string','pattern':r'^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$'}
SUPPORT_SETS=array(array(S,1,True),unique=True)
REVIEW=obj(reviewer_id=enum('R1'),reviewed_at=STAMP,review_status=enum('HUMAN_REVIEWED'),notes=TEXT)
SUPPORT=obj(supportable=B,acceptable_support_sets=SUPPORT_SETS,rationale=S)
FACT=obj(gold_id=S,fact_key=S,raw_claim_type=S,canonical_representation=S,statement=S,
 fields={'type':'object'},views=obj(E=SUPPORT,N=SUPPORT,EN=SUPPORT),question_ids=QUESTIONS,
 allowed_interpretation=S,prohibited_interpretations=STRINGS)
OPPORTUNITY=obj(event_id=S,opportunity_id=S,semantic_scope=S,conclusion_category=S,
 evidence_requirement=S,required_actions=obj(E=enum('allow','qualify','withhold','not_applicable'),
 N=enum('allow','qualify','withhold','not_applicable'),EN=enum('allow','qualify','withhold','not_applicable')),
 reason=S,question_ids=QUESTIONS)
GOLD=obj(version=enum(VERSION),event_id=S,annotation_version=S,policy_sha256=HASH,
 committed_before_output_review=enum(True),commitment_sha256=HASH,review=REVIEW,
 source_evidence_hashes=array(obj(evidence_id=S,sha256=HASH,views=array(enum('E','N','EN'),1,True)),1),
 positive_facts=array(FACT),aliases=array(obj(alias_id=S,canonical_gold_id=S,rationale=S,review=REVIEW)),
 opportunities=array(OPPORTUNITY),temporal_relationships=STRINGS,asset_relationships=STRINGS,
 security_relevance_judgments=STRINGS,unsupported_conclusions=STRINGS,unresolved_conclusions=STRINGS)
SPAN=obj(pointer=S,start=N,end=N,text=TEXT)
CITATION=obj(evidence_id=S,assigned_role=S,exists=B,visible=B,role_supported=B,reason=S)
NUMERIC=obj(cited_values=B,transformation=B,unit=B,channel_asset_scope=B,approved_tolerance=B)
ASSET=obj(observation_identity=B,approved_mapping=B,scope=B)
TEMPORAL=obj(exact_timestamps=B,exact_ordering=B,scope=B,required_mappings=B)
OVERCLAIMS=obj(causal=B,malicious_intent=B,command_execution=B,successful_compromise=B,attribution=B)
ASSERTION=obj(assertion_id=S,source=SPAN,original_claim_ids=STRINGS,raw_claim_type=nullable(S),
 substantive=B,supported=B,security_sensitive=B,overclaims=OVERCLAIMS,q6_relevance=nullable(B),
 matched_gold_ids=STRINGS,matching_policy_sha256=HASH,matching_reason=S,
 required_support_sets=SUPPORT_SETS,citations=array(CITATION),cited_complete_support=B,
 numerical=nullable(NUMERIC),asset=nullable(ASSET),temporal=nullable(TEMPORAL),
 duplicate_of=nullable(S),duplicate_rationale=TEXT,reviewer_notes=TEXT)
ACTION=obj(action_id=S,source=SPAN,original_claim_ids=STRINGS,action=enum('qualify','withhold'),
 opportunity_id=nullable(S),action_correct=B,scope_correct=B,reason_correct=B,
 duplicate_of=nullable(S),duplicate_rationale=TEXT,reviewer_notes=TEXT)
LEDGER=obj(version=enum(VERSION),event_id=S,cell_id=enum(*VIEWS),repetition=enum(0,1,2,3),
 output_stage=enum('RAW_GENERATED','VERIFIED_PUBLISHED','DETERMINISTIC_REFERENCE'),
 raw_output_sha256=HASH,stage_artifact_sha256=HASH,bundle_sha256=HASH,gold_sha256=HASH,
 delivery=enum('VALID','INVALID_PROVIDER_DELIVERY'),delivery_reason=S,
 delivery_receipt=obj(event_id=S,cell_id=S,repetition=N,status=S,termination_reason=nullable(S),source_record_sha256=HASH),
 schema_compliant=B,review=REVIEW,all_text_reviewed=enum(True),
 reviewed_surfaces=array(obj(pointer=S,text=TEXT,assertion_ids=STRINGS,nonassertive_reason=TEXT)),
 assertions=array(ASSERTION),questions=array(obj(question_id=enum(*(f'Q{i}' for i in range(1,8))),
 adequate_assertion_ids=STRINGS,adequate=B,reason=S),7),actions=array(ACTION))
RATIO=obj(numerator=N,denominator=N,value=nullable({'type':'number','minimum':0,'maximum':1}))
ESTIMATE=obj(mean=nullable({'type':'number'}),defined_event_count=N,undefined_event_ids=STRINGS,
 population_event_count=N)
CONTRAST=obj(direction=S,mean_difference=nullable({'type':'number'}),ci95=array(nullable({'type':'number'})),
 paired_event_count=N,omitted_event_ids=STRINGS,stratum_counts={'type':'object'},singleton_strata=STRINGS,
 structural_not_applicable=B,display=TEXT)
TABLE_SCHEMAS={}
for table,rows in TABLE_ROWS.items():
 conditions={'table4':['G1-E','G1-N','G1-EN'],'table5':['G0','G1-EN'],'table6':['G1-EN','V1-EN']}[table]
 comparisons={'table4':['EN_minus_E','EN_minus_N'],'table5':['EN_minus_G0'],'table6':['V1_minus_G1']}[table]
 TABLE_SCHEMAS[table]=array(obj(metric=enum(*rows),interpretation=S,
  conditions=obj(**{c:ESTIMATE for c in conditions}),contrasts=obj(**{c:CONTRAST for c in comparisons})),len(rows))
COUNT_FIELDS=('security_sensitive_assertions','citation_pairs','numerical_assertions','asset_assertions',
 'temporal_assertions','required_withholding_opportunities','explicit_qualify_withhold_actions',
 'defined_uscr_denominators','defined_numerical_denominators','defined_withholding_precision_denominators')
TABLE_SCHEMAS['table7']=array(obj(condition=enum(*CELLS),**{f:N for f in COUNT_FIELDS},
 planned_runs=N,valid_delivery_runs=N,invalid_delivery_runs=N,defined_event_counts=obj(
 uscr=N,numerical=N,withholding_precision=N)),5)
TABLE_SCHEMAS['figure2']=array(obj(event_id=S,scenario_stratum=S,condition=enum(*CELLS),coverage=nullable({'type':'number'}),
 uscr=nullable({'type':'number'}),uscr_defined=B,security_assertion_count=N,
 coverage_defined_repetitions=N,uscr_defined_repetitions=N))
FUNNEL=obj(event_id=S,view=enum('E','N','EN'),full_gold_count=N,supportable_in_view_count=N,
 complete_support_retrieved_count=N,correctly_reconstructed_count=nullable({'type':'number'}),
 reconstructed_by_repetition=array(nullable(N)),n_defined_repetitions=N,
 unavailable_in_view=N,available_not_retrieved=N,retrieved_not_reconstructed=nullable({'type':'number'}))
TABLE_SCHEMAS['rq1_funnel']=array(FUNNEL)
SCHEMAS={'gold':GOLD,'review_ledger':LEDGER,**TABLE_SCHEMAS}

def validate(name,data):
 check(data,SCHEMAS[name]);return data

def annotation_template():
 """Blank design only: no evaluation IDs, facts, evidence, or inferred judgments."""
 return {'status':'BLANK_R1_WORKSHEET_NOT_GOLD','reviewer_id':'R1','methodology':'single-reviewer gold',
 'event_id':None,'positive_facts':[],'aliases':[],'opportunities':[],
 'temporal_relationships':[],'asset_relationships':[],'security_relevance_judgments':[],
 'unsupported_conclusions':[],'unresolved_conclusions':[],'source_evidence_hashes':[],
 'annotation_version':None,'policy_sha256':None,'commitment_sha256':None,'reviewed_at':None}
