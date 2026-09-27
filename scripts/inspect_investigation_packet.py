"""Read a blinded review packet using IDs/channel/time, without evaluator access."""
import argparse
import gzip
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('--evidence-id');p.add_argument('--channel');
    p.add_argument('--from-time',type=float,default=-60);p.add_argument('--to-time',type=float,default=60);p.add_argument('--limit',type=int,default=20)
    args=p.parse_args()
    if args.limit<1:raise ValueError('Positive output limit required')
    with gzip.open(args.packet/'complete_allowed_evidence.json.gz','rt') as f:bundle=json.load(f)
    rows=[r for r in bundle['records'] if (not args.evidence_id or r['evidence_id']==args.evidence_id)
          and (not args.channel or r['fields'].get('channel_id')==args.channel)
          and args.from_time<=r['observation_time']<args.to_time]
    print(json.dumps({'status':'DRAFT_UNREVIEWED','matching_records':len(rows),'returned_records':min(args.limit,len(rows)),
                      'records':rows[:args.limit]},indent=2,ensure_ascii=False))


if __name__=='__main__':main()
