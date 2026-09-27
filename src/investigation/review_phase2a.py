"""Pilot-only full-universe reader and human annotation statistics. No scoring."""
import gzip
import json
from collections import Counter
from pathlib import Path
from sherlock.io import ROOT,read_json,sha256
from investigation.pilot_audit import CLAIM_TYPES
from retrieval.investigation_retriever import largest_gap
from investigation.fact_keys_phase2a import propose_fact_key

VIEWS=('E','N','EN')
ANSWERABILITY=('supported','partially_supported','insufficient')
ACTIONS=('assert','qualify','withhold')
CATEGORIES=('observation','derived_observation','static_relationship','temporal_association','weak_review_interpretation','guardrail_insufficiency')
CHECKABILITY=('mechanically_checkable','human_semantic_judgment','both')
PROHIBITED=('execution','physical_causation','malicious_intent','attacker_identity','successful_compromise','benign_safe_from_absence')


def pilot_ids():
    return read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids']


def load_universe(event_id,view='EN',production=False):
    if event_id not in pilot_ids():raise ValueError('Phase2A tools only access four approved development pilots')
    if view not in VIEWS:raise ValueError('Unknown view')
    folder=ROOT/'results/investigation-v2/B0'/event_id/view
    manifest=read_json(ROOT/'results/investigation-v2/baseline_manifest.json')
    hashes=next(r['files'] for r in manifest['rows'] if r['event_id']==event_id and r['view']==view)
    path=folder/('retrieved.json' if production else 'eligible.json.gz')
    if sha256(path)!=hashes[str(path.relative_to(ROOT))]:raise ValueError('Immutable evidence hash mismatch')
    if production:
        b=read_json(path);return {'scope':b['scope'],'records':b['entries'],'metadata':b['metadata'],'control_metadata':b['control_metadata']}
    with gzip.open(path,'rt') as f:return json.load(f)


def support_index(event_id,view,production=False):
    public=load_universe(event_id,view,production)
    index={r['evidence_id']:r for r in public['records']}
    index[public['scope']['evidence_id']]=public['scope']
    index.update({m['evidence_id']:m for m in public['metadata'].values()});index.update(public['control_metadata'])
    if not production:
        # Pre-existing approved numeric query candidates, not invented baselines.
        if 'E' in view:
            packet=ROOT/'annotations/events-v2'/event_id
            pair_path=packet/'numerical_candidates.DRAFT.json'
            if sha256(pair_path)!=read_json(packet/'manifest.json')['files'][pair_path.name]:raise ValueError('Immutable numerical candidates changed')
            pairs=read_json(pair_path)['entries']
            for d in pairs:
                if set(d['parent_ids'])<=set(index):index[d['evidence_id']]=d
        if 'N' in view:
            gap=largest_gap(public);index[gap['evidence_id']]=gap
    return index


def blank_fact(event_id):
    return {'gold_claim_id':None,'event_id':event_id,'question_ids':[],'claim_type':None,'epistemic_category':None,
        'atomic_statement':None,'fact_key':None,'proposed_fact_key':None,'key_kind':None,'key_identity':None,'key_override_reason':None,
        'minimal_support_sets':{v:[] for v in VIEWS},'E_answerability':None,'N_answerability':None,'EN_answerability':None,
        'acceptable_action':{v:None for v in VIEWS},'prohibited_stronger_interpretation':[],
        'ambiguity_notes':None,'reviewer_id':None,'review_status':'UNREVIEWED','checkability':None,
        'alias_of':None,'alias_decision':None,'alias_rationale':None,
        'view_accounting':{v:{'eligible_in_view':None,'retrieved_in_production_bundle':None,'recovered_by_system':None} for v in VIEWS}}


