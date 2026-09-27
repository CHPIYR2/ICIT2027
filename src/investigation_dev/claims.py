"""Evidence-dependent finite support checks and specialization-aware matching.

Raw annotations/outputs are never rewritten. Free prose needs a hash-bound human
review for content matching; B4 publishes only finite, exactly rendered statements.
"""
import copy
import math
from fractions import Fraction
from .common import ROOT, load, dumps, digest
from .custody import require_development
from investigation.schema_v2 import schema, check
from investigation.fact_keys_phase2a import propose_fact_key
from retrieval.investigation_retriever_v2 import validate_bundle

FAMILIES = {'voltage':'PER_UNIT','current':'AMPERE','active_power':'WATT','reactive_power':'VAR'}
NUMERIC = {'reported_change','electrical_change'}
TEMPLATES = load(ROOT/'prompts/investigation-v1/canonical_text.v1.json')

class Unsupported(ValueError):
    pass

def need(condition, reason):
    if not condition: raise Unsupported(reason)

def reference_number(v):
    need(type(v) in (int,float) and math.isfinite(v), 'nonfinite_or_boolean_numeric')
    return Fraction(v)

def numeric_equal(predicted, reference, duration=False):
    need(type(predicted) in (int,float) and math.isfinite(predicted), 'nonfinite_or_boolean_numeric')
    p = Fraction(str(predicted))
    r = reference if isinstance(reference,Fraction) else reference_number(reference)
    return abs(p-r) <= (Fraction(5,10**7) if duration else Fraction(5,10**8)*abs(r))

def fmt(v):
    return dumps(v) if isinstance(v,(list,dict,bool)) or v is None else str(v)

def render(name, **values):
    return TEMPLATES[name].format(**{k:fmt(v) for k,v in values.items()})

def context(bundle):
    validate_bundle(bundle)
    idx = {r['evidence_id']:r for r in bundle['entries']}
    meta = {m['evidence_id']:m for m in bundle['metadata'].values()}
    meta.update(bundle['control_metadata'])
    need(not(set(idx)&set(meta)), 'record_metadata_id_collision')
    return idx, meta

def valid_e(r, bundle, numeric=False):
    need(r['source_type']=='process' and not r['quality_flags'] and r['value'] is not None, 'invalid_E_quality')
    ch = r['fields']['channel_id']; m = bundle['metadata'].get(ch)
    need(m is not None, 'missing_channel_mapping')
    need(r['asset_id'] is not None and r['asset_id']==m['asset_id'], 'asset_mismatch')
    need(r['unit']==m['unit'] and r['fields']['family']==m['family'], 'family_or_unit_mismatch')
    need((m['family']=='reported_state')==(type(r['value']) is bool), 'boolean_family_mismatch')
    if numeric:
        reference_number(r['value'])
        need(m['family'] in FAMILIES and m['unit']==FAMILIES[m['family']], 'electrical_family_gate')
    return m

def require_entities(c, assets=(), channels=(), endpoints=()):
    for field, expected in [('asset_ids',assets),('channel_ids',channels),('endpoint_ids',endpoints)]:
        need(sorted(c[field])==sorted(expected), field+'_mismatch')

def refs_for(c):
    p=c['payload'];ids=set()
    for k in ('record_id','before_id','after_id','earlier_id','later_id','coverage_id','left_id','right_id','scope_id','address_evidence_id','mapping_evidence_id'):
        if p.get(k) is not None:ids.add(p[k])
    for k in ('record_ids','mapping_ids','basis_ids'):ids.update(p.get(k,[]))
    return ids

