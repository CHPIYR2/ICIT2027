"""Read-only denominator binding for the four already-sealed development pilots."""
from investigation_dryrun.common import ROOT,load,file_hash,digest
from .core import require_development, read_bundle

MANIFEST_SHA='660ca033cd1c6a5bb9de98bb75c6a7ece5f28980716b9181152187e72c557d4a'

def pilot_contract(event_id,view):
    require_development(event_id)
    if view not in ('E','N','EN'):raise ValueError('Invalid primary view')
    path=ROOT/'annotations/gold/pilot-v1/manifest.json'
    if file_hash(path)!=MANIFEST_SHA:raise ValueError('Gold manifest changed')
    manifest=load(path);event=next((e for e in manifest['events'] if e['event_id']==event_id),None)
    if event is None:raise ValueError('No sealed human gold for this development event; do not invent a denominator')
    ref=event['annotation'];path=ROOT/ref['snapshot_path']
    if file_hash(path)!=ref['sha256']:raise ValueError('Gold annotation changed')
    data=load(path);byid={f['gold_claim_id']:f for f in data['facts']}
    def canonical(f):
        seen=set()
        while f.get('alias_of'):
            if f['gold_claim_id'] in seen:raise ValueError('Gold alias cycle')
            seen.add(f['gold_claim_id']);f=byid[f['alias_of']]
        return f['gold_claim_id']
    rows=[{'gold_id':f['gold_claim_id'],'canonical_gold_id':canonical(f),
           'kind':'guardrail' if f['epistemic_category']=='guardrail_insufficiency' else 'positive',
           'view_eligible':f['view_accounting'][view]['eligible_in_view'],
           'retrieved_support':f['view_accounting'][view]['retrieved_in_production_bundle']} for f in data['facts']]
    for r in rows:
        if type(r['view_eligible']) is not bool:raise ValueError('Pending view eligibility')
        if r['kind']=='positive' and r['view_eligible'] and type(r['retrieved_support']) is not bool:raise ValueError('Eligible positive retrieval accounting is pending')
        if r['retrieved_support'] is not None and type(r['retrieved_support']) is not bool:raise ValueError('Invalid retrieval accounting')
    return {'event_id':event_id,'view':view,'gold_manifest_sha256':MANIFEST_SHA,'annotation_sha256':ref['sha256'],'gold':rows, 'bundle_sha256':digest(read_bundle(event_id,view)[0]), 'question_answerability':{q['question_id']:q['answerability'][view] for q in data['question_review']}}
