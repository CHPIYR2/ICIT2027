"""Inspect all approved pilot evidence, with explicit production-only opt-in."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import argparse
import json
from investigation.review_phase2a import load_universe,support_index


def main():
    p=argparse.ArgumentParser();p.add_argument('event_id');p.add_argument('--view',choices=('E','N','EN'),default='EN')
    p.add_argument('--production',action='store_true');p.add_argument('--evidence-id');p.add_argument('--asset');p.add_argument('--channel')
    p.add_argument('--source-type');p.add_argument('--from-time',type=float,default=-60);p.add_argument('--to-time',type=float,default=60)
    p.add_argument('--offset',type=int,default=0);p.add_argument('--limit',type=int,default=20);p.add_argument('--all',action='store_true')
    args=p.parse_args()
    if args.offset<0 or args.limit<1:raise ValueError('Invalid pagination')
    public=load_universe(args.event_id,args.view,args.production)
    if args.evidence_id:
        index=support_index(args.event_id,args.view,args.production);rows=[index[args.evidence_id]] if args.evidence_id in index else []
    else:
        rows=[r for r in public['records'] if (not args.asset or r.get('asset_id',r.get('mapped_target_asset_id'))==args.asset)
            and (not args.channel or r.get('fields',{}).get('channel_id')==args.channel)
            and (not args.source_type or r['source_type']==args.source_type)
            and args.from_time<=r['observation_time']<args.to_time]
        rows.sort(key=lambda r:(r['observation_time'],r['evidence_id']))
    visible=rows[args.offset:] if args.all else rows[args.offset:args.offset+args.limit]
    channels={r.get('fields',{}).get('channel_id') for r in visible};mapping_ids={r.get('mapping_evidence_id') for r in visible}
    result={'status':'EVIDENCE_INSPECTION_NOT_HUMAN_GOLD','event_id':args.event_id,'view':args.view,
        'source':'PRODUCTION_RETRIEVAL' if args.production else 'FULL_APPROVED_UNIVERSE',
        'total_matching':len(rows),'returned':len(visible),'offset':args.offset,'next_offset':args.offset+len(visible) if args.offset+len(visible)<len(rows) else None,
        'records':visible,'channel_metadata':{c:m for c,m in public['metadata'].items() if c in channels},
        'control_metadata':{mid:m for mid,m in public['control_metadata'].items() if mid in mapping_ids}}
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
