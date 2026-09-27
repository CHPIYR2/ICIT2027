"""Explicit development-only entry point. No evaluation execution mode."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from investigation_dev.runner import plan, generate, replay
from investigation_dev.common import create_json, load, file_hash
from investigation_dev.metrics import score_reviewed_run
from investigation_dev.statistics import aggregate

p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
s.add_parser('plan')
for a in ('generate','replay'):
 q=s.add_parser(a);q.add_argument('--event',required=True);q.add_argument('--repetition',type=int,choices=(1,2,3),required=True);q.add_argument('--run-id',required=True)
 if a=='generate':q.add_argument('--baseline',choices=('B1','B2','B3'),required=True)
q=s.add_parser('score');q.add_argument('--event',required=True);q.add_argument('--ledger',required=True);q.add_argument('--output',required=True);q.add_argument('--save',required=True)
q=s.add_parser('aggregate');q.add_argument('--cells',required=True);q.add_argument('--strata',required=True);q.add_argument('--metric',required=True);q.add_argument('--save',required=True)
a=p.parse_args()
if a.action=='plan':result=plan()
elif a.action=='generate':result=generate(a.event,a.baseline,a.repetition,a.run_id)
elif a.action=='replay':result=replay(a.event,a.repetition,a.run_id)
elif a.action=='score':
 from investigation_dev.custody import require_development
 require_development(a.event)
 # Review paths must be under the isolated development results tree.
 root=Path(__file__).resolve().parents[1]/'results/investigation-development-v1'
 for name in (a.ledger,a.output,a.save):
  if not Path(name).resolve().is_relative_to(root):raise PermissionError('Development result path required')
 ledger=load(a.ledger)
 if ledger['event_id']!=a.event:raise ValueError('Ledger event mismatch')
 from investigation_dev.gold_contract import pilot_contract
 result=score_reviewed_run(ledger,file_hash(a.output),pilot_contract(a.event,'N' if ledger['baseline']=='B1' else 'EN'));create_json(a.save,result)
else:
 root=Path(__file__).resolve().parents[1]/'results/investigation-development-v1'
 for name in (a.cells,a.strata,a.save):
  if not Path(name).resolve().is_relative_to(root):raise PermissionError('Development result path required')
 result=aggregate(load(a.cells),a.metric,load(a.strata));create_json(a.save,result)
print(json.dumps(result,indent=2))
