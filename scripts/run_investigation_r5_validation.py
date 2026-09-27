"""Author-approved r5 validation entrypoint; predeclared manifest only."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_r5_live.adapter import run
p=argparse.ArgumentParser();p.add_argument('--key-file',required=True);a=p.parse_args();run(a.key_file)
