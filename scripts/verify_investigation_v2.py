"""Offline artifact audit; no network, LLM, evaluator labels, or gold generation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
import gzip
import json
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256
from retrieval.evidence_formatter import digest
from retrieval.evidence_formatter_v2 import validate_public,validate_visibility,base_export
from retrieval.investigation_retriever_v2 import retrieve,validate_bundle
from retrieval.investigation_retriever import difference,largest_gap
from investigation.timeline_v2 import timeline
from investigation.support_v2 import validate_supported_claim
from run_timeline_baseline_v2 import verify_locks

OUT=ROOT/'results/investigation-v2'


def gz(path):
    with gzip.open(path,'rt') as f:return json.load(f)


def main():
    verify_locks();manifest=read_json(OUT/'baseline_manifest.json');counts=Counter();inventories=[]
    if manifest['llm_calls']!=0 or manifest['conditions']!=144:raise ValueError('Wrong authorized stage')
    for row in manifest['rows']:
        for path,expected in row['files'].items():
            if sha256(ROOT/path)!=expected:raise ValueError('Output hash mismatch: '+path)
        eid=row['event_id'];view=row['view'];dest=OUT/'B0'/eid/view
        public=gz(dest/'eligible.json.gz');bundle=read_json(dest/'retrieved.json');receipt=read_json(dest/'receipt.json');report=read_json(dest/'timeline.json')
        validate_public(public);validate_visibility(read_json(dest/'visibility.json'),public);validate_bundle(bundle)
        # The complete canonical E/N projection must exactly equal the prior public universe.
        previous=gz(ROOT/'results/investigation-v1/B0'/eid/view/'eligible.json.gz')
        canonical=base_export(public);canonical['scope']=dict(canonical['scope']);canonical['scope']['command_target_mapping']=previous['scope']['command_target_mapping']
        if canonical!=previous:raise ValueError('Prior E/N evidence changed')
        regenerated,replayed_receipt=retrieve(public)
        if (regenerated,replayed_receipt)!=(bundle,receipt):raise ValueError('Nondeterministic or stale retrieval')
        if timeline(bundle,receipt)!=report:raise ValueError('B0 replay differs')
        original={r['evidence_id']:r for r in public['records']};retrieved={r['evidence_id']:r for r in bundle['entries']}
        for rid,r in retrieved.items():
            if r['source_type']=='derived':
                expected=largest_gap(public) if r['fields']['kind']=='communication_gap' else difference(*[original[p] for p in r['parent_ids']])
                if r!=expected:raise ValueError('Derived evidence calculation mismatch')
            elif r!=original[rid]:raise ValueError('Retrieved observation altered')
        for c in report['amendment_claims']:
            validate_supported_claim(c,bundle)
            counts[view+'_'+c['claim_type']]+=1
            if c['claim_type']=='temporal_association':
                p=c['payload'];a=original[p['earlier_id']];e=original[p['later_id']]
                # Independent exact time and both-edge checks, separate from the B0 helper.
                cm=public['control_metadata'][a['mapping_evidence_id']];em=public['metadata'][e['fields']['channel_id']]
                assert a['mapping_status']=='exact_static_match' and a['cause_of_transmission']==6 and e['value'] is not None and not e['quality_flags']
                assert cm['asset_id']==em['asset_id']==e['asset_id']==a['mapped_target_asset_id']==p['mapped_asset_id']
                assert p['delta_seconds']==e['observation_time']-a['observation_time']>0
        assert report['review_status']=='DRAFT_UNREVIEWED' and report['security_interpretation']==[]
        assert report['accounting']['final_recovered_gold_facts'] is None
        assert not any(u['subject']=='reported_state_change' for u in report['unknowns'])
        if view=='EN':
            addresses=[r for r in public['records'] if r['source_type']=='command_address_observation']
            es=[r for r in public['records'] if r['source_type']=='process' and r['value'] is not None and not r['quality_flags']]
            for a in addresses:
                same=[e for e in es if e['asset_id']==a['mapped_target_asset_id']]
                counts['address_children']+=1;counts['exact_mapped_children']+=a['mapping_status']=='exact_static_match'
                counts['same_asset_valid_E_children']+=bool(same);counts['same_asset_later_valid_E_children']+=any(e['observation_time']>a['observation_time'] for e in same)
                if a['cause_of_transmission']==6:
                    counts['request_children']+=1;counts['same_asset_valid_E_requests']+=bool(same)
                    counts['same_asset_later_valid_E_requests']+=any(e['observation_time']>a['observation_time'] for e in same)
        counts['conditions_checked']+=1
    pilots=read_json(ROOT/'configs/investigation_pilots.v1.json')['event_ids']
    for eid in pilots:
        folder=ROOT/'annotations/events-v2'/eid;pm=read_json(folder/'manifest.json')
        for name,expected in pm['files'].items():
            if sha256(folder/name)!=expected:raise ValueError('Packet hash mismatch')
        annotation=read_json(folder/'annotation.DRAFT.json');assert annotation['signoff'] is None and annotation['facts']==[]
        public=gz(folder/'complete_allowed_evidence.json.gz');edges=gz(folder/'allowed_lineage.json.gz')
        assert public==gz(OUT/'B0'/eid/'EN/eligible.json.gz')
        assert set(edges)=={r['evidence_id'] for r in public['records']}
        assert all(set(parents)<=set(edges) for parents in edges.values())
        counts['pilot_packets_checked']+=1
    result={'status':'PASS','stage':'PHASE1_B0_ONLY','tests':read_json(OUT/'test_results.json'),'counts':dict(counts),
        'checks':['old classification and Phase1 locks unchanged','all 144 canonical E/N projections identical to v1','all output hashes','retrieval and B0 deterministic replay',
            'address/message/static mapping closure','namespace and cross-view checks','derived arithmetic and gap queries','both static asset edges and capture-time arithmetic','all four packet hashes and lineage closure'],
        'llm_calls':0,'human_gold_events':0,'formal_protocol_frozen':False}
    save_json(OUT/'verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