def typed_support(c,bundle):
    require_development(bundle['scope']['event_id'])
    root=schema('investigation_claim.v2.json');check(c,root['$defs']['claim'],root)
    idx,meta=context(bundle);p=c['payload'];kind=c['claim_type'];required=refs_for(c)
    if kind!='unknown':need(c['support_assertion']=='asserted','assertion_status_conflict')
    scope_id=bundle['scope']['evidence_id'];available=set(idx)|set(meta)|{scope_id}
    need(required<=available, 'unavailable_payload_reference')
    need(set(c['evidence_ids'])<=available, 'unavailable_citation')
    allowed=set(required); result={'raw_claim_type':kind, 'raw_claim_sha256':digest(c), 'bundle_sha256':digest(bundle)}
    key_kind=kind; key=None
    def record(rid,types):
        r=idx.get(rid);need(r is not None and r['source_type'] in types,'wrong_evidence_role');return r
    if kind in NUMERIC or kind=='reported_state_change':
        a=record(p['before_id'],{'process'});b=record(p['after_id'],{'process'})
        m=valid_e(a,bundle,kind in NUMERIC);n=valid_e(b,bundle,kind in NUMERIC)
        need(a['evidence_id']!=b['evidence_id'] and a['observation_time']<b['observation_time'],'nonordered_pair')
        need(a['fields']['channel_id']==b['fields']['channel_id'] and a['asset_id']==b['asset_id'] and a['unit']==b['unit'] and m==n,'incompatible_pair')
        need(p['before_time']==a['observation_time'] and p['after_time']==b['observation_time'],'timestamp_mismatch')
        ch=a['fields']['channel_id'];asset=a['asset_id'];require_entities(c,[asset],[ch])
        if kind in NUMERIC:
            need(numeric_equal(p['before_value'],a['value']) and numeric_equal(p['after_value'],b['value']),'wrong_reported_value')
            delta=reference_number(b['value'])-reference_number(a['value'])
            expected_unit=a['unit'];expected=delta
            if p['operation']=='percent_change':
                need(a['value']!=0,'zero_baseline_percent');expected=100*delta/abs(reference_number(a['value']));expected_unit='PERCENT'
            need(p['unit']==expected_unit,'result_unit_mismatch')
            need(numeric_equal(p['result'],expected),'arithmetic_mismatch')
            key_kind='reported_change';key={'before_id':p['before_id'],'after_id':p['after_id'],'quantity':p['operation'],'unit':p['unit']}
            identity={'projection_version':'numeric-fact-projection-v1','event_id':bundle['scope']['event_id'],'evidence_export_version':'investigation-export-v2','canonical_kind':'reported_numeric_change','before_e_id':p['before_id'],'after_e_id':p['after_id'],'asset_id':asset,'channel_id':ch,'family':m['family'],'source_unit':a['unit'],'operation':p['operation'],'result_unit':p['unit']}
            result['canonical_identity']=identity
            text=render('numeric',family=m['family'],channel=ch,asset=asset,before=p['before_value'],after=p['after_value'],source_unit=a['unit'],t0=p['before_time'],t1=p['after_time'],before_id=p['before_id'],after_id=p['after_id'],operation=p['operation'],result=p['result'],result_unit=p['unit'])
        else:
            need(type(a['value']) is bool and type(b['value']) is bool and a['value']!=b['value'] and m['family']=='reported_state' and a['unit']=='NONE','invalid_state_pair')
            need(p['before_value'] is a['value'] and p['after_value'] is b['value'],'state_value_mismatch')
            key={'before_id':p['before_id'],'after_id':p['after_id']}
            text=render('state',channel=ch,asset=asset,before=p['before_value'],after=p['after_value'],t0=p['before_time'],t1=p['after_time'],before_id=p['before_id'],after_id=p['after_id'])
        allowed.add(m['evidence_id'])
        # Existing B0 cites its d record. Validate the entire derived fields before accepting it.
        for r in idx.values():
            f=r.get('fields',{})
            if r['source_type']=='derived' and f.get('before_id')==p['before_id'] and f.get('after_id')==p['after_id']:
                from retrieval.investigation_retriever import difference
                need(r==difference(a,b),'invalid_derived_record');allowed.add(r['evidence_id'])
    elif kind=='reported_value':
        r=record(p['record_id'],{'process'});m=valid_e(r,bundle)
        need(p['unit']==r['unit'] and p['time']==r['observation_time'],'value_unit_time_mismatch')
        if type(r['value']) is bool:need(type(p['value']) is bool and p['value'] is r['value'],'boolean_value_mismatch')
        else:need(numeric_equal(p['value'],r['value']),'value_mismatch')
        require_entities(c,[r['asset_id']],[r['fields']['channel_id']]);allowed.add(m['evidence_id'])
        key={'record_id':p['record_id']}
        text=render('value',record_id=p['record_id'],value=p['value'],unit=p['unit'],channel=r['fields']['channel_id'],asset=r['asset_id'],time=p['time'])
    elif kind in ('network_activity','acknowledgement_observed'):
        r=record(p['record_id'],{'packet','message'});need(p['time']==r['observation_time'],'network_time_mismatch');require_entities(c)
        f=r['fields']
        if kind=='network_activity':
            k=p['activity'];ok=(r['source_type']=='packet' and (k=='packet_observed' or k=='tcp_rst_observed' and bool((f['tcp_flags'] or 0)&4))) or (r['source_type']=='message' and k=='iec_'+f['apci_format'].lower()+'_frame')
            need(ok,'network_activity_mismatch');key={'record_id':p['record_id'],'activity':k};text=render('network',record_id=p['record_id'],activity=k,time=p['time'])
        else:
            k=p['kind'];ok=(k=='tcp_ack_bit' and r['source_type']=='packet' and bool((f['tcp_flags'] or 0)&16)) or (r['source_type']=='message' and (k=='iec_s_frame' and f['apci_format']=='S' or k=='iec_activation_confirmation' and f['apci_format']=='I' and f['asdu_type'] in range(45,52) and f['cause_of_transmission']==7))
            need(ok,'ack_subtype_mismatch');key={'record_id':p['record_id'],'kind':k};text=render('ack',record_id=p['record_id'],kind=k,time=p['time'])
    elif kind=='command_observed':
        m=record(p['record_id'],{'message'});f=m['fields']
        need(f['apci_format']=='I' and f['asdu_type']==p['asdu_type'] and f['cause_of_transmission']==p['cause_of_transmission']==6 and p['time']==m['observation_time'],'command_mismatch')
        mapped=[p[k] for k in ('address_evidence_id','mapping_evidence_id','mapped_control_point_id','mapped_target_asset_id')]
        need(all(x is None for x in mapped) or all(x is not None for x in mapped),'partial_command_mapping')
        if mapped[0]:
            a=record(mapped[0],{'command_address_observation'});cm=meta[mapped[1]]
            need(a['parent_ids']==[m['evidence_id']] and a['mapping_status']=='exact_static_match' and a['mapping_evidence_id']==mapped[1] and a['mapped_control_point_id']==mapped[2]==cm['control_point_id'] and a['mapped_target_asset_id']==mapped[3]==cm['asset_id'],'command_mapping_mismatch')
            require_entities(c,[mapped[3]]);key_kind='mapped_command_observed';key={'message_id':m['evidence_id'],'address_id':a['evidence_id'],'mapping_id':mapped[1],'control_point_id':mapped[2],'asset_id':mapped[3]}
            text=render('mapped_command',record_id=p['record_id'],address_id=mapped[0],mapping_id=mapped[1],control_point=mapped[2],asset=mapped[3],asdu=p['asdu_type'],time=p['time'])
        else:
            require_entities(c);key={'message_id':m['evidence_id']};text=render('command',record_id=p['record_id'],asdu=p['asdu_type'],time=p['time'])
    elif kind=='temporal_association':
        a=record(p['earlier_id'],{'packet','message','process','command_address_observation'});b=record(p['later_id'],{'packet','message','process','command_address_observation'})
        for r in (a,b):
            if r['source_type']=='process':valid_e(r,bundle)
            if r['source_type']=='command_address_observation':required.update(r['parent_ids']);allowed.update(r['parent_ids'])
        need(a['evidence_id']!=b['evidence_id'],'self_temporal_relation')
        t0=a['observation_time'];t1=b['observation_time']
        need(t0<t1 if p['relation']=='precedes' else t0==t1,'temporal_order_mismatch')
        need(numeric_equal(p['delta_seconds'],reference_number(t1)-reference_number(t0),True),'duration_mismatch')
        if p['scope']=='same_observed_asset':
            need({a['source_type'],b['source_type']}=={'command_address_observation','process'},'same_asset_needs_N_E')
            addr=a if a['source_type']=='command_address_observation' else b;e=b if addr is a else a
            em=valid_e(e,bundle);need(addr['mapping_status']=='exact_static_match','missing_control_mapping')
            cm=meta[addr['mapping_evidence_id']]
            need(addr['cause_of_transmission']==6 and addr['mapped_target_asset_id']==e['asset_id']==p['mapped_asset_id']==cm['asset_id'],'same_asset_mismatch')
            need(set(p['mapping_ids'])=={cm['evidence_id'],em['evidence_id']},'both_mapping_edges_required')
            require_entities(c,[e['asset_id']],[e['fields']['channel_id']])
        else:
            need(not p['mapping_ids'] and p['mapped_asset_id'] is None,'episode_scope_has_asset');require_entities(c)
        key={'earlier_id':p['earlier_id'],'later_id':p['later_id'],'relation':p['relation'],'scope':p['scope'],'mapping_ids':p['mapping_ids'],'asset_id':p['mapped_asset_id']}
        text=render('temporal',earlier_id=p['earlier_id'],later_id=p['later_id'],relation=p['relation'],delta=p['delta_seconds'],scope=p['scope'],asset=p['mapped_asset_id'])
    elif kind=='asset_relationship':
        rs=[record(r,{'packet','process','message','command_address_observation'}) for r in p['record_ids']];relation=p['relation']
        if relation=='command_address_maps_to_asset':
            need(len(rs)==2 and {r['source_type'] for r in rs}=={'message','command_address_observation'},'mapping_roles')
            a=next(r for r in rs if r['source_type']=='command_address_observation');m=next(r for r in rs if r['source_type']=='message')
            need(a['parent_ids']==[m['evidence_id']] and a['mapping_status']=='exact_static_match' and p['mapping_ids']==[a['mapping_evidence_id']] and p['mapped_asset_id']==a['mapped_target_asset_id'],'mapping_mismatch')
            require_entities(c,[p['mapped_asset_id']]);key_kind=relation;key={'message_id':m['evidence_id'],'address_id':a['evidence_id'],'mapping_id':a['mapping_evidence_id'],'asset_id':p['mapped_asset_id']}
        elif relation=='same_mapped_asset':
            ms=[valid_e(r,bundle) for r in rs];need(len(rs)>=2,'same_asset_needs_two_observations')
            need(all(r['asset_id']==p['mapped_asset_id'] for r in rs) and set(p['mapping_ids'])=={m['evidence_id'] for m in ms},'same_asset_mapping_mismatch')
            require_entities(c,[p['mapped_asset_id']],sorted({r['fields']['channel_id'] for r in rs}));key_kind=relation;key={'record_ids':p['record_ids'],'mapping_ids':p['mapping_ids'],'asset_id':p['mapped_asset_id']}
        else:
            need(len(rs)==1 and rs[0]['source_type']=='packet' and not p['mapping_ids'] and p['mapped_asset_id'] is None,'endpoint_scope')
            f=rs[0]['fields'];eps=[f['source_endpoint'],f['destination_endpoint']];need(None not in eps,'unknown_endpoint');require_entities(c,endpoints=sorted(set(eps)))
            key_kind=relation;key={'packet_id':rs[0]['evidence_id'],'source_endpoint':eps[0],'destination_endpoint':eps[1]}
        text=render('asset',records=p['record_ids'],relation=relation,mappings=p['mapping_ids'],asset=p['mapped_asset_id'],endpoints=c['endpoint_ids'])
    elif kind=='communication_gap':
        r=record(p['coverage_id'],{'derived'});f=r['fields'];need(f.get('kind')=='communication_gap' and f.get('complete_visible_query') is True,'gap_receipt_required')
        need(f['population']=='captured_TCP_2404_packets','gap_population')
        need(all(p[k]==f[k] for k in ('left_id','right_id','start','end')) and numeric_equal(p['duration_seconds'],reference_number(f['end'])-reference_number(f['start']),True),'gap_mismatch')
        need(f['start']<=f['end'] and f['window']==[-60,60] and f['universe_sha256'] and f['ordered_population_sha256'],'gap_query_provenance')
        # Query source is bound in the trusted production receipt; never infer a gap from top-k alone.
        require_entities(c);key={'coverage_id':p['coverage_id'],'population':p['population'],'start':p['start'],'end':p['end']}
        text=render('gap',coverage_id=p['coverage_id'],start=p['start'],end=p['end'],duration=p['duration_seconds'],left_id=p['left_id'],right_id=p['right_id'])
    elif kind=='unknown':
        need(p['scope_id']==scope_id,'unknown_scope_mismatch');require_entities(c)
        subjects={'execution','causation','malicious_intent','successful_compromise','attribution','benign_or_safe','true_measurement_time','cross_source_relationship'}
        need(p['attempted_conclusion'] in subjects,'unknown_subject_not_checkable')
        if p['reason']=='view_excluded':need(p['attempted_conclusion']=='cross_source_relationship' and bundle['scope']['view']!='EN','view_exclusion_not_established')
        elif p['reason']=='no_measurement_time':need(p['attempted_conclusion']=='true_measurement_time' and not bundle['scope']['reported_measurement_time_available'],'measurement_time_policy')
        else:need(p['reason']=='policy_disallows_inference' and p['attempted_conclusion'] not in {'cross_source_relationship','true_measurement_time'},'unknown_reason_not_checkable')
        need(p['missing_requirement']=='independent supporting evidence outside the approved observation contract','unknown_free_text_not_checkable')
        text=render('unknown',subject=p['attempted_conclusion'],reason=p['reason'])
    elif kind in ('security_indicator','security_interpretation'):
        # Accepted Q6 explicitly requires human relevance judgment; no hidden threshold/template rule.
        raise Unsupported('Q6_relevance_requires_human_review_not_deterministically_checkable')
    else:raise Unsupported('claim_type_not_supported')
    need(set(c['evidence_ids'])<=allowed,'irrelevant_citation')
    result.update(canonical_text=text,required_ids=sorted(required),allowed_ids=sorted(allowed),substantive=kind!='unknown',key_kind=key_kind)
    if key is not None:
        result['key_identity']=key;result['fact_key']=propose_fact_key(bundle['scope']['event_id'],key_kind,key)
    return result

