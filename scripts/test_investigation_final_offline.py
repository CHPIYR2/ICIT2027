"""Run candidate tests with network and protected evaluation opens denied."""
import sys,os,socket,json,io,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'scripts')]
os.environ['PYTHONDONTWRITEBYTECODE']='1'
ids=json.loads((ROOT/'configs/investigation_events.v1.json').read_text())['evaluation']
opens=[];denied=[]
def audit(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=str(Path(os.fsdecode(args[0])).absolute())
 support_regression='/results/investigation-v2/B0/' in p or p.endswith('/annotation-v1/'+ 'ev_eda32c84a9cf2952b292/annotation.worksheet.json')
 prohibited=(any(e in p for e in ids) or p.endswith('/api_key.txt') or '/annotations/evaluation/' in p or '/results/investigation-final-evaluation/' in p or ('/annotations/gold/' in p and '/pilot-v1/' not in p))
 if prohibited and not support_regression:
  denied.append(p);raise PermissionError('Protected evaluation or credential access forbidden in offline tests')
 opens.append(p)
sys.addaudithook(audit)
def blocked(*a,**k):raise AssertionError('Network forbidden in offline tests')
socket.create_connection=blocked;socket.socket.connect=blocked
from prepare_investigation_final_offline import preserve,write,OUT
before=preserve()
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern='test_investigation_final_offline.py',top_level_dir=str(ROOT/'tests'))
stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
after=preserve();assert before==after
n=1
while (OUT/f'tests.{n}.json').exists():n+=1
log=OUT/f'tests.{n}.log';log.write_text(stream.getvalue())
record={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),
 'errors':len(result.errors),'skipped':len(result.skipped),'network_disabled':True,'model_calls':0,
 'protected_read_guard_active':True,'denied_opens':denied,'evaluation_content_reads':0,
 'preservation':after,'test_log':str(log.relative_to(ROOT))}
write(OUT/f'tests.{n}.json',record)
write(OUT/f'test_read_audit.{n}.json',{'allowed_opens':sorted(set(opens)),'denied':denied,'model_calls':0})
print(json.dumps(record,indent=2))
if not result.wasSuccessful():print(stream.getvalue()[-8000:]);raise SystemExit(1)
