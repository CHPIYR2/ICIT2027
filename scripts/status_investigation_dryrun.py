"""Read-only delivery progress; no claim contents or gold access."""
import collections,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]/'results/investigation-dryrun-v1'
a=json.loads((R/'transport_recovery_authorization.json').read_text());authorized={(x['event_id'],x['baseline'],x['repetition']) for x in a['cells']}
original=[];recovery=[];effective=[]
for p in (R/'runs').glob('*/*/*/rep-*/completed.json'):
 m=json.loads(p.read_text());cell=(m['event_id'],m['baseline'],m['repetition'])
 if m['run_id']==a['recovery_run_id']:recovery.append(m);effective.append(m)
 else:
  original.append(m)
  if cell not in authorized:effective.append(m)
def counts(rows):return dict(collections.Counter(m['status'] for m in rows))
print(json.dumps({'original_slots_finished':len(original),'original_statuses':counts(original),'recovery_slots_finished':len(recovery),'recovery_statuses':counts(recovery),'effective_slots_finished':len(effective),'effective_slots_remaining':144-len(effective),'effective_statuses':counts(effective)},indent=2))