def validate_raw_support(c,bundle,require_citations=False,text_review=None):
    result=typed_support(c,bundle)
    if require_citations:need(set(result['required_ids'])<=set(c['evidence_ids']),'incomplete_cited_support')
    if c['claim_text']!=result['canonical_text']:
        legacy_text_valid=False
        if c['claim_type'] in ('command_observed','asset_relationship','temporal_association'):
            try:
                from investigation.support_v2 import validate_supported_claim
                legacy_text_valid=validate_supported_claim(c,bundle)
            except (ValueError,KeyError,TypeError,StopIteration):pass
        need(legacy_text_valid or text_review is not None and text_review.get('claim_sha256')==digest(c) and text_review.get('bundle_sha256')==digest(bundle) and text_review.get('supported') is True and text_review.get('reviewer_id') and text_review.get('reviewed_at'),'noncanonical_text_requires_hash_bound_human_review')
    return result

def canonical_numeric_fact(c,bundle,text_review=None,require_citations=False):
    need(c['claim_type'] in NUMERIC,'not_numeric_change')
    checked=validate_raw_support(c,bundle,require_citations,text_review)
    return {'raw_claim':copy.deepcopy(c),'raw_sha256':digest(c),'identity':checked['canonical_identity'],
            'fact_key':checked['fact_key'],'support':checked}

