"""Seal single-reviewer pilot gold and prepare (never freeze) a protocol candidate."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import json
import hashlib
from datetime import datetime,timezone
from functools import lru_cache
from sherlock.io import ROOT,read_json,sha256
from investigation.review_phase2a import pilot_ids,summarize,support_index

OUT=ROOT/'results/investigation-freeze-v1'
GOLD=ROOT/'annotations/gold/pilot-v1'


def write_new(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')


def hashed(path):
    return {'path':str(path.relative_to(ROOT)),'sha256':sha256(path)}


def prepare():
    if GOLD.exists() or (ROOT/'configs/investigation_protocol.v1.freeze_candidate.json').exists():raise ValueError('Version exists; never overwrite gold or candidate')
    ids=pilot_ids();templates=[read_json(ROOT/'annotations/phase2a/pilots'/eid/'reviewer_annotation.json') for eid in ids]
    @lru_cache(None)
    def availability(eid,v):return set(support_index(eid,v)),set(support_index(eid,v,True))
    summary=summarize(templates,availability)
    assert summary['counts']=={'unique_reviewed_facts':54,'reviewed_rows':54,'aliases_merged':0,'pending_rows':0,'signed_off_events':4}
    positive=sum(f['epistemic_category']!='guardrail_insufficiency' for t in templates for f in t['facts'])
    assert positive==30 and all(t['review_status']=='HUMAN_REVIEWED' and t['reviewer_id']=='R1' for t in templates)
    assert all(q['review_status']=='HUMAN_REVIEWED' for t in templates for q in t['question_review'])
    write_new(OUT/'pilot_annotation_validation.json',{'status':'PASS','single_reviewer_gold':True,'positive_facts':positive,'guardrails':24,'reviewed_questions':28,
        'pending_decisions_in_pilot_annotations':0,'summary':summary,'research_metrics_computed':False})
    question_path=ROOT/'configs/investigation_questions.v1.candidate.json'
    previous=read_json(ROOT/'configs/investigation.phase1.v2.json')['questions']
    previous['Q5']='What supported capture-time relationships connect observed network activity and electrical/process observations, at episode-only or exactly mapped same-asset scope?'
    previous['Q6']='Which concrete observations or evidence combinations warrant further security investigation, and what interpretation boundary is supported?'
    write_new(question_path,{'version':'questions-v1-candidate-20260925','status':'FINAL_SEMANTIC_CANDIDATE_NOT_PROTOCOL_FREEZE','questions':previous,
        'normative_detail':hashed(ROOT/'docs/investigation_questions.v1.candidate.md'),'state_change_required':False,'classification_of_malicious_or_benign':False,
        'same_asset_requires_both_static_mapping_edges':True,'pilot_judgments_modified':False})
    evidence_components=['schemas/command_address.v2.json','schemas/evidence_id_roles.v2.json','schemas/visibility_ids.v2.json','schemas/retrieval_ids.v2.json',
        'src/evidence/schema.py','src/evidence/command_address_v2.py','src/retrieval/evidence_formatter.py','src/retrieval/evidence_formatter_v2.py',
        'src/sherlock/sanitizer.py','src/investigation/schema_v2.py','configs/evidence_contract.v1.json','configs/investigation.phase1.v2.json']
    contract_path=ROOT/'configs/investigation_export.v2.contract_snapshot.json'
    write_new(contract_path,{'version':'investigation-export-v2','snapshot_version':'export-contract-snapshot-20260925','status':'DESCRIBES_UNCHANGED_APPROVED_IMPLEMENTATION',
        'validation_entrypoint':'retrieval.evidence_formatter_v2.validate_public','note':'The complete v2 export contract is enforced by the versioned runtime validator plus component schemas; this descriptor does not invent a new full JSON Schema.',
        'record_types':['packet','message','process','command_address_observation'],'audited_command_types':[45,47,50],
        'components':[hashed(ROOT/p) for p in evidence_components]})
    rules={'evidence_id':'exact','asset_id':'exact','channel_id':'exact','claim_type':'exact_literal','command_asdu_type':'exact',
        'cause_of_transmission':'exact','state_boolean':'exact','unit':'exact','temporal_ordering':'exact_stored_capture_timestamps','temporal_scope':'exact'}
    matching_path=ROOT/'configs/investigation_matching.v1.candidate.json'
    unit_names=['AMPERE','PER_UNIT','WATT','VAR','PERCENT']
    write_new(matching_path,{'version':'matching-v1-candidate-20260925','status':'NON_NUMERIC_RULES_READY_NUMERIC_APPROVAL_PENDING','exact_rules':rules,
        'formula':'abs(pred-reference) <= max(atol, rtol * abs(reference))','active_numeric_profile':None,
        'numeric_profiles':{'A_recommended_typed_fidelity':{'author_approval':'PENDING','atol':{u:0 for u in unit_names},'rtol':{u:5e-8 for u in unit_names},
            'rationale':'Eight-significant-digit rendering bound; exact zero avoids erasing tiny observed nonzero WATT/VAR values; not sensor uncertainty.'},
            'B_six_decimal_compatibility':{'author_approval':'PENDING','atol':{u:5e-7 for u in unit_names},'rtol':{u:5e-8 for u in unit_names},
            'rationale':'Half a unit at six decimal places; less strict for small quantities; retain zero/sign gates and scientific notation near zero.'}},
        'percent_unit':'percentage points; baseline zero unavailable; no inferred denominator floor',
        'duration_rendering':{'unit':'SECOND','atol_proposed':5e-7,'rtol_proposed':0,'author_approval':'PENDING','ordering_tolerance':0},
        'unsupported_units':'PENDING_SEPARATE_APPROVAL_NO_FALLBACK','natural_language_similarity_is_correctness_metric':False,
        'fact_key_dedup_does_not_override_type_mismatch':True,'specification':hashed(ROOT/'docs/investigation_matching.v1.candidate.md'),
        'empirical_basis':hashed(OUT/'numeric_precision.pilots.json')})
    model_path=ROOT/'configs/investigation_model.v1.pending.json'
    write_new(model_path,{'status':'PENDING_AUTHOR_SELECTION_NO_API_AUTHORIZATION','provider':None,'exact_model_snapshot_version':None,
        'temperature':None,'seed':None,'seed_supported':None,'max_input_tokens':None,'max_output_tokens':None,
        'evidence_serialization_budget':{'existing_record_caps':{'N':{'N':64,'E':0},'EN':{'N':32,'E':32}},'existing_compact_json_bytes':48000,
            'final_input_token_budget':None,'tokenizer_name_version':None,'final_model_fit_status':'PENDING'},
        'prompt_version':None,'prompt_hash':None,'prompt_files':None,'generation_repetitions':None,'transport_retry_policy':None,'approved_cost_budget':None,
        'shared_by':['B1','B2','B3','B4_LLM_component'],'B4_uses_exact_B3_output_replay':True})
    # Snapshot the original annotation context AND the prospective policies separately.
    roles={
        'annotation_guidelines':['annotations/phase2a/REVIEWER_INSTRUCTIONS.md','annotations/guidelines.v2.md'],
        'claim_ontology_schema':['schemas/investigation_claim.v2.json'],
        'claim_support_policy':['docs/claim_support_policy_v2.md'],
        'fact_key_policy':['docs/investigation_fact_keys.phase2a.proposed.md','src/investigation/fact_keys_phase2a.py'],
        'annotation_time_matching_policy':['docs/investigation_matching.phase2a.proposed.md'],
        'prospective_matching_candidate':['docs/investigation_matching.v1.candidate.md','configs/investigation_matching.v1.candidate.json'],
        'annotation_time_question_definitions':['configs/investigation.phase1.v2.json'],
        'prospective_question_definitions':['docs/investigation_questions.v1.candidate.md','configs/investigation_questions.v1.candidate.json'],
        'evidence_export_schema':['configs/investigation_export.v2.contract_snapshot.json',*evidence_components],
        'verification_schema':['schemas/investigation_verification.v2.json'],
        'verification_policy':['docs/claim_support_policy_v2.md','docs/investigation_verification_policy.v1.candidate.md'],
        'event_selection':['configs/investigation_events.v1.json','configs/investigation_events.v1.lock.json','configs/investigation_pilots.v1.json'],
        'gold_validation':['results/investigation-freeze-v1/pilot_annotation_validation.json']}
    copied={}
    def snapshot(relative):
        if relative not in copied:
            src=ROOT/relative;dest=GOLD/'snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(src.read_bytes())
            assert sha256(src)==sha256(dest)
            copied[relative]={'original_path':relative,'snapshot_path':str(dest.relative_to(ROOT)),'sha256':sha256(dest)}
        return copied[relative]
    bindings={role:[snapshot(p) for p in paths] for role,paths in roles.items()}
    events=[]
    for template in templates:
        eid=template['event_id'];annotation=snapshot(f'annotations/phase2a/pilots/{eid}/reviewer_annotation.json')
        sources={}
        packet=ROOT/'annotations/events-v2'/eid
        assert sha256(packet/'manifest.json')==template['source_packet_manifest_sha256']
        assert sha256(packet/'complete_allowed_evidence.json.gz')==template['full_universe_sha256']
        for name in ('manifest.json','complete_allowed_evidence.json.gz','allowed_lineage.json.gz','numerical_candidates.DRAFT.json'):
            sources[name]=snapshot(str((packet/name).relative_to(ROOT)))
        for view in ('E','N','EN'):
            for name in ('eligible.json.gz','retrieved.json','receipt.json','visibility.json'):
                relative=f'results/investigation-v2/B0/{eid}/{view}/{name}'
                sources[view+'/'+name]=snapshot(relative)
        events.append({'event_id':eid,'annotation':annotation,'reviewer_id':template['signoff']['reviewer_id'],'review_timestamp':template['signoff']['reviewed_at'],
            'annotation_schema_version':template['schema_version'],'claim_schema_version':'investigation-claim-v2','evidence_export_version':'investigation-export-v2',
            'policy_snapshot_version':'pilot-annotation-context-v1-20260925','signoff':template['signoff'],'source_evidence_hashes':sources,
            'positive_facts':sum(f['epistemic_category']!='guardrail_insufficiency' for f in template['facts']),'guardrails':6,'reviewed_questions':7})
    manifest={'version':'pilot-gold-v1','status':'FROZEN_PILOT_GOLD_SNAPSHOT','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'methodology':'single-reviewer gold','reviewer_ids':['R1'],'independent_dual_annotation':False,'adjudication_performed':False,'inter_annotator_agreement':None,
        'reviewed_annotation_bytes_modified':False,'positive_facts':30,'guardrails':24,'reviewed_question_judgments':28,'pending_reviewer_decisions':0,
        'events':events,'policy_and_schema_bindings':bindings,'files':list(copied.values()),
        'protocol_frozen':False,'policy_binding_note':'Original annotation-context policies are preserved as reviewed provenance. Prospective matching/question/verification candidates are hashed as proposals, not retroactively human-approved numeric rules. Later policy approval requires a new protocol candidate, not mutation of this gold snapshot.',
        'immutability':'Create-once versioned directory; SHA256 seals and read-only snapshot files. Changes require a new gold version; this is not a tamper-proof external WORM service.'}
    write_new(GOLD/'manifest.json',manifest)
    seal=sha256(GOLD/'manifest.json')
    with (GOLD/'manifest.sha256').open('x') as f:f.write(seal+'  manifest.json\n')
    for p in GOLD.rglob('*'):
        if p.is_file():p.chmod(0o444)
    artifacts={key:hashed(ROOT/path) for key,path in {
        'gold_manifest':'annotations/gold/pilot-v1/manifest.json','question_definitions':'configs/investigation_questions.v1.candidate.json',
        'matching_rules':'configs/investigation_matching.v1.candidate.json','claim_schema':'schemas/investigation_claim.v2.json',
        'verification_schema':'schemas/investigation_verification.v2.json','claim_support_policy':'docs/claim_support_policy_v2.md',
        'verification_policy':'docs/investigation_verification_policy.v1.candidate.md','annotation_guidelines':'annotations/phase2a/REVIEWER_INSTRUCTIONS.md',
        'fact_key_policy':'docs/investigation_fact_keys.phase2a.proposed.md','evidence_export_contract':'configs/investigation_export.v2.contract_snapshot.json',
        'event_selection':'configs/investigation_events.v1.json','retrieval_configuration':'configs/investigation.phase1.v2.json',
        'metrics':'docs/investigation_metrics.v1.candidate.md','baseline_matrix':'docs/investigation_baselines.v1.candidate.md',
        'model_placeholders':'configs/investigation_model.v1.pending.json','evaluation_isolation':'docs/investigation_gold_isolation.phase2a.md'}.items()}
    config={'version':'investigation-protocol-v1-freeze-candidate-20260925','status':'AWAITING_AUTHOR_APPROVAL_NOT_FROZEN','protocol_frozen':False,
        'supersedes_baseline_semantics_in':'configs/investigation_protocol.v1.proposed.json','pilot_gold_methodology':'single-reviewer gold',
        'llm_calls_authorized':False,'B1_B4_implementation_authorized':False,'research_metrics_computed':False,
        'artifacts':artifacts,'exact_matching_rules':rules,'numeric_tolerance_profile':None,
        'primary_baselines':[
            {'baseline':'B0','view':'EN','generation':'existing deterministic structured baseline'},
            {'baseline':'B1','view':'N','generation':'shared pending LLM','citations':'optional'},
            {'baseline':'B2','view':'EN','generation':'shared pending LLM','citations':'optional'},
            {'baseline':'B3','view':'EN','generation':'shared pending LLM','citations':'required'},
            {'baseline':'B4','view':'EN','generation':'exact B3 output replay, same LLM component','citations':'required','verifier':'deterministic; not implemented'}],
        'primary_contrasts':{'B1_vs_B2':'cross-source value under fixed total evidence budget','B2_vs_B3':'citation/grounding value','B3_vs_B4':'verification/publication value on identical B3 output'},
        'model_comparison_primary_experiments':False,'event_count':32,'planned_primary_event_baseline_cells':160,
        'evaluation_isolation':{'pilot_development_use_allowed':True,'evaluation_gold_or_results_may_tune_protocol':False,
            'post_exposure_change_requires':'new exploratory protocol version','untouched_test_claim':False,'custodian_and_access_controls':'PENDING_AUTHOR_DECISION'},
        'pending_author_decisions':[
            'Choose numeric profile A or B (or explicitly justified alternative), duration-rendering tolerance and output precision.',
            'Confirm literal exact claim-type matching versus an explicitly versioned common representation adapter; existing B0 reported_change differs from reviewed electrical_change. No facts changed.',
            'Approve final matching, Q5/Q6, metric and controlled-baseline candidate as one protocol version.',
            'Select provider/exact model snapshot, temperature/seed policy, input/output/evidence token budgets, prompt versions/hashes, repetitions, retry and cost budget.',
            'Finalize evaluation gold/version, custodian/access controls and scoring-reviewer role under single-reviewer methodology; no second reviewer or IAA claimed.',
            'Fix event-level uncertainty procedure and diagnostic reporting before evaluation inspection.',
            'Authorize later baseline implementation and validate/hash final B0–B4 serialization, prompts and verifier code before protocol freeze.'],
        'freeze_blockers':['numeric approval missing','model/prompts/token limits missing','B0 representation unresolved','baseline/verifier final code not implemented','evaluation gold/access setup pending','author freeze approval absent'],
        'future_exact_file_bindings_pending':{'prompt_files':None,'baseline_generation_implementation':None,'deterministic_verifier_implementation':None,'evaluation_gold_manifest':None,
            'reason':'No nonexistent path/hash is presented as a frozen artifact; final inventory must name and hash these before actual freeze.'}}
    write_new(ROOT/'configs/investigation_protocol.v1.freeze_candidate.json',config)
    print('Pilot gold manifest SHA256:',seal)
    print('Protocol candidate written; NOT frozen. Snapshot files:',len(copied))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true',required=True);p.parse_args();prepare()
