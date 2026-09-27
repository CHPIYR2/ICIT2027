"""Authorized development-only batch; never launch evaluation or freeze."""
import argparse
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.batch import run,verify_preflight
p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','run','report']);p.add_argument('--workers',type=int,default=3);p.add_argument('--env-file',type=Path)
a=p.parse_args()
if a.env_file:
    # Explicit local path only, no shell sourcing or credential logging.
    secret_text=a.env_file.read_text().strip()
    if secret_text.startswith('sk-') and '\n' not in secret_text:
        os.environ['OPENAI_API_KEY']=secret_text
    for line in secret_text.splitlines():
        k,sep,v=line.removeprefix('export ').partition('=')
        if sep and k.strip()=='OPENAI_API_KEY':os.environ['OPENAI_API_KEY']=v.strip().strip('\"\'')
if a.action=='run':print(json.dumps(run(a.workers),indent=2))
elif a.action=='verify':print(json.dumps({'status':'PASS','bindings':len(verify_preflight()['files']),'API_key_present':bool(os.environ.get('OPENAI_API_KEY')),'protocol_frozen':False},indent=2))
else:
    from investigation_dryrun.report import report
    print(json.dumps(report(),indent=2))