def matches_gold(c,bundle,gold,text_review=None):
    """Approved raw support first; reviewed key/alias identity second. No gold mutation."""
    supported=validate_raw_support(c,bundle,text_review=text_review)
    need(gold['event_id']==bundle['scope']['event_id'],'gold_event_mismatch')
    pair={c['claim_type'],gold['claim_type']}
    if len(pair)>1 and not pair<=NUMERIC:return False
    return supported.get('fact_key')==gold['fact_key']

def numeric_claim(bundle,before_id,after_id,operation='difference',raw_type='reported_change',claim_id='c_1'):
    """Fixture/adapter constructor only; callers must not treat construction as support."""
    idx={r['evidence_id']:r for r in bundle['entries']};a=idx[before_id];b=idx[after_id]
    value=b['value']-a['value']
    if operation=='percent_change':
        if a['value']==0:raise Unsupported('zero_baseline_percent')
        value=100*value/abs(a['value'])
    c={'claim_id':claim_id,'question_ids':['Q2'],'claim_type':raw_type,'claim_text':'Pending canonical rendering.','support_assertion':'asserted','evidence_ids':[before_id,after_id], 'asset_ids':[a['asset_id']],'channel_ids':[a['fields']['channel_id']],'endpoint_ids':[],
       'payload':{'before_id':before_id,'after_id':after_id,'before_value':a['value'],'after_value':b['value'],'before_time':a['observation_time'],'after_time':b['observation_time'],'operation':operation,'result':value,'unit':'PERCENT' if operation=='percent_change' else a['unit']}}
    c['claim_text']=typed_support(c,bundle)['canonical_text'];return c