def validate_fact(fact,event_id):
    required=set(blank_fact(event_id))
    if set(fact)!=required or fact['event_id']!=event_id:raise ValueError('Annotation fields/event mismatch')
    if any(fact['view_accounting'][v]['recovered_by_system'] is not None for v in VIEWS):raise ValueError('System recovery is out of Phase2A scope')
    if fact['review_status'] not in ('UNREVIEWED','IN_REVIEW','HUMAN_REVIEWED'):raise ValueError('Unknown review status')
    if fact['review_status']!='HUMAN_REVIEWED':return False
    for field in ('gold_claim_id','reviewer_id','atomic_statement','fact_key'):
        if not isinstance(fact[field],str) or not fact[field].strip():raise ValueError('Missing human field: '+field)
    if fact['claim_type'] not in CLAIM_TYPES or fact['epistemic_category'] not in CATEGORIES or fact['checkability'] not in CHECKABILITY:raise ValueError('Unknown claim/category/checkability')
    if not fact['question_ids'] or len(set(fact['question_ids']))!=len(fact['question_ids']) or not set(fact['question_ids'])<=set('Q'+str(i) for i in range(1,8)):raise ValueError('Invalid question references')
    if fact['alias_decision'] not in ('distinct','merge_alias','ambiguous'):raise ValueError('Human alias decision required')
    if fact['alias_decision']=='ambiguous':raise ValueError('Resolve ambiguous alias before HUMAN_REVIEWED')
    if bool(fact['alias_of'])!=(fact['alias_decision']=='merge_alias'):raise ValueError('Alias target/decision mismatch')
    if fact['alias_of'] and not fact['alias_rationale']:raise ValueError('Human alias rationale required')
    if fact['key_kind'] is not None:
        key=propose_fact_key(event_id,fact['key_kind'],fact['key_identity'])
        if fact['proposed_fact_key']!=key:raise ValueError('Stale mechanical key proposal')
        if fact['fact_key']!=key and not fact['key_override_reason']:raise ValueError('Override requires human reason')
    elif not fact['key_override_reason']:raise ValueError('Human semantic key needs explicit rationale')
    for view in VIEWS:
        if fact[view+'_answerability'] not in ANSWERABILITY or fact['acceptable_action'][view] not in ACTIONS:raise ValueError('Missing view judgment')
        sets=fact['minimal_support_sets'][view]
        if not isinstance(sets,list) or any(not isinstance(s,list) or not s or len(s)!=len(set(s)) for s in sets):raise ValueError('Support sets must be nonempty alternative ID lists')
        if fact[view+'_answerability']=='supported' and not sets:raise ValueError('Supported fact requires human-selected support set')
        if fact[view+'_answerability']=='insufficient' and fact['acceptable_action'][view]=='assert':raise ValueError('Cannot assert an insufficient fact')
        acc=fact['view_accounting'][view]
        if set(acc)!={'eligible_in_view','retrieved_in_production_bundle','recovered_by_system'}:raise ValueError('Accounting layers missing')
        if any(acc[k] is not None and type(acc[k]) is not bool for k in ('eligible_in_view','retrieved_in_production_bundle')):raise ValueError('Availability must be boolean or pending')
        if acc['retrieved_in_production_bundle'] is True and acc['eligible_in_view'] is False:raise ValueError('Retrieval cannot exceed eligibility')
    if fact['epistemic_category']=='guardrail_insufficiency' and any(fact['acceptable_action'][v]=='assert' for v in VIEWS):raise ValueError('Guardrail cannot assert the prohibited conclusion')
    if fact['claim_type']=='security_interpretation' and fact['epistemic_category'] not in ('weak_review_interpretation','guardrail_insufficiency'):raise ValueError('No strong positive security gold under current policy')
    return True


