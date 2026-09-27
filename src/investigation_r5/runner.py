"""Offline request construction and exact verifier replay. No network client."""
import copy,hashlib
from .core import CONFIG,cell_spec,prompt_for,validate_input,require_development
from investigation_dryrun.common import ROOT,load,dumps,digest,binding
from investigation_dryrun.tokens import count
from investigation_dryrun.structured import compile_schema
from investigation_dryrun.runner import delivery_validation,parse_experiment,replay_bytes as r4_replay


def build_request(event_id,cell,bundle,receipt):
    require_development(event_id);spec=cell_spec(cell)
    if spec['action']!='generation':raise ValueError('No model request for reference or verifier')
    validate_input(bundle,receipt)
    if bundle['scope']['event_id']!=event_id or bundle['scope']['view']!=spec['view']:raise ValueError('Cell/view mismatch')
    m=load(CONFIG/'model.candidate.json');budget=load(CONFIG/'token_budget.candidate.json')
    if m['live_api_enabled'] or m['max_output_tokens']!=8192 or budget['max_output_tokens']!=8192 or budget['evidence_token_safety_ceiling']!=16384:raise ValueError('Offline candidate configuration drift')
    if m['temperature']!=0 or m['exact_callable_model']!='gpt-4.1-2025-04-14':raise ValueError('Model drift')
    prompt,ref=prompt_for(cell);evidence=dumps(bundle)
    if count(prompt)+count(evidence)>budget['max_input_text_tokens']:raise ValueError('Input text budget exceeded')
    schema=compile_schema(spec['citation_mode'])
    local_reserved=count(prompt)+count(evidence)+count(dumps(schema))+8192
    if local_reserved>m['context_window']:raise ValueError('Context budget exceeded')
    return {'model':m['exact_callable_model'],'instructions':prompt,'input':evidence,'temperature':0,'max_output_tokens':8192,'store':False,'truncation':'disabled','tools':[],'text':{'format':{'type':'json_schema','name':'investigation_v3','strict':True,'schema':schema}}}


def generate(*args,**kwargs):
    # Deliberately no live adapter in this candidate; no credentials are read.
    raise PermissionError('r5 OFFLINE ONLY: future model execution needs explicit author authorization')


def reference_visibility_errors(experiment,bundle):
    visible={r['evidence_id'] for r in bundle['entries']}|{r['evidence_id'] for r in bundle['metadata'].values()}|set(bundle['control_metadata'])|{bundle['scope']['evidence_id']}
    reference_keys={'scope_id','record_id','before_id','after_id','earlier_id','later_id','coverage_id','left_id','right_id','address_evidence_id','mapping_evidence_id','record_ids','mapping_ids','basis_ids','evidence_ids'}
    errors=[]
    entity_keys={'asset_ids','channel_ids','endpoint_ids','mapped_asset_id','mapped_target_asset_id','mapped_control_point_id'}
    allowed_entities=set()
    def collect(obj):
        if isinstance(obj,dict):
            for v in obj.values():collect(v)
        elif isinstance(obj,list):
            for v in obj:collect(v)
        elif isinstance(obj,str) and obj.startswith(('asset_','ch_','ep_','cp_')):allowed_entities.add(obj)
    collect(bundle)
    def walk(obj):
        if isinstance(obj,dict):
            for k,v in obj.items():
                if k in reference_keys:
                    values=v if isinstance(v,list) else [v]
                    if any(x is not None and (not isinstance(x,str) or x not in visible) for x in values):errors.append('invisible_reference:'+k)
                if k in entity_keys:
                    values=v if isinstance(v,list) else [v]
                    if any(x is not None and (not isinstance(x,str) or x not in allowed_entities) for x in values):errors.append('invisible_entity:'+k)
                walk(v)
        elif isinstance(obj,list):
            for v in obj:walk(v)
    walk(experiment)
    return errors


def validate_delivery(exp,event_id,cell,bundle):
    s=cell_spec(cell)
    return delivery_validation(exp,event_id,s['view'],s['citation_mode'])+reference_visibility_errors(exp,bundle)


def replay_bytes(event_id,raw,generation_manifest,bundle,receipt):
    m=generation_manifest
    if m.get('cell_id')!='G1-EN' or m.get('view')!='EN' or m.get('citation_mode')!='required':raise ValueError('Wrong r5 replay source')
    validate_input(bundle,receipt)
    # Adapt provenance keys only. Raw bytes and verifier implementation are untouched.
    legacy={**m,'baseline':'B3'}
    result=r4_replay(event_id,raw,legacy,bundle,receipt)
    result.update(version='r5-exact-replay',cell_id='V1-EN',source_cell_id='G1-EN',source_output_sha256=hashlib.sha256(raw).hexdigest(),r5_adapter=binding(ROOT/'src/investigation_r5/runner.py'))
    result.pop('baseline');result['historical_verifier_engine']='r4 B4; unchanged finite verification/publishing implementation'
    return result


def exercise_cell(event_id,cell,fixture,directory):
    """Integration route for finite synthetic fixtures only, no provider adapter."""
    from .core import read_bundle
    from .transport import exercise
    b,r=read_bundle(event_id,cell_spec(cell)['view']);q=build_request(event_id,cell,b,r)
    return exercise(q,fixture,directory,validate=lambda exp:validate_delivery(exp,event_id,cell,b))
