"""Read-only denominator binding for the four already-sealed development pilots."""
from .common import ROOT,load,file_hash
from .custody import require_development

MANIFEST_SHA='660ca033cd1c6a5bb9de98bb75c6a7ece5f28980716b9181152187e72c557d4a'

def pilot_contract(event_id,view):
    require_development(event_id)
    if view not in ('N','EN'):raise ValueError('Invalid primary view')
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
           'view_eligible':bool(f['view_accounting'][view]['eligible_in_view'])} for f in data['facts']]
    return {'event_id':event_id,'view':view,'gold_manifest_sha256':MANIFEST_SHA,'annotation_sha256':ref['sha256'],'gold':rows}
