"""Versioned cell routing and read-only development bundle checks."""
from investigation_dryrun.common import ROOT, load, digest, dumps, file_hash, binding
from investigation_dryrun.custody import require_development, development_ids
from investigation_dryrun.tokens import count
from retrieval.investigation_retriever_v2 import validate_bundle

CONFIG=ROOT/'configs/investigation-r5'
OUT=ROOT/'results/investigation-r5'
BUDGETS={'E':{'E':64,'N':0},'N':{'E':0,'N':64},'EN':{'E':32,'N':32}}

def cell_spec(cell):
    matrix=load(CONFIG/'matrix.json')['cells']
    if cell not in matrix:raise ValueError('Unknown r5 cell')
    return matrix[cell]

def validate_input(bundle,receipt):
    validate_bundle(bundle);scope=bundle['scope'];require_development(scope['event_id']);v=scope['view']
    if v not in BUDGETS:raise ValueError('Unknown view')
    if receipt['event_id']!=scope['event_id'] or receipt['view']!=v or receipt['retrieved_bundle_sha256']!=digest(bundle):raise ValueError('Receipt binding mismatch')
    if receipt['budget']!=BUDGETS[v] or receipt['max_bytes']!=48000:raise ValueError('Retrieval policy drift')
    size=len(dumps(bundle).encode())
    if size!=receipt['serialized_bundle_bytes'] or size>48000:raise ValueError('Byte budget failure')
    counts={d:sum(r['view']==d for r in bundle['entries']) for d in ('E','N')}
    if any(counts[d]>BUDGETS[v][d] for d in counts):raise ValueError('Entry quota failure')
    channels={r['fields']['channel_id'] for r in bundle['entries'] if r['source_type']=='process'}
    mids={r['mapping_evidence_id'] for r in bundle['entries'] if r['source_type']=='command_address_observation' and r['mapping_evidence_id']}
    if set(bundle['metadata'])!=channels or set(bundle['control_metadata'])!=mids:raise ValueError('Unnecessary or hidden metadata')
    if v=='E' and (counts['N'] or bundle['control_metadata']):raise ValueError('Hidden N support')
    if v=='N' and (counts['E'] or bundle['metadata']):raise ValueError('Hidden E support')
    for row in bundle['entries']:
        if row['view']=='N' and row['source_type']=='derived' and row.get('value') is not None:raise ValueError('Unexpected process value in derived N')
    tokens=count(dumps(bundle))
    if tokens>16384:raise ValueError('Input evidence safety ceiling; no reselection')
    return {'evidence_tokens':tokens,'serialized_bytes':size,'entry_counts':counts,'status':'PASS'}

def read_bundle(event_id,view):
    require_development(event_id)
    if view not in BUDGETS:raise ValueError('Unknown view')
    base=ROOT/'results/investigation-v2/B0'/event_id/view
    paths=[base/'retrieved.json',base/'receipt.json']
    for p in paths:
        if p.resolve()!=p.absolute():raise PermissionError('Symlink forbidden')
    audit=OUT/'input_audit.json'
    if audit.exists():
        row=next(x for x in load(audit)['rows'] if x['event_id']==event_id and x['view']==view)
        for ref in row['source_files']:
            if file_hash(ROOT/ref['path'])!=ref['sha256']:raise ValueError('Pinned input changed')
    b,r=map(load,paths)
    if b['scope']['event_id']!=event_id or b['scope']['view']!=view:raise ValueError('Wrong input context')
    validate_input(b,r)
    return b,r

def prompt_for(cell):
    spec=cell_spec(cell)
    if spec['action']!='generation':raise ValueError('Cell has no generation prompt')
    m=load(ROOT/'prompts/investigation-v1-r5/manifest.json');ref=m['prompts'][cell];p=ROOT/ref['path']
    if file_hash(p)!=ref['sha256']:raise ValueError('Prompt changed')
    text=p.read_text()
    if spec['citation_mode']=='required':
        t=m['template'];tp=ROOT/t['path']
        if file_hash(tp)!=t['sha256'] or text!=tp.read_text().replace('{VIEW}',spec['view']):raise ValueError('Required prompt drift')
    return text,ref
