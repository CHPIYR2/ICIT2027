"""Retrieval-support dispatch for exact, existential, and role-based gold facts.

Concrete acceptable_support_sets stay on the fact. They are the retrieval
definition only for EXACT. Existential and role-based facts are retrieved from
visible record predicates. This module does not inspect event or gold IDs.
"""
TIME_OPERATORS=('gte','gt','lt','lte')
FORMS=('EXACT','EXISTENTIAL','ROLE_BASED')

def need(ok,message):
    if not ok: raise ValueError(message)

def support_form(fact):
    form=fact.get('fields',{}).get('support_form','EXACT')
    need(form in FORMS,'Unknown support form')
    return form

def _time_matches(value,bounds):
    need(isinstance(bounds,dict) and bounds and set(bounds)<=set(TIME_OPERATORS),'Malformed observation_time predicate')
    if isinstance(value,bool) or not isinstance(value,(int,float)): return False
    checks={'gte':value>=bounds['gte'] if 'gte' in bounds else True,
            'gt':value>bounds['gt'] if 'gt' in bounds else True,
            'lt':value<bounds['lt'] if 'lt' in bounds else True,
            'lte':value<=bounds['lte'] if 'lte' in bounds else True}
    return all(checks[k] for k in bounds)

def project(record):
    fields=record.get('fields') if isinstance(record.get('fields'),dict) else {}
    context=record.get('context',fields.get('context'))
    return {'source_type':record.get('source_type'),'protocol':record.get('protocol'),
            'context':context,'quality_flags':record.get('quality_flags'),
            'observation_time':record.get('observation_time')}

def record_matches(record,predicate):
    need(isinstance(predicate,dict) and predicate,'Empty support predicate')
    projected=project(record)
    for key,expected in predicate.items():
        if key=='observation_time':
            if not _time_matches(projected['observation_time'],expected): return False
        elif key not in projected or projected[key]!=expected:
            return False
    return True

def bundle_records(bundle,visible):
    """Return visible record projections, or None when the bundle has none.

    EXACT facts do not require records. Existential and role-based facts do.
    """
    if 'visible_records' not in bundle: return None
    records=bundle['visible_records']
    need(isinstance(records,list),'Visible records must be a list')
    ids=[]
    for record in records:
        need(isinstance(record,dict) and isinstance(record.get('evidence_id'),str) and record['evidence_id'],'Visible record missing evidence_id')
        ids.append(record['evidence_id'])
    need(len(ids)==len(set(ids)),'Duplicate visible records')
    need(set(ids)<=visible,'Visible record outside visible evidence IDs')
    return records

def materialize_support_fields(fields):
    """Store the support form implied by an already accepted proposition.

    Named evidence IDs stay exact. A stored window without a named evidence ID
    is existential. Stored before/after role flags are role-based. The scorer
    reads the stored form and does not call this function.
    """
    fields=dict(fields)
    if fields.get('support_form') in FORMS: return fields
    if 'before_evidence_id' in fields or 'metadata_evidence_id' in fields:
        fields['support_form']='EXACT'
        return fields
    if fields.get('requires_network_observation_before_anchor'):
        anchor=fields.get('anchor_time',0)
        measurement={'source_type':'process','context':'MEASUREMENT','quality_flags':fields.get('quality_flags',[]),'observation_time':None}
        message={'source_type':'message','protocol':'IEC104','observation_time':None}
        def role(base,lower,upper,lower_op,upper_op):
            item=dict(base);item['observation_time']={lower_op:lower,upper_op:upper};return item
        fields['support_form']='ROLE_BASED'
        fields['support_roles']=[
            role(message,-60,anchor,'gte','lt'),role(message,anchor,60,'gt','lt'),
            role(measurement,-60,anchor,'gte','lt'),role(measurement,anchor,60,'gt','lt')]
        return fields
    if fields.get('requires_observation_before_anchor'):
        common={'source_type':fields['source_type'],'protocol':fields['protocol']}
        anchor=fields['anchor_time']
        fields['support_form']='ROLE_BASED'
        fields['support_roles']=[
            {**common,'observation_time':{'gte':fields['interval_start'],'lt':anchor}},
            {**common,'observation_time':{'gt':anchor,'lt':fields['interval_end']}}]
        return fields
    if 'window_start' in fields:
        predicate={'source_type':fields['source_type'],'observation_time':{'gte':fields['window_start'],'lt':fields['window_end']}}
        if 'protocol' in fields: predicate['protocol']=fields['protocol']
        if 'context' in fields: predicate['context']=fields['context']
        if fields.get('source_type')=='process': predicate['quality_flags']=fields.get('quality_flags',[])
        fields['support_form']='EXISTENTIAL'
        fields['support_predicate']=predicate
        return fields
    fields['support_form']='EXACT'
    return fields

def retrieval_supported(fact,view,visible_ids,records):
    """Gold-fact retrieval predicate for one scored view."""
    if not fact['views'][view]['supportable']: return False
    form=support_form(fact)
    if form=='EXACT':
        return any(set(support)<=set(visible_ids) for support in fact['views'][view]['acceptable_support_sets'])
    need(records is not None,'Existential and role-based retrieval requires visible records')
    visible=[r for r in records if r['evidence_id'] in visible_ids]
    if form=='EXISTENTIAL':
        predicate=fact['fields'].get('support_predicate')
        return any(record_matches(r,predicate) for r in visible)
    roles=fact['fields'].get('support_roles')
    need(isinstance(roles,list) and roles,'Role-based fact requires support roles')
    return all(any(record_matches(r,role) for r in visible) for role in roles)
