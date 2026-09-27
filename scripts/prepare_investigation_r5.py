"""Create-once offline inputs audit and 64-position request/parent manifest. No API."""
import json,sys,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_r5.core import OUT,CONFIG,read_bundle,validate_input,development_ids,cell_spec,prompt_for
from investigation_r5.runner import build_request
from investigation_dryrun.common import load,create_json,binding,file_hash,digest,dumps
from investigation_dryrun.tokens import count

def prepare():
 rows=[]
 for eid in development_ids():
  for view in ('E','N','EN'):
   b,r=read_bundle(eid,view);row={'event_id':eid,'view':view,**validate_input(b,r),'source_files':[binding(ROOT/'results/investigation-v2/B0'/eid/view/n) for n in ('retrieved.json','receipt.json')]};rows.append(row)
 create_json(OUT/'input_audit.json',{'scope':'16 development events x E/N/EN; no evaluation evidence','rows':rows,'model_calls':0})
 report=load(ROOT/'results/investigation-dryrun-v1/final_conformance_report.json');positions=[]
 for p in report['effective_144_slots']['output_truncations']:
  if p['baseline'] not in ('B2','B3'):continue
  cell={'B2':'G0','B3':'G1-EN'}[p['baseline']];eid=p['event_id'];rep=p['repetition']
  base=ROOT/'results/investigation-dryrun-v1/runs'/p['run_id']/eid/p['baseline']/f'rep-{rep}'
  m=load(base/'completed.json');a=load(base/f"attempt-{p['attempt']}"/'attempt.json');md=a['provider_metadata']
  if m['status']!='PROVIDER_INCOMPLETE' or md['status']!='incomplete' or md['incomplete_details']['reason']!='max_output_tokens':raise ValueError('Stress selection not exact output-cap failure')
  b,r=read_bundle(eid,'EN');request=build_request(eid,cell,b,r);old=load(base/'request.json')
  if {k:v for k,v in request.items() if k!='max_output_tokens'}!={k:v for k,v in old.items() if k!='max_output_tokens'}:raise ValueError('Stress request changed beyond output cap')
  positions.append({'event_id':eid,'cell_id':cell,'view':'EN','citation_mode':cell_spec(cell)['citation_mode'],'repetition':rep,'purpose':'capacity_stress','position_id':f'{eid}/{cell}/rep-{rep}','parent_completed':binding(base/'completed.json'),'parent_request':binding(base/'request.json'),'parent_attempt':binding(base/f"attempt-{p['attempt']}"/'attempt.json'),'parent_response_id':md['id'],'parent_output_sha256':m['output_sha256'],'allowed_request_changes':{'max_output_tokens':[4096,8192]},'request_sha256':digest(request),'bundle_sha256':digest(b),'receipt_sha256':digest(r)})
 pilots=load(ROOT/'annotations/gold/pilot-v1/manifest.json')
 for e in pilots['events']:
  for cell in ('G1-E','G1-N'):
   view=cell_spec(cell)['view'];b,r=read_bundle(e['event_id'],view);req=build_request(e['event_id'],cell,b,r)
   for rep in (1,2,3):positions.append({'position_id':f"{e['event_id']}/{cell}/rep-{rep}",'event_id':e['event_id'],'cell_id':cell,'view':view,'citation_mode':'required','repetition':rep,'purpose':'new_condition_smoke','pilot_annotation':e['annotation'],'request_sha256':digest(req),'bundle_sha256':digest(b),'receipt_sha256':digest(r),'new_condition_not_a_r4_retry':True})
 positions=sorted(positions,key=lambda x:x['position_id']);assert len(positions)==len({p['position_id'] for p in positions})==64
 counts=dict(collections.Counter(p['cell_id'] for p in positions));assert counts=={'G0':19,'G1-EN':21,'G1-E':12,'G1-N':12}
 create_json(OUT/'validation_manifest.json',{'version':'r5-64-position-development-validation','status':'PREDECLARED_NOT_EXECUTED','model_calls_authorized':False,'protocol_frozen':False,'counts':counts,'generation_positions':64,'V1_EN_replay_positions':21,'historical_B1_truncations_excluded':15,'positions':positions,'parent_report':binding(ROOT/'results/investigation-dryrun-v1/final_conformance_report.json'),'acceptance':{'output_cap_truncations_allowed':0,'delivered_smoke_requires_schema_and_visibility':True,'no_delivery':'separate and INCONCLUSIVE, neither evidence of output-cap pass nor failure','request_diff_required':True,'bindings_must_remain_unchanged':True,'on_any_output_cap_truncation':'preserve, stop capacity acceptance, author review; no rerun or automatic increase'}})
 print(json.dumps({'input_audit_rows':len(rows),'E_max_tokens':max(r['evidence_tokens'] for r in rows if r['view']=='E'),'counts':counts,'generation_executed':0},indent=2))
if __name__=='__main__':prepare()
