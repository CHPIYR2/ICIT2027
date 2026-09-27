"""Execute only the explicitly authorized, preflight-bound r6 development manifest."""
import argparse,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ['TIKTOKEN_CACHE_DIR']=str(ROOT/'.cache/tiktoken')
from investigation_r6_live.adapter import run
p=argparse.ArgumentParser();p.add_argument('--key-file',required=True);a=p.parse_args();run(a.key_file)
