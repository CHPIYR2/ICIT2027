"""Fail closed before file access: only existing development bundle/receipt paths."""
from pathlib import Path
from .common import ROOT, load, file_hash, digest, dumps, utc
from retrieval.investigation_retriever_v2 import validate_bundle

SPLIT = ROOT / 'configs/investigation_events.v1.json'
SPLIT_SHA256 = 'cee7286d3acd4c70a9e21325ee566690cf3663684521a81f86549ae2f6f8dc2c'

def development_ids():
    if file_hash(SPLIT) != SPLIT_SHA256:
        raise ValueError('Event split changed')
    return tuple(load(SPLIT)['development'])

def require_development(event_id):
    if event_id not in development_ids():
        raise PermissionError('Development-only execution: event is not authorized')

def log_access(log_path, action, event_id, path=None, sha256=None):
    # This application log is auditable, not an OS-level access-control guarantee.
    p = Path(log_path); p.parent.mkdir(parents=True, exist_ok=True)
    previous = None
    if p.exists():
        lines = p.read_text().splitlines()
        if lines: previous = __import__('json').loads(lines[-1])['entry_sha256']
    item = {'at': utc(), 'action': action, 'event_id': event_id,
            'path': str(path) if path else None, 'file_sha256': sha256, 'previous_entry_sha256': previous}
    item['entry_sha256'] = digest(item)
    with p.open('a') as f: f.write(dumps(item) + '\n')

def verify_access_log(log_path):
    previous = None
    for line in Path(log_path).read_text().splitlines():
        item = __import__('json').loads(line); h = item.pop('entry_sha256')
        if item['previous_entry_sha256'] != previous or digest(item) != h:
            raise ValueError('Access-log chain mismatch')
        previous = h
    return previous

def read_bundle(event_id, view, log_path):
    # No caller-supplied data path, fallback split, evaluation switch or symlink escape.
    if event_id not in development_ids():
        log_access(log_path, 'DENIED_NON_DEVELOPMENT', event_id)
        raise PermissionError('Development-only execution')
    if view not in ('N', 'EN'): raise ValueError('Primary views are N and EN')
    base = ROOT / 'results/investigation-v2/B0' / event_id / view
    paths = [base / 'retrieved.json', base / 'receipt.json']
    audit_path=ROOT/'results/investigation-development-v1/token_budget_audit.json'
    pinned={}
    if audit_path.exists():
        rows=[row for row in load(audit_path)['rows'] if row['event_id']==event_id and row['view']==view]
        if len(rows)!=1:raise ValueError('Missing audited development input binding')
        pinned={x['path']:x['sha256'] for x in rows[0]['source_files']}
    for path in paths:
        if path.resolve() != path.absolute():
            log_access(log_path,'DENIED_SYMLINK',event_id,path);raise PermissionError('Symlink data path forbidden')
        if pinned and file_hash(path)!=pinned.get(str(path.relative_to(ROOT))):
            log_access(log_path,'DENIED_CHANGED_INPUT',event_id,path,file_hash(path));raise ValueError('Audited development input changed')
        log_access(log_path, 'READ_APPROVED_DEVELOPMENT_EVIDENCE', event_id, path, file_hash(path))
    bundle, receipt = map(load, paths)
    validate_bundle(bundle)
    if bundle['scope']['event_id'] != event_id or bundle['scope']['view'] != view:
        raise ValueError('Bundle event/view mismatch')
    if receipt['event_id'] != event_id or receipt['view'] != view or digest(bundle) != receipt['retrieved_bundle_sha256']:
        raise ValueError('Receipt mismatch')
    if len(dumps(bundle).encode()) != receipt['serialized_bundle_bytes'] or receipt['max_bytes'] != 48000:
        raise ValueError('Serialization contract mismatch')
    if receipt['budget'] != ({'E': 0, 'N': 64} if view == 'N' else {'E': 32, 'N': 32}):
        raise ValueError('Retrieval budget changed')
    return bundle, receipt
