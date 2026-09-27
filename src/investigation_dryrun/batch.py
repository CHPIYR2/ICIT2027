"""Create-once development batch, pinned before any provider call, resumable.

No gold reader, score selection, prompt changes, or evaluation execution route.
"""
import concurrent.futures
import hashlib
import os
from pathlib import Path
from .common import ROOT,load,create_json,file_hash,utc
from .custody import development_ids
from . import runner

PREFLIGHT=ROOT/'results/investigation-dryrun-v1/preflight_manifest.json'
BATCH_ID='authorized-dev-v1-r4'

def verify_preflight():
    m=load(PREFLIGHT)
    for ref in m['files']:
        if file_hash(ROOT/ref['path'])!=ref['sha256']:raise ValueError('Preflight binding changed: '+ref['path'])
    if m['development_event_ids']!=list(development_ids()) or m['planned_generation_cells']!=144:raise ValueError('Preflight plan drift')
    if m['protocol_frozen'] or m['evaluation_authorized']:raise ValueError('Not a development-only preflight')
    return m

def expected_cells():
    return [(eid,b,rep) for eid in development_ids() for b in ('B1','B2','B3') for rep in (1,2,3)]

def cell_dir(cell):
    eid,b,rep=cell;return runner.RUNS/BATCH_ID/eid/b/f'rep-{rep}'

def verify_completed(cell):
    p=cell_dir(cell);m=load(p/'completed.json');eid,b,rep=cell
    if (m['event_id'],m['baseline'],m['repetition'],m['run_id'])!=(eid,b,rep,BATCH_ID):raise ValueError('Completed cell identity mismatch')
    if (p/'output.raw.json').exists() and file_hash(p/'output.raw.json')!=m.get('output_sha256'):raise ValueError('Stored output changed')
    for attempt in m['attempts']:
        ap=p/f"attempt-{attempt['attempt']}"
        if load(ap/'attempt.json')!=attempt:raise ValueError('Attempt manifest mismatch')
        if 'response_sha256' in attempt and file_hash(ap/'response.raw')!=attempt['response_sha256']:raise ValueError('Provider response changed')
    return m

def run(workers=3):
    verify_preflight()
    if not os.environ.get('OPENAI_API_KEY'):raise RuntimeError('OPENAI_API_KEY is not configured; no provider requests made')
    if type(workers) is not int or not 1<=workers<=4:raise ValueError('Concurrency must be 1..4')
    pending=[]
    for cell in expected_cells():
        p=cell_dir(cell)
        if (p/'completed.json').exists():verify_completed(cell)
        elif p.exists():raise RuntimeError('Interrupted cell requires reconciliation; will not regenerate or overwrite: '+str(p))
        else:pending.append(cell)
    batch_root=runner.RUNS/BATCH_ID;batch_root.mkdir(parents=True,exist_ok=True)
    started=batch_root/'batch_started.json'
    if not started.exists():create_json(started,{'started_at':utc(),'preflight_sha256':file_hash(PREFLIGHT),'planned_cells':144,'workers':workers,'protocol_frozen':False})
    elif load(started)['preflight_sha256']!=file_hash(PREFLIGHT):raise ValueError('Batch preflight changed')
    def execute(cell):
        verify_preflight()
        eid,b,rep=cell
        return runner.generate(eid,b,rep,BATCH_ID)
    if len(pending)==144:
        first=execute(pending.pop(0))
        print(first['event_id'],first['baseline'],first['repetition'],first['status'],flush=True)
        if first['status'] in ('TERMINAL_HTTP_FAILURE','RUNNER_CONFIGURATION_OR_IMPLEMENTATION_FAILURE','MODEL_IDENTIFIER_MISMATCH','FAILED_NO_VALID_DELIVERY'):
            raise RuntimeError('Initial delivery failed; batch stopped for infrastructure diagnosis; retained first cell is not retried or overwritten')
    # Provider requests are independent; every repetition is retained. No adaptive tuning.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(execute,c):c for c in pending}
        for f in concurrent.futures.as_completed(futures):
            m=f.result();print(m['event_id'],m['baseline'],m['repetition'],m['status'],flush=True)
    for eid in development_ids():
        for rep in (1,2,3):
            p=batch_root/eid/'B4'/f'rep-{rep}'/'replay.json'
            if not p.exists():runner.replay(eid,rep,BATCH_ID)
            replay=load(p);m=verify_completed((eid,'B3',rep))
            if replay['B3_input_sha256']!=m.get('output_sha256') or replay['llm_calls']!=0:raise ValueError('B4 identity mismatch')
    verify_preflight()
    return {'generation_cells':len(expected_cells()),'B4_replays':48,'protocol_frozen':False}