def adapt_b0_numeric(row,bundle):
    """Lossless sidecar for legacy B0 numeric fields; never fixes wrong raw values."""
    need(row['claim_type']=='reported_change' and row['kind']=='numeric_difference','wrong_B0_numeric_kind')
    idx={r['evidence_id']:r for r in bundle['entries']};a=idx[row['before_id']]
    need(row['asset_id']==a['asset_id'] and row['channel_id']==a['fields']['channel_id'] and row['family']==a['fields']['family'] and row['unit']==a['unit'],'B0_identity_family_unit_mismatch')
    outputs=[]
    for operation in ('difference','percent_change'):
        if row[operation] is None:continue
        c=numeric_claim(bundle,row['before_id'],row['after_id'],operation,claim_id='c_'+str(len(outputs)+1))
        c['evidence_ids']=copy.deepcopy(row['evidence_ids'])
        for k in ('before_value','after_value','before_time','after_time'):c['payload'][k]=row[k]
        c['payload']['result']=row[operation]
        checked=typed_support(c,bundle) # Arithmetic checked before rendering any sidecar.
        c['claim_text']=checked['canonical_text']
        outputs.append({'raw_B0_sha256':digest(row),'raw_B0':copy.deepcopy(row),'raw_field':operation,'adapted_claim':c})
    return outputs

