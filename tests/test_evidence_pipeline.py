import io
import json
import math
from pathlib import Path
import struct
import sys
import unittest
from dataclasses import replace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from evidence.schema import EvidenceEpisode,EvidenceRecord
from evidence.lineage import remove_sources
from features.extract import extract,FLOORS,E_NAMES,N_NAMES
from sherlock.build import sanitize_mapping
from sherlock.io import read_json,verify_protocol
from sherlock.parser import decode_apdus,Deduplicator,Packet,read_pcap
from sherlock.sanitizer import validate_features


def episode_fixture():
    base=dict(asset_id=None,reported_time=None,value=None,unit=None,source_file='src_'+'a'*20,
              vantage_point='vp_'+'b'*16,protocol='IEC104',quality_flags=(),transformation='pcap-iec104-v1',view='N')
    records=[]
    for i,(t,value) in enumerate([(90,1.),(110,.8)],1):
        p='p_'+str(i)*24;m='m_'+str(i)*24;e='e_'+str(i)*24
        records.append(EvidenceRecord(evidence_id=p,observation_time=t,source_type='packet',parent_ids=(),
            fields=dict(ip_protocol=6,source_endpoint='ep_'+'c'*16,destination_endpoint='ep_'+'d'*16,
                        source_port=2404,destination_port=5000,tcp_flags=24,packet_length=88),**base))
        records.append(EvidenceRecord(evidence_id=m,observation_time=t,source_type='message',parent_ids=(p,),
            fields=dict(apci_format='I',asdu_type=13,cause_of_transmission=3),**base))
        records.append(EvidenceRecord(evidence_id=e,observation_time=t,source_type='process',parent_ids=(m,),
            fields=dict(channel_id='ch_'+'e'*16,family='voltage',attribute='voltage',context='MEASUREMENT'),
            **{**base,'asset_id':'asset_'+'f'*16,'value':value,'unit':'PER_UNIT','view':'E'}))
    channels={'ch_'+'e'*16:dict(asset_id='asset_'+'f'*16,family='voltage',attribute='voltage',context='MEASUREMENT',unit='PER_UNIT',scale='NONE')}
    return EvidenceEpisode('ev_'+'0'*20,['asset_'+'f'*16],(40,160),100,records,channels).validate()


def apdu(type_id=13,value=1.,quality=0):
    obj=struct.pack('<fB',value,quality) if type_id==13 else bytes([int(value)])
    body=b'\x00'*4+bytes([type_id,1,3,0,1,0])+b'\x01\x00\x00'+obj
    return bytes([0x68,len(body)])+body


