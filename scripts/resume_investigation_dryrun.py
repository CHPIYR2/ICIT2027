"""Rate-paced infrastructure continuation; no exhausted-cell retry or score tuning."""
import argparse,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,create_json,binding,file_hash,utc
from investigation_dryrun.batch import verify_preflight,expected_cells,cell_dir,BATCH_ID,verify_completed
from investigation_dryrun.runner import OpenAITransport,generate,replay,RUNS
from investigation_dryrun.transport_resume import continue_started
from investigation_dryrun.custody import development_ids
p=argparse.ArgumentParser();p.add_argument('--key-file',type=Path,required=True);a=p.parse_args()
secret=a.key_file.read_text().strip()
if secret.startswith('sk-') and '\n' not in secret:os.environ['OPENAI_API_KEY']=secret
else:
 for line in secret.splitlines():
  k,sep,v=line.removeprefix('export ').partition('=')
  if k.strip()=='OPENAI_API_KEY' and sep:os.environ[k.strip()]=v.strip().strip('\"\'')
if not os.environ.get('OPENAI_API_KEY'):raise SystemExit('Credential format unavailable')
OUT=ROOT/'results/investigation-dryrun-v1'
record=OUT/'transport_pacing_amendment.json'
if not record.exists():
 create_json(record,{'created_at':utc(),'kind':'IMPLEMENTATION_INFRASTRUCTURE_DEFECT_CORRECTION','observed_limit_TPM':30000,'finding':'Concurrent requests and fixed short backoff exhausted delivery budgets under account rate limits. No model semantics prompted this correction.','action':'One request at a time; minimum 60 seconds between request starts, including authorized transport retries. Original attempt maximum remains three. Delivered outputs are not regenerated. The separately authorized 86 exclusively rate-limited failures use a distinct recovery batch with identical requests.','protocol_semantics_unchanged':True,'files':[binding(ROOT/'scripts/resume_investigation_dryrun.py'),binding(ROOT/'src/investigation_dryrun/transport_resume.py'),binding(OUT/'transport_recovery_authorization.json')],'preflight_sha256':file_hash(OUT/'preflight_manifest.json')})
for ref in load(record)['files']:
 if file_hash(ROOT/ref['path'])!=ref['sha256']:raise ValueError('Transport continuation drift')
class PacedTransport(OpenAITransport):
 def __init__(self):self.last=None
 def __call__(self,request,client_id,timeout):
  if self.last is not None:
   remaining=60-(time.monotonic()-self.last)
   if remaining>0:time.sleep(remaining)
  self.last=time.monotonic()
  return super().__call__(request,client_id,timeout)
transport=PacedTransport()
verify_preflight()
for cell in expected_cells():
 path=cell_dir(cell)
 if (path/'completed.json').exists():verify_completed(cell);continue
 verify_preflight()
 if path.exists():m=continue_started(path,transport)
 else:m=generate(*cell,BATCH_ID,transport=transport)
 print(m['event_id'],m['baseline'],m['repetition'],m['status'],flush=True)
for eid in development_ids():
 for rep in (1,2,3):
  path=RUNS/BATCH_ID/eid/'B4'/f'rep-{rep}'/'replay.json'
  if not path.exists():replay(eid,rep,BATCH_ID)
verify_preflight()
recovery=load(OUT/'transport_recovery_authorization.json');recovery_id=recovery['recovery_run_id']
if len(recovery['cells'])!=86:raise ValueError('Recovery authorization scope changed')
for cell in recovery['cells']:
 eid,b,rep=cell['event_id'],cell['baseline'],cell['repetition'];original=verify_completed((eid,b,rep))
 if original['status']!='FAILED_NO_VALID_DELIVERY' or len(original['attempts'])!=3 or not all(x.get('HTTP_status')==429 for x in original['attempts']):raise ValueError('Recovery attempted on non-authorized output')
 directory=RUNS/recovery_id/eid/b/f'rep-{rep}'
 if (directory/'completed.json').exists():continue
 if directory.exists():raise RuntimeError('Recovery interrupted; manual reconciliation needed')
 verify_preflight()
 m=generate(eid,b,rep,recovery_id,transport=transport)
 if load(directory/'request.json')!=load(cell_dir((eid,b,rep))/'request.json'):raise ValueError('Recovery request differs from original')
 print('RECOVERY',eid,b,rep,m['status'],flush=True)
 if b=='B3':replay(eid,rep,recovery_id)
verify_preflight()
from investigation_dryrun.report import report
create_json(OUT/'dryrun_conformance.json',report())
print('Completed original 144 cells and 86 authorized transport-recovery cells; all outputs retained.',flush=True)