def verify_claim(c,bundle):
    try:
        checked=validate_raw_support(c,bundle,require_citations=True)
        return {'claim_id':c['claim_id'],'disposition':'SUPPORTED','reason':'finite_support_checks_passed','published_claim':copy.deepcopy(c),'checks':checked}
    except (ValueError,KeyError,TypeError,StopIteration) as error:
        # Only the already-approved same-asset -> episode scope weakening is automatic.
        try:
            p=c['payload'];need(c['claim_type']=='temporal_association' and p['scope']=='same_observed_asset','no_qualification')
            need(c['claim_text']==render('temporal',earlier_id=p['earlier_id'],later_id=p['later_id'],relation=p['relation'],delta=p['delta_seconds'],scope=p['scope'],asset=p['mapped_asset_id']),'uncheckable_stronger_text')
            q=copy.deepcopy(c);q['payload'].update(scope='episode_only',mapping_ids=[],mapped_asset_id=None);q['asset_ids']=[];q['channel_ids']=[]
            keep={p['earlier_id'],p['later_id']};idx,_=context(bundle)
            for rid in list(keep):
                if idx[rid]['source_type']=='command_address_observation':keep.update(idx[rid]['parent_ids'])
            need(keep<=set(c['evidence_ids']),'missing_retained_support')
            need(all(x in set(idx)|{m['evidence_id'] for m in bundle['metadata'].values()}|set(bundle['control_metadata']) for x in c['evidence_ids']),'fabricated_original_citation')
            q['evidence_ids']=sorted(keep);q['claim_text']=typed_support(q,bundle)['canonical_text']
            checks=validate_raw_support(q,bundle,True)
            return {'claim_id':c['claim_id'],'disposition':'QUALIFIED','reason':'same_asset_not_established_retained_episode_capture_order','original_failure':str(error),'published_claim':q,'checks':checks}
        except (ValueError,KeyError,TypeError,StopIteration):
            return {'claim_id':c.get('claim_id'),'disposition':'INSUFFICIENT','reason':str(error),'published_claim':None,'checks':{'status':'NOT_SUPPORTED_OR_NOT_CHECKABLE'}}
