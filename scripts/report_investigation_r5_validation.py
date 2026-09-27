"""Audit only the authorized development run; summarize usage and post-test integrity."""
import collections,json,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from investigation_dryrun.common import load,file_hash,binding,digest,create_json,utc
from investigation_r5.acceptance import assess
from investigation_r5.core import read_bundle
from investigation_r5.runner import build_request
from check_investigation_r5_validation import integrity
from report_investigation_api_usage import cost,RATES,SOURCE
OUT=ROOT/'results/investigation-r5-validation'

def report():
 state=load(OUT/'execution.finished.json');pre=load(OUT/'preflight.json');plan=load(ROOT/'results/investigation-r5/validation_manifest.json');post=load(OUT/'post-execution.tests.json');checks=integrity()
 for ref in pre['protected_files']:assert file_hash(ROOT/ref['path'])==ref['sha256'],ref['path']
 assert post['status']=='PASS'
 planned={p['position_id']:p for p in plan['positions']};rows=[];attempts=[];replays=[];acceptance_rows=[];ids=set();totals=collections.Counter();prices=[];usage_rows=[];unknown=[]
 counts={c:collections.Counter(planned=n) for c,n in plan['counts'].items()}
 for position_id in state['finished_positions']:
  p=planned[position_id];base=OUT/'runs'/state['run_id']/p['event_id']/p['cell_id']/f"rep-{p['repetition']}";m=load(base/'completed.json');assert m['position_id']==position_id
  b,r=read_bundle(p['event_id'],p['view']);q=build_request(p['event_id'],p['cell_id'],b,r)
  assert load(base/'request.json')==q and digest(q)==p['request_sha256']==m['request_sha256'];assert load(base/'bundle.json')==b and load(base/'receipt.json')==r
  if m.get('output_sha256'):assert file_hash(base/'output.raw.json')==m['output_sha256']
  s=counts[p['cell_id']];s['executed']+=1;s[m['status']]+=1;s['normal_complete_outputs']+=m['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID');s['schema_valid_outputs']+=m['schema_valid'];s['schema_and_visibility_valid']+=m.get('schema_and_visibility_valid',False);s['output_cap_truncations']+=m['capacity_hard_stop'];s['transport_attempts']+=len(m['attempts'])
  for a in m['attempts']:
   ap=base/f"attempt-{a['attempt']}"/'attempt.json';assert load(ap)==a and a['request_sha256']==p['request_sha256']
   if a.get('response_sha256'):assert file_hash(ap.parent/'response.raw')==a['response_sha256']
   attempts.append({'position_id':position_id,'cell_id':p['cell_id'],**a});md=a.get('provider_metadata') or {};u=md.get('usage')
   if md.get('status') in ('completed','incomplete'):s['provider_delivered_responses']+=1
   if u:
    response_id=md.get('id');assert response_id and response_id not in ids;ids.add(response_id)
    cached=(u.get('input_tokens_details') or {}).get('cached_tokens');values={'input_tokens':u.get('input_tokens'),'cached_input_tokens':cached,'output_tokens':u.get('output_tokens'),'total_tokens':u.get('total_tokens')}
    if all(type(values[k]) is int for k in ('input_tokens','output_tokens','total_tokens')):assert values['total_tokens']==values['input_tokens']+values['output_tokens']
    price=cost(u,md.get('service_tier')) if md.get('model')=='gpt-4.1-2025-04-14' else None
    if price is not None:prices.append(price)
    for k,v in values.items():
     if type(v) is int:totals[k]+=v
    usage_rows.append({'attempt':binding(ap),'response_id':response_id,'model':md.get('model'),'service_tier':md.get('service_tier'),'usage':values,'known_list_price_USD':str(price) if price is not None else None})
   else:unknown.append({'attempt':binding(ap),'HTTP_status':a.get('HTTP_status'),'reason':a.get('reason'),'usage':None,'cost':None})
  s['delivered_positions']+=any((a.get('provider_metadata') or {}).get('status') in ('completed','incomplete') for a in m['attempts'])
  s['reference_visibility_valid_complete_outputs']+=m['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID') and m['reference_visibility_valid']
  s['input_view_and_budget_checks_passed']+=1
  acceptance_rows.append({'position_id':position_id,'status':m['status'],'termination_reason':m.get('termination_reason'),'request_diff_valid':m['request_diff_valid'],'schema_and_visibility_valid':m.get('schema_and_visibility_valid',False)})
  if p['cell_id']=='G1-EN':
   rp=base/'V1-EN.replay.json';v=load(rp);assert v['llm_calls']==0
   if v['status']=='REPLAYED':assert v['source_output_sha256']==m['output_sha256'] and m['status'] in ('DELIVERED','DELIVERED_SCHEMA_OR_VISIBILITY_INVALID')
   replays.append({'position_id':position_id,'status':v['status'],'artifact':binding(rp),'exact_identity_pass':v['status']=='REPLAYED','model_calls':0})
  rows.append({'position':p,'completed':binding(base/'completed.json'),'status':m['status'],'schema_valid':m['schema_valid'],'reference_visibility_valid':m['reference_visibility_valid'],'validation_errors':m.get('validation_errors',[]),'evidence_tokens':m['actual_evidence_tokens']})
 ordered_attempts=sorted(attempts,key=lambda a:a['start_monotonic'])
 starts=[a['start_monotonic'] for a in ordered_attempts];gaps=[b-a for a,b in zip(starts,starts[1:])];assert not gaps or min(gaps)>=60
 for previous,current in zip(ordered_attempts,ordered_attempts[1:]):assert current['start_monotonic']>=previous['pacing']['next_start_monotonic'],'Provider reset/Retry-After wait violated'
 accepted=assess(plan,acceptance_rows,True)
 for c,s in counts.items():s['not_executed']=s['planned']-s['executed'];s['other_failures']=s['executed']-s['normal_complete_outputs']-s['output_cap_truncations']
 usage={'known_totals':dict(totals),'metered_responses':len(usage_rows),'priced_responses':len(prices),'attempts_without_usage':len(unknown),'known_calculable_cost_USD':str(sum(prices,Decimal(0))),'actual_invoice_total':None,'rates_USD_per_million':RATES,'approved_pricing_source':SOURCE,'formula':'(input-cached)*input_rate/1e6 + cached*cache_rate/1e6 + output*output_rate/1e6','cached_input_included_in_input':True,'unknown_usage_not_zero':True,'metered_attempts':usage_rows,'unmetered_attempts':unknown}
 create_json(OUT/'usage_and_cost.json',usage)
 result={'version':'r5-8192-development-validation-results','created_at':utc(),'scope':'DEVELOPMENT CAPACITY/CONFORMANCE ONLY; no research performance scores','preflight':binding(OUT/'preflight.json'),'execution_status':state['status'],'executed_positions':len(rows),'not_executed_positions':len(state['not_scheduled']),'attempts':len(attempts),'per_cell':{c:dict(s) for c,s in counts.items()},'capacity_acceptance':accepted,'replay':{'planned':21,'eligible':sum(x['exact_identity_pass'] for x in replays),'replayed':sum(x['exact_identity_pass'] for x in replays),'unavailable':sum(x['status']=='REPLAY_UNAVAILABLE' for x in replays),'not_reached':21-len(replays),'model_calls':0,'records':replays},'transport':{'HTTP_status_counts':dict(collections.Counter(str(a.get('HTTP_status')) for a in attempts)),'retry_reasons':dict(collections.Counter(a.get('reason') for a in attempts if a['will_retry'])),'unknown_delivery_attempts':sum(a['delivery_status']=='UNKNOWN' for a in attempts),'minimum_start_spacing_seconds':min(gaps) if gaps else None,'all_attempts_single_flight':True,'header_records':[{'position_id':a['position_id'],'attempt':a['attempt'],'headers':a['response_headers'],'pacing':a['pacing']} for a in attempts]},'usage':binding(OUT/'usage_and_cost.json'),'pre_tests':binding(OUT/'pre-execution.tests.json'),'post_tests':binding(OUT/'post-execution.tests.json'),'post_integrity':checks,'all_preflight_bindings_unchanged':True,'human_gold_changed':False,'evaluation_material_accessed':False,'protocol_frozen':False,'protocol_deviations':[],'positions':rows,'execution_layer_limitation':'Interrupted STARTED attempt without completion requires author/checkpoint audit; no automatic restart or fabricated delivery status'}
 create_json(OUT/'validation_report.json',result)
 table='\n'.join(f"| {c} | {s['planned']} | {s['executed']} | {s['delivered_positions']} | {s['normal_complete_outputs']} | {s['schema_valid_outputs']} | {s['output_cap_truncations']} | {s['DELIVERED_SCHEMA_OR_VISIBILITY_INVALID']} | {s['other_failures']} | {s['not_executed']} |" for c,s in counts.items())
 smoke_table='\n'.join(f"| {c} | {counts[c]['planned']} | {counts[c]['executed']} | {counts[c]['schema_valid_outputs']} | {counts[c]['reference_visibility_valid_complete_outputs']} | {counts[c]['schema_and_visibility_valid']} | {counts[c]['input_view_and_budget_checks_passed']} |" for c in ('G1-E','G1-N'))
 cap_details='\n'.join(f"- `{position}`: provider `status=incomplete`, reason `max_output_tokens`; exact response and output preserved; no retry." for position in accepted['truncated']) or 'No output-cap truncation was observed.'
 next_action='Do not accept or freeze the 8192 candidate. Review the preserved truncation and authorize a separately versioned offline development proposal before any further generation. The 46 unscheduled positions remain unexecuted; no automatic resume or token-limit increase.' if accepted['truncated'] else 'Review the validation outcome and remaining conformance/custody/freeze decisions under separate authorization.'
 text=f'''# r5 8192 Development Validation — Author Review

**{accepted['status']}**. Protocol NOT FROZEN; no final evaluation or custody provisioning.

## A. Preflight

All r5 inventory, manifest and protected r4/gold bindings passed. 64 exact requests verified; 40 stress requests differ from r4 only at output cap. Fixed model gpt-4.1-2025-04-14, temperature 0, no seed assumption, output 8192, input evidence safety ceiling 16384. Scientific candidate files unchanged; separate execution adapter bound before calls.

## B–C. Execution

Logical positions executed: {len(rows)}/64; transport attempts: {len(attempts)}. Status: {state['status']}.

| Cell | Planned | Executed | Delivered | Complete outputs | Schema valid | Cap truncations | Schema/context/visibility failures | Other non-complete failures | Not executed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{table}

Complete schema-valid delivery does not imply factual correctness. Full attempt status/headers/IDs/raw bytes retained in the run folders and JSON report.

## D. Capacity decision

{accepted['status']}. A cap truncation overrides completing the matrix. No limit increase, retry of truncated output, prompt shortening or evidence reduction is authorized. No-delivery remains separate/inconclusive. A development pass would not guarantee zero evaluation truncation and never automatically freezes 8192.

{cap_details}

Run stopped at {state['finished_at']}; {len(state['not_scheduled'])} remaining positions were not scheduled.

## E. Smoke conformance

G1-E/G1-N delivered output schema/context/reference checks appear separately in the JSON report. All scheduled inputs were validated against exact view, necessary metadata, existing entry quotas/48,000-byte policy and 16,384 evidence safety ceiling. Unexecuted positions are not successes or failures. No factual scores were used to tune the protocol.

| Cell | Planned | Executed | Schema valid | Visible references, complete outputs | All output conformance checks | Input view/budget checks |
|---|---:|---:|---:|---:|---:|---:|---:|
{smoke_table}

## F. V1-EN replay

{result['replay']['replayed']} replayed; {result['replay']['unavailable']} unavailable; {result['replay']['not_reached']} not reached. Eligible replay input hashes matched exact corresponding stored G1-EN bytes; zero verifier model calls. Raw and published outputs retained separately.

## G. Transport

HTTP counts: {result['transport']['HTTP_status_counts']}. Retry reasons: {result['transport']['retry_reasons']}. Unknown-delivery attempts: {result['transport']['unknown_delivery_attempts']}. Minimum recorded request-start spacing: {result['transport']['minimum_start_spacing_seconds']} seconds. Single in-flight request; Retry-After and later reset headers respected. [Official header reference](https://developers.openai.com/api/docs/guides/rate-limits#rate-limits-in-headers).

## H. API usage/cost

Known input: {totals['input_tokens']:,}; cached input (subset): {totals['cached_input_tokens']:,}; output: {totals['output_tokens']:,}; total: {totals['total_tokens']:,} tokens. Known calculable list-price subtotal **USD {usage['known_calculable_cost_USD']}**, using the approved documented pricing formula. {len(unknown)} attempts without provider usage remain unknown, never assumed zero. This is not necessarily the provider invoice. Exact meters and pricing in usage_and_cost.json.

Provider input usage includes the full request; the separate 16,384-token safety ceiling applies to the serialized input evidence, not total provider-billed input. Cached input is already included in input tokens.

## I–J. Tests and preservation

Pre-execution tests: {load(OUT/'pre-execution.tests.json')['tests_run']} PASS. Post-execution tests: {post['tests_run']} PASS. r5 candidate, protected r4/legacy and sealed gold hashes verified again after the run. Every preflight protected binding unchanged. No gold facts, aliases, guardrails or human decisions changed. No evaluation evidence/gold/results accessed.

## K. Artifacts

New result namespace: results/investigation-r5-validation/. post_validation_manifest.json and its SHA-256 sidecar bind all new run records, reports, tests and execution adapter files. Original r5 candidate/manifest are not overwritten.

## L. Deviations

{result['protocol_deviations']}. Early capacity stop, when triggered, is compliance with author instruction and not missing-data selection. All completed and unavailable records remain preserved.

## M. Remaining blockers

Capacity acceptance and any unresolved smoke conformance require author review. Custody ACL/account logging and gold commitments remain unprovisioned; no evaluation authorization. Final protocol freeze always needs explicit approval.

## N. Next author action

Review this validation outcome and its exact failure/conformance records. If the hard output-cap stop fired, decide a separately versioned development plan; do not resume unscheduled positions or increase limits automatically. If passed, review the evidence and remaining custody/freeze steps under separate authorization. STOP for author review.

Recommended action for this run: {next_action}
'''
 (OUT/'author_review_report.md').write_text(text)
 paths=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ('execution.lock','post_validation_manifest.json','post_validation_manifest.json.sha256')]
 paths += list((ROOT/'src/investigation_r5_live').glob('*.py'))+[ROOT/'scripts/run_investigation_r5_validation.py',ROOT/'scripts/check_investigation_r5_validation.py',ROOT/'scripts/report_investigation_r5_validation.py',ROOT/'tests/test_investigation_r5_live.py']
 manifest={'version':'r5-post-validation-artifacts','protocol_frozen':False,'files':[binding(p) for p in sorted(set(paths))],'parent_candidate':binding(ROOT/'configs/investigation_protocol.v1.offline_candidate.r5.json'),'parent_validation_manifest':binding(ROOT/'results/investigation-r5/validation_manifest.json')}
 mp=OUT/'post_validation_manifest.json';create_json(mp,manifest);Path(str(mp)+'.sha256').write_text(file_hash(mp)+'  post_validation_manifest.json\n')
 print(json.dumps({'capacity':accepted['status'],'executed':len(rows),'attempts':len(attempts),'per_cell':result['per_cell'],'tokens':dict(totals),'cost_USD':usage['known_calculable_cost_USD'],'post_manifest_sha256':file_hash(mp)},indent=2))
if __name__=='__main__':report()
