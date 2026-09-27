"""Summarize reviewed pilot annotations only; never run system-vs-gold metrics."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import json
from functools import lru_cache
from sherlock.io import ROOT,read_json,sha256
from investigation.review_phase2a import pilot_ids,summarize,support_index


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=ROOT/'annotations/phase2a/pilots')
    p.add_argument('--filename',default='reviewer_annotation.BLANK.json');p.add_argument('--output',type=Path)
    args=p.parse_args()
    if Path(args.filename).name!=args.filename:raise ValueError('Filename must be a basename')
    templates=[]
    for eid in pilot_ids():
        template=read_json(args.directory/eid/args.filename)
        if template['event_id']!=eid:raise ValueError('Expected frozen pilot event')
        packet=ROOT/'annotations/events-v2'/eid
        if template['source_packet_manifest_sha256']!=sha256(packet/'manifest.json') or template['full_universe_sha256']!=sha256(packet/'complete_allowed_evidence.json.gz'):raise ValueError('Worksheet provenance mismatch')
        templates.append(template)
    @lru_cache(None)
    def availability(eid,view):return set(support_index(eid,view)),set(support_index(eid,view,production=True))
    result=summarize(templates,availability)
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.output:
        # Never write into immutable evidence, reviewer files, or final-gold trees.
        destination=args.output.resolve();allowed=(ROOT/'results/investigation-phase2a').resolve()
        if allowed not in destination.parents:raise ValueError('Summary output must be in results/investigation-phase2a/')
        destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('x') as f:f.write(text)
    else:print(text,end='')


if __name__=='__main__':main()