def summarize(templates,availability=None):
    """Only explicit reviewed rows count. Question judgments are never inferred."""
    totals=Counter();by_type=Counter();views={v:{'answerability':Counter(),'actions':Counter()} for v in VIEWS}
    checkable=Counter();questions={f'Q{i}':{v:Counter() for v in VIEWS} for i in range(1,8)}
    per_event=[];accounting=[];positive=set()
    for template in templates:
        eid=template['event_id'];facts=template['facts'];reviewed={};pending=0
        for f in facts:
            if validate_fact(f,eid):
                if f['gold_claim_id'] in reviewed:raise ValueError('Duplicate gold claim ID')
                reviewed[f['gold_claim_id']]=f
            else:pending+=1
        roots={};canonical={};numeric_pairs=set()
        def root_of(gid,visited=()):
            if gid in visited:raise ValueError('Alias cycle')
            if gid not in reviewed:raise ValueError('Alias target must be reviewed in same event')
            f=reviewed[gid]
            if not f['alias_of']:return gid
            return root_of(f['alias_of'],visited+(gid,))
        for gid,f in reviewed.items():
            root=root_of(gid);roots[gid]=root
            if root!=gid:
                base=reviewed[root]
                if f['fact_key']!=base['fact_key'] or any(f[v+'_answerability']!=base[v+'_answerability'] or f['acceptable_action'][v]!=base['acceptable_action'][v] for v in VIEWS):raise ValueError('Merged aliases need same adjudicated key and view decisions')
                continue
            if f['fact_key'] in canonical:raise ValueError('Same fact key without explicit merge or reasoned override')
            if f['claim_type'] in ('reported_change','electrical_change'):
                if f['key_kind'] not in ('reported_change','electrical_change'):raise ValueError('Numerical alias requires typed pair identity')
                numerical_key=propose_fact_key(eid,f['key_kind'],f['key_identity'])
                if numerical_key in numeric_pairs:raise ValueError('Same numerical pair/quantity cannot count twice via an override')
                numeric_pairs.add(numerical_key)
            canonical[f['fact_key']]=f
        totals['aliases_merged']+=len(reviewed)-len(canonical);totals['pending_rows']+=pending
        totals['reviewed_rows']+=len(reviewed);totals['unique_reviewed_facts']+=len(canonical)
        for f in canonical.values():
            kind='reported_change' if f['claim_type']=='electrical_change' else f['claim_type']
            by_type[kind]+=1;checkable[f['checkability']]+=1
            if f['epistemic_category']!='guardrail_insufficiency' and any(f[v+'_answerability']=='supported' and f['acceptable_action'][v]=='assert' for v in VIEWS):positive.add(kind)
            for v in VIEWS:
                views[v]['answerability'][f[v+'_answerability']]+=1;views[v]['actions'][f['acceptable_action'][v]]+=1
                row={'event_id':eid,'gold_claim_id':f['gold_claim_id'],'view':v,**f['view_accounting'][v]}
                if availability is not None:
                    eligible,retrieved=availability(eid,v);sets=f['minimal_support_sets'][v]
                    unknown={rid for s in sets for rid in s}-eligible
                    if unknown:raise ValueError('Support IDs outside full allowed view: '+str(sorted(unknown)))
                    row['mechanical_support_set_available_in_full_view']=any(set(s)<=eligible for s in sets) if sets else None
                    row['mechanical_support_set_in_production_bundle']=any(set(s)<=retrieved for s in sets) if sets else None
                    for human,mechanical in [('eligible_in_view','mechanical_support_set_available_in_full_view'),('retrieved_in_production_bundle','mechanical_support_set_in_production_bundle')]:
                        if row[human] is not None and row[mechanical] is not None and row[human]!=row[mechanical]:raise ValueError('Human accounting contradicts referenced support availability')
                accounting.append(row)
        qs=template['question_review']
        if {q['question_id'] for q in qs}!={f'Q{i}' for i in range(1,8)} or len(qs)!=7:raise ValueError('Exactly Q1-Q7 required')
        for q in qs:
            if q['review_status']=='HUMAN_REVIEWED':
                if not q['reviewer_id'] or not set(q['gold_claim_ids'])<=set(reviewed):raise ValueError('Question reviewer/references missing')
                for v in VIEWS:
                    if q['answerability'][v] not in ANSWERABILITY:raise ValueError('Missing question answerability')
                    questions[q['question_id']][v][q['answerability'][v]]+=1
            else:
                for v in VIEWS:questions[q['question_id']][v]['pending']+=1
        if template['signoff'] is not None:
            if not isinstance(template['signoff'],dict) or set(template['signoff'])!={'reviewer_id','reviewed_at','notes'} or not template['signoff']['reviewer_id'] or not template['signoff']['reviewed_at']:raise ValueError('Explicit human signoff identity/time required')
        complete=bool(template['signoff']) and not pending and all(q['review_status']=='HUMAN_REVIEWED' for q in qs)
        if template['signoff'] and not complete:raise ValueError('Cannot sign off incomplete template')
        totals['signed_off_events']+=complete
        per_event.append({'event_id':eid,'unique_reviewed_facts':len(canonical),'pending_rows':pending,'signed_off':complete})
    return {'status':'ANNOTATION_PENDING' if not totals['reviewed_rows'] else 'HUMAN_ANNOTATION_SUMMARY_NOT_SYSTEM_EVALUATION',
        'counts':{k:totals[k] for k in ('unique_reviewed_facts','reviewed_rows','aliases_merged','pending_rows','signed_off_events')},
        'unique_facts_by_canonical_claim_type':{k:by_type[k] for k in CLAIM_TYPES},
        'by_view':{v:{'answerability':{k:views[v]['answerability'][k] for k in ANSWERABILITY},'actions':{k:views[v]['actions'][k] for k in ACTIONS}} for v in VIEWS},
        'checkability':{'mechanically_checkable':checkable['mechanically_checkable']+checkable['both'],
            'requiring_human_semantic_judgment':checkable['human_semantic_judgment']+checkable['both'],'both':checkable['both'],
            'note':'Categories overlap for both; these are human judgments.'},
        'question_level_answerability':questions,'zero_usable_positive_types':[k for k in CLAIM_TYPES if k not in positive and k not in ('unknown','electrical_change')],
        'zero_positive_interpretation':'Provisional counts of reviewed annotations only; no annotations does not establish an unusable ontology.',
        'excluded_positive_types':{'unknown':'guardrail/insufficiency','electrical_change':'reported_change alias'},
        'per_event':per_event,'fact_view_accounting':accounting,'research_performance_metrics_computed':False,
        'recovered_by_system':'NOT_EVALUATED_PHASE2A'}
