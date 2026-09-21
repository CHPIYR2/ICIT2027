#!/usr/bin/env python3
"""Build audit tables and reviewable (not frozen) contracts/splits from local facts."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import zipfile

from audit_contents import ROOT, save

FAMILIES={
    'voltage': {'voltage','voltage_from','voltage_to','voltage_hv','voltage_lv'},
    'current': {'current_from','current_to','current_hv','current_lv'},
    'active_power': {'active_power','active_power_from','active_power_to','active_power_hv','active_power_lv'},
    'reactive_power': {'reactive_power','reactive_power_from','reactive_power_to','reactive_power_hv','reactive_power_lv'},
    'reported_state': {'is_closed','is_connected'},
}
UNITS={'voltage':'PER_UNIT','current':'AMPERE','active_power':'WATT','reactive_power':'VAR','reported_state':'NONE'}


def main():
    reports=[]
    catalog=[]
    fields=[]
    recording_table=[]
    for p in sorted((ROOT/'data/manifests/content_audit').glob('0*.json')):
        d=json.loads(p.read_text())
        assert d['status']=='complete',p
        reports.append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                        'archive_sha256':d['archive_sha256']})
        with zipfile.ZipFile(ROOT/f"data/raw/sherlock/v3/{d['scenario']}.zip") as z:
            for split,r in d['recordings'].items():
                assert not r['events']['label_disagreements'] and not r['events']['unresolved']
                assert not r['alignment']['events_outside_pcap_scope']
                for e in r['events']['events']:
                    key=f"sherlock-v3|{d['scenario']}|{split}|{e['id']}"
                    eid='ev_'+hashlib.sha256(key.encode()).hexdigest()[:20]
                    catalog.append({'episode_id':eid,'scenario':d['scenario'],'recording':split,
                                    'source_event_id':e['id'],'event_truth':'CYBER' if e['raw_malicious'] else 'BENIGN',
                                    'start':e['start'],'end':e['end'],'recovery':e.get('recovery'),
                                    'family_description':e['description'],
                                    'source_member':f"{d['scenario']}/ipal/{split}/events.json",
                                    'raw_start_match_confirmed':True})
                pcaps=r['pcaps']
                primary=next(n for n in pcaps if f"switch-{r['alignment']['state_vantage']}-" in n)
                mapping_member=f"{d['scenario']}/raw/{split}/data-point-map.json"
                mapping=json.loads(z.read(mapping_member))
                seen=set(pcaps[primary]['mapped_ca_ioas'])
                for ca_ioa,m in mapping.items():
                    family=next((k for k,v in FAMILIES.items() if m['attribute'] in v),None)
                    eligible=bool(family and m['context']=='MEASUREMENT' and m['unit']==UNITS[family])
                    fields.append({'scenario':d['scenario'],'recording':split,'source_member':mapping_member,
                                   'parent_packet_member':primary,'ca_ioa':ca_ioa,'asset':m['element'],
                                   'attribute':m['attribute'],'context':m['context'],'unit':m['unit'],'scale':m['scale'],
                                   'E_family_candidate':family if eligible else None,
                                   'candidate_E_allowed_if_observed':eligible,
                                   'seen_in_primary_segment_scoped_probe':ca_ioa in seen,
                                   'N_payload_allowed':False,'initial_value_allowed':False,
                                   'lineage_requirement':'archive SHA256 + member + packet index + APDU/object offset',
                                   'possible_leakage':'Do not expose scenario, recording, filenames, or initial_value to model.'})
                recording_table.append({'scenario':d['scenario'],'recording':split,'events':r['events']['count'],
                                        'cyber':r['events']['cyber'],'benign':r['events']['benign'],
                                        'pcap_files':len(pcaps),'pcap_records_all_vantages':sum(v['packets'] for v in pcaps.values()),
                                        'primary_vantage':r['alignment']['state_vantage'],'primary_pcap_member':primary,
                                        'state_rows':r['state']['rows'],'state_field_counts':r['state']['field_count_histogram'],
                                        'mapping_entries':len(mapping)})
    assert len(reports)==3
    assert len({e['episode_id'] for e in catalog})==len(catalog)
    catalog.sort(key=lambda e:e['episode_id'])
    catalog_path=ROOT/'data/evaluator/event_catalog.json'
    save(catalog_path,{'access':'EVALUATOR_ONLY; forbidden as features, retrieval, or LLM input',
                       'labels':'Raw procedure malicious flag cross-checked at exact IPAL start; recovery is not a new event.',
                       'events':catalog})
    save(ROOT/'data/manifests/field_catalog.proposed.json',{'status':'proposed','entries':fields})
    development=[e['episode_id'] for e in catalog if e['scenario']=='01-Basic']
    heldout=[e['episode_id'] for e in catalog if e['scenario']!='01-Basic']
    rng=random.Random(20270921)
    folds={eid:None for eid in development}
    for label in ['CYBER','BENIGN']:
        ids=[e['episode_id'] for e in catalog if e['episode_id'] in folds and e['event_truth']==label]
        rng.shuffle(ids)
        for i,eid in enumerate(ids):folds[eid]=i%5
    proposed={'version':'split-v1-proposal','status':'proposed_not_frozen','seed':20270921,
              'event_catalog_sha256':hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
              'development':development,'held_out':heldout,'development_fold_assignment':folds,
              'scope':'Basic train+test develop; Semiurban train+test and Rural test held out.',
              'development_cv':'5 folds stratified by event truth; all descendants of an episode stay together.',
              'episode_window_proposal':{'baseline_seconds_before_start':60,'decision_seconds_after_start':60,
                                          'bounds':'[start-60, start+60); decision issued at start+60',
                                          'scope_assets':'all observable mapped assets at the fixed control-center vantage; no attack_point filtering'},
              'restrictions':['No held-out fitting of imputation, scaling, thresholds, prompts, retrieval, or verifier policies.',
                              'No random row/packet split; folds are not independent simulation-run validation.',
                              'No cropping by gold end/recovery; no background-window inflation of benign sample counts.',
                              'Report all held-out recordings separately, including Semiurban train benign-only results.'],
              'window_overlap_checks':[]}
    # Check proposed fixed windows without changing them to accommodate test data.
    for row in recording_table:
        es=sorted((e for e in catalog if e['scenario']==row['scenario'] and e['recording']==row['recording']),key=lambda e:e['start'])
        collisions=[[a['episode_id'],b['episode_id']] for i,a in enumerate(es) for b in es[i+1:] if a['start']+60>b['start']-60]
        proposed['window_overlap_checks'].append({'scenario':row['scenario'],'recording':row['recording'],'overlapping_pairs':collisions})
    save(ROOT/'configs/split.proposed.json',proposed)
    contract={'version':'evidence-v1-proposal','status':'proposed_not_frozen',
              'decision_layer':'binary conventional ML; LLM explanation and verifier are later phases',
              'classifier_classes':['CYBER_RELATED','BENIGN_OPERATIONAL'],
              'final_insufficient_evidence':'Layer-3 sufficiency outcome, not a third training class',
              'E':{'source':'raw PCAP IEC-104 observed MEASUREMENT objects','attribute_families':{k:sorted(v) for k,v in FAMILIES.items()},
                   'units':UNITS,'exclude':['CONFIGURATION values','initial values','state.test','malicious','state aggregates without packet lineage'],
                   'missing_policy':'No observation => None plus missing flag; never turn missing into 0; preserve quality and last observation time.'},
              'N':{'source':'same raw PCAP, headers and protocol activity only',
                   'fields':['observation_time','source_endpoint','destination_endpoint','ip_protocol','source_port','destination_port',
                             'tcp_flags','apci_format','asdu_type','cause_of_transmission','packet_length'],
                   'excluded':['electrical/process payload values','setpoint values','gold event metadata'],
                   'note':'TCP ACK and IEC activation confirmation must remain distinct.'},
              'M':{'fields':['asset_mapping','ca_ioa_mapping','context','attribute','unit','scale','fixed_vantage_mapping'],
                   'constant_across_views':True,'exclude':['initial_value','scenario narrative','playbook','raw filenames']},
              'G':{'sources':['events.json','events.jsonl','physical.zip','sherlock-config.yml','malicious','attack_point','initial_state.json'],
                   'allowed':['isolated trainer target y','offline scoring','annotation','error analysis'],
                   'forbidden':['model X','runtime retrieval','LLM prompts','normal runtime tools']},
              'lineage':{'root_identity':['archive_sha256','member','packet_index'],
                         'derived_identity':['parent_ids','APDU index','object offset','transformation version'],
                         'source_file_visibility':'opaque source handle; raw path resolver stays outside model/LLM inputs',
                         'removal':'Remove descendants and recompute aggregates when a parent packet is hidden.'},
              'time_policy':'Use PCAP capture time in Unix seconds; simulator time is evaluator-only. No observations at/after the decision cutoff.',
              'runtime_enforcement_status':'not implemented in Phase 1; sanitizer/decoder tests required before experiments'}
    save(ROOT/'configs/evidence_contract.proposed.json',contract)
    summary={'status':'complete_with_documented_limitations','completed_at_utc':datetime.now(timezone.utc).isoformat(),
             'python':platform.python_version(),'platform':platform.platform(),'reports':reports,
             'recordings':recording_table,'events_total':len(catalog),'cyber_total':sum(e['event_truth']=='CYBER' for e in catalog),
             'benign_total':sum(e['event_truth']=='BENIGN' for e in catalog),
             'pcap_files':sum(r['pcap_files'] for r in recording_table),
             'pcap_records':sum(r['pcap_records_all_vantages'] for r in recording_table),
             'state_rows':sum(r['state_rows'] for r in recording_table),
             'coverage':{'PCAP':'every record','state':'every JSON row','IPAL_events':'every event, exact raw start/label cross-check',
                         'mappings_rules_initial_config_logs':'all files inspected; dataset code not executed',
                         'nested_physical_and_control_center':'all nested member headers; first useful member schema sampled; quarantined',
                         'diagrams':'SVG parsed and PDF bytes inventoried/hashed; PDFs not rendered'},
             'unknowns':['Historical IPAL transcriber commit','per-item lineage of distributed state aggregates','freshness of carried state values'],
             'protocol_status':'proposed, not frozen','model_training_started':False}
    save(ROOT/'data/manifests/content_audit/summary.json',summary)
    acquisition_path=ROOT/'data/manifests/acquisition_status.json'
    if acquisition_path.exists():
        acquisition=json.loads(acquisition_path.read_text())
        acquisition['semantic_audit_complete']=True
        acquisition['semantic_audit_completed_at_utc']=summary['completed_at_utc']
        acquisition['semantic_audit_scope']=summary['coverage']
        save(acquisition_path,acquisition)
    print(json.dumps({'events':len(catalog),'development':len(development),'held_out':len(heldout),'field_entries':len(fields)},indent=2))


if __name__=='__main__':main()
