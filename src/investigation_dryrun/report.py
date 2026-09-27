"""Conformance accounting only; never reads gold or computes research performance."""
from collections import Counter,defaultdict
import json
from .common import ROOT,load,file_hash,digest,binding
from .tokens import summary
from .custody import development_ids,verify_access_log
from .claims import typed_support,validate_raw_support,canonical_numeric_fact
from .batch import expected_cells,cell_dir,BATCH_ID,verify_preflight,verify_completed
from .runner import RUNS,parse_experiment,delivery_validation

def distribution(xs):return summary(xs) if xs else {'n':0,'minimum':None,'median':None,'p90':None,'p95':None,'maximum':None}

def report():
    verify_preflight();states=Counter();per=defaultdict(Counter);attempts=[];evidence=[];cells=[];replays=[];diagnostics=[];accessed=set();chains=[]
    for eid,b,rep in expected_cells():
        p=cell_dir((eid,b,rep))
        if not (p/'completed.json').exists():continue
        m=verify_completed((eid,b,rep));states[m['status']]+=1;per[b][m['status']]+=1;evidence.append(m['actual_evidence_tokens'])
        cells.append({'event_id':eid,'baseline':b,'repetition':rep,'status':m['status'],'manifest':binding(p/'completed.json')})
        attempts.extend(dict(a,event_id=eid,baseline=b,repetition=rep) for a in m['attempts'])
        chains.append(verify_access_log(p/'access.jsonl'))
        for line in (p/'access.jsonl').read_text().splitlines():
            row=json.loads(line)
            if row['action'].startswith('READ'):accessed.add(row['event_id'])
        if m['status'] not in ('DELIVERED','DELIVERED_SCHEMA_INVALID'):continue
        exp=parse_experiment((p/'output.raw.json').read_bytes());bundle=load(p/'bundle.json')
        available={r['evidence_id'] for r in bundle['entries']}|{r['evidence_id'] for r in bundle['metadata'].values()}|set(bundle['control_metadata'])|{bundle['scope']['evidence_id']}
        diagnostic=Counter();reasons=Counter()
        for claim in exp['claims']:
            diagnostic['claims']+=1
            if not isinstance(claim,dict):diagnostic['malformed_claims']+=1;continue
            citations=claim.get('evidence_ids',[])
            if isinstance(citations,list) and all(isinstance(x,str) for x in citations):
                diagnostic['unique_citation_edges']+=len(set(citations));diagnostic['invisible_citation_edges']+=sum(x not in available for x in set(citations))
            else:diagnostic['unparseable_citation_arrays']+=1
            try:
                typed_support(claim,bundle);diagnostic['typed_support_pass']+=1
                validate_raw_support(claim,bundle,require_citations=b=='B3');diagnostic['finite_text_and_support_pass']+=1
                if claim['claim_type'] in ('reported_change','electrical_change'):
                    canonical_numeric_fact(claim,bundle,require_citations=b=='B3');diagnostic['canonical_numeric_projection_pass']+=1
                if claim['claim_type']=='asset_relationship' and claim['payload']['relation']=='observation_channel_maps_to_asset':diagnostic['channel_asset_mapping_pass']+=1
            except (ValueError,KeyError,TypeError,StopIteration) as err:
                reasons[str(err)]+=1;diagnostic['not_supported_or_not_checkable']+=1
        diagnostics.append({'event_id':eid,'baseline':b,'repetition':rep,'counts':dict(diagnostic),'reasons':dict(reasons)})
    for eid in development_ids():
        for rep in (1,2,3):
            p=RUNS/BATCH_ID/eid/'B4'/f'rep-{rep}'/'replay.json'
            if p.exists():
                r=load(p);m=verify_completed((eid,'B3',rep));identity=r['B3_input_sha256']==m.get('output_sha256')
                replays.append({'event_id':eid,'repetition':rep,'status':r['status'],'input_identity':identity,'stored_output_present':'output_sha256' in m,'llm_calls':r['llm_calls'],'dispositions':dict(Counter(x['disposition'] for x in r['dispositions'])),'artifact':binding(p)})
    usages=[a['provider_metadata']['usage'] for a in attempts if a.get('provider_metadata',{}).get('usage') is not None]
    truncations=[{k:a[k] for k in ('event_id','baseline','repetition','attempt','provider_metadata')} for a in attempts if (a.get('provider_metadata',{}).get('incomplete_details') or {}).get('reason')=='max_output_tokens' and a['provider_metadata'].get('status')=='incomplete']
    combined=Counter();reasons=Counter()
    for d in diagnostics:combined.update(d['counts']);reasons.update(d['reasons'])
    return {'version':'development-dryrun-conformance-v1','scope':'DEVELOPMENT ONLY; no research performance or human accuracy scores','protocol_frozen':False,'planned_generation_cells':144,'completed_generation_cells':len(cells),'missing_generation_cells':144-len(cells),'generation_statuses':dict(states),'statuses_by_baseline':dict(per),'schema_valid_complete_outputs':states['DELIVERED'],'schema_invalid_recoverable_outputs':states['DELIVERED_SCHEMA_INVALID'],'provider_attempts':len(attempts),'retry_attempts':sum(a['attempt']>1 for a in attempts),'retry_reasons':dict(Counter(a.get('reason') for a in attempts if a.get('will_retry'))),'provider_models':dict(Counter(a['provider_metadata'].get('model') for a in attempts if a.get('provider_metadata'))),'provider_statuses':dict(Counter(a['provider_metadata'].get('status') for a in attempts if a.get('provider_metadata'))),'provider_response_ids':[a['provider_metadata'].get('id') for a in attempts if a.get('provider_metadata')],'attempts_without_usage':len(attempts)-len(usages),'usage_all_attempts':{k:{'distribution':distribution([u[k] for u in usages if type(u.get(k)) is int]),'total':sum(u.get(k,0) for u in usages)} for k in ('input_tokens','output_tokens','total_tokens')},'evidence_tokens_per_cell':distribution(evidence),'truncation_count':len(truncations),'truncations':truncations,'output_limit_recommendation':'PROPOSE_8192_REQUIRES_AUTHOR_APPROVAL_NO_AUTOMATIC_INCREASE' if truncations else 'RETAIN_4096_UNLESS_COMPLETED_RUN_PROVIDES_TRUNCATION_EVIDENCE','B4_statuses':dict(Counter(r['status'] for r in replays)),'B4_replay_records':len(replays),'B4_identity_all_pass':all(r['input_identity'] for r in replays) if replays else None,'B4_actual_stored_output_identity_checks':sum(r['stored_output_present'] and r['input_identity'] for r in replays),'B4_provider_calls':sum(r['llm_calls'] for r in replays),'accessed_event_ids':sorted(accessed),'evaluation_evidence_accesses':len(accessed-set(development_ids())),'evaluation_gold_read':False,'access_log_chains_checked':len(chains),'conformance_diagnostic_counts':dict(combined),'model_output_or_not_checkable_reasons':dict(reasons),'diagnostic_limit':'Finite verifier failures are not a human oracle: free text and Q6 may be NOT_CHECKABLE. These are not Supported Claim Precision, recall, or verifier accuracy. No gold was loaded.','cells':cells,'B4_replays':replays,'per_output_diagnostics':diagnostics}