class PipelineTests(unittest.TestCase):
    def test_freeze_hashes(self):
        split,_=verify_protocol();self.assertEqual(len(split['development']),35)
        self.assertEqual(len(set(split['held_out'])),84)
        self.assertFalse(set(split['development'])&set(split['held_out']))

    def test_recipe_constants_match(self):
        d=read_json(ROOT/'configs/features.v1.json')
        self.assertEqual(d['E_numeric_relative_change']['floors'],FLOORS)
        self.assertEqual(d['N_order'],N_NAMES)
        self.assertEqual(len(E_NAMES),10)

    def test_decoder_quality_and_nan(self):
        x=decode_apdus(apdu(value=.8,quality=128))[0]['objects'][0]
        self.assertAlmostEqual(x['value'],.8,places=6);self.assertEqual(x['quality'],['invalid'])
        x=decode_apdus(apdu(value=math.nan))[0]['objects'][0]
        self.assertIsNone(x['value']);self.assertIn('nonfinite',x['quality'])

    def test_decoder_excludes_command_values(self):
        # Single command is structurally decoded but never exposed as a process measurement.
        self.assertEqual(decode_apdus(apdu(type_id=45,value=1))[0]['objects'],[])
        with self.assertRaises(ValueError):decode_apdus(apdu()[:-1])

    def test_decoder_sequence_addressing(self):
        body=b'\x00'*4+bytes([13,0x82,3,0,1,0])+b'\x01\x00\x00'+struct.pack('<fBfB',1.,0,2.,0)
        x=decode_apdus(bytes([0x68,len(body)])+body)[0]['objects']
        self.assertEqual([o['ca_ioa'] for o in x],['1.1','1.2'])

    def test_duplicate_and_conflicting_capture(self):
        d=Deduplicator();p=Packet(1,90,88,6,'a','b',2404,5000,24,1000,apdu())
        self.assertFalse(d.retransmission(p))
        self.assertTrue(d.retransmission(replace(p,index=2,timestamp=91)))
        self.assertFalse(d.retransmission(replace(p,index=3,timestamp=92,payload=apdu(value=2.))))
        self.assertIn(1,d.conflicting_packet_indices)
        self.assertFalse(d.retransmission(replace(p,index=4,timestamp=93,payload=apdu()+apdu())))

    def test_mapping_strips_secrets(self):
        row=dict(element='bus.1',context='MEASUREMENT',attribute='voltage',unit='PER_UNIT',scale='NONE',initial_value=123,description='secret attack label')
        channels,lookup=sanitize_mapping({'1.1':row,'1.2':{**row,'context':'CONFIGURATION'}},read_json(ROOT/'configs/evidence_contract.v1.json'),'src_'+'a'*20)
        self.assertEqual(len(channels),1);self.assertNotIn('secret',json.dumps(channels));self.assertNotIn('initial_value',json.dumps(channels))

    def test_features_missing_and_views(self):
        e=episode_fixture();full=extract(e)
        self.assertAlmostEqual(full['e_voltage_relative_change'],.2)
        self.assertIsNone(full['e_current_relative_change'])
        self.assertEqual(full['e_voltage_post_missing'],0)
        self.assertEqual({**extract(e,'E'),**extract(e,'N')},full)
        altered=replace(e,evidence_records=[replace(r,value=999.) if r.view=='E' else r for r in e.evidence_records])
        self.assertEqual(extract(e,'N'),extract(altered,'N'))

    def test_source_removal_recomputes_descendants(self):
        e=episode_fixture();removed=remove_sources(e,['p_'+'2'*24])
        self.assertEqual(len(removed.evidence_records),3)
        f=extract(removed)
        self.assertIsNone(f['e_voltage_relative_change']);self.assertEqual(f['e_voltage_post_missing'],1)
        self.assertEqual(f['n_post_log_rate'],0)
        self.assertEqual(f['n_post_max_gap_fraction'],1)

    def test_scope_and_forbidden_fields_fail_closed(self):
        e=episode_fixture()
        for modified in [replace(e.evidence_records[-1],observation_time=160),
                         replace(e.evidence_records[-1],source_file='Basic/test/attack.pcap'),
                         replace(e.evidence_records[-1],fields={**e.evidence_records[-1].fields,'malicious':True}),
                         replace(e.evidence_records[-1],parent_ids=('m_'+'9'*24,))]:
            with self.assertRaises(ValueError):replace(e,evidence_records=e.evidence_records[:-1]+[modified]).validate()
        with self.assertRaises(ValueError):validate_features({**extract(e),'label':1},E_NAMES+N_NAMES)
        self.assertEqual(EvidenceEpisode.from_dict(e.to_dict()).to_dict(),e.to_dict())

    def test_missing_imputer_is_train_only_and_contributions_sum(self):
        import numpy as np
        from triage.baseline import make_pipeline,contributions
        cfg=read_json(ROOT/'configs/models.v1.json')
        x=np.array([[1.,np.nan],[2.,np.nan],[3.,np.nan],[4.,np.nan]])
        pipeline=make_pipeline('logistic_regression',cfg).fit(x,[0,0,1,1])
        stats=pipeline['missing'].transformer_list[0][1].statistics_.copy()
        test=np.array([[1000.,8.],[np.nan,np.nan]])
        score=pipeline.decision_function(test)
        cs=contributions(pipeline,test,['a','b'])
        np.testing.assert_allclose([c['intercept']+sum(c['log_odds_contributions'].values()) for c in cs],score)
        np.testing.assert_array_equal(pipeline['missing'].transformer_list[0][1].statistics_,stats)
        np.testing.assert_allclose(stats,[2.5,0])


if __name__=='__main__':unittest.main()
