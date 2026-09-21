import unittest,json,math,sys
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
from test_evidence_pipeline import episode_fixture
from evidence.observability_v2 import transport_projection,public_evidence,visibility_receipt
from evidence.lineage import remove_sources
from features.network_transport_v2 import extract_transport,NAMES
from features.extract import extract
from run_observability_v2 import predictor_matrix,REGIMES
from sherlock.io import ROOT,read_json


def extended():
    e=episode_fixture();p=e.evidence_records[0]
    later=[replace(p,evidence_id='p_'+'3'*24,observation_time=120,fields={**p.fields,'tcp_flags':4}),
           replace(p,evidence_id='p_'+'4'*24,observation_time=159)]
    return replace(e,evidence_records=e.evidence_records+later).validate()


class ObservabilityTests(unittest.TestCase):
    def test_exact_feature_allowlist(self):
        self.assertEqual(list(read_json(ROOT/'configs/features.v2.json')['N_TRANSPORT']),NAMES)
        self.assertEqual(set(REGIMES.values()),set(read_json(ROOT/'configs/evaluation.v2.json')['regimes'])-{'N_FULL_T60'})

    def test_expected_rates_counts_and_actual_visible_duration(self):
        e=extended();full=transport_projection(e);short=full.restrict(15)
        f=extract_transport(short)
        self.assertAlmostEqual(f['nt_post_log_packet_rate'],math.log1p(1/15))
        self.assertAlmostEqual(f['nt_log_packet_rate_change'],math.log1p(1/15)-math.log1p(1/60))
        self.assertEqual(f['nt_rst_log_count'],0)
        self.assertAlmostEqual(f['nt_post_max_packet_gap_fraction'],10/15)
        self.assertEqual(extract_transport(full)['nt_rst_log_count'],math.log1p(1))

    def test_half_open_cutoff_and_no_recovery_of_hidden_packets(self):
        e=extended();p=replace(e.evidence_records[0],evidence_id='p_'+'5'*24,observation_time=115)
        e=replace(e,evidence_records=e.evidence_records+[p]);full=transport_projection(e)
        short=full.restrict(15)
        with self.assertRaises(PermissionError):short.lookup(p.evidence_id)
        with self.assertRaises(ValueError):short.restrict(60)
        with self.assertRaises(ValueError):full.restrict(0)
        with self.assertRaises(ValueError):full.restrict(20)

    def test_semantic_and_process_mutations_cannot_affect_transport(self):
        e=extended();baseline=extract_transport(transport_projection(e))
        changed=[]
        for r in e.evidence_records:
            if r.source_type=='message':r=replace(r,fields={'malicious':'forbidden','asdu_type':45,'cause_of_transmission':6})
            elif r.source_type=='process':r=replace(r,value=999.)
            changed.append(r)
        poisoned=replace(e,evidence_records=changed)
        self.assertEqual(extract_transport(transport_projection(poisoned)),baseline)
        roots=replace(e,evidence_records=[r for r in e.evidence_records if r.source_type=='packet'])
        self.assertEqual(extract_transport(transport_projection(roots)),baseline)

    def test_hidden_tail_mutation_invariant(self):
        e=extended();a=extract_transport(transport_projection(e).restrict(15))
        altered=replace(e,evidence_records=[replace(r,fields={**r.fields,'tcp_flags':255}) if r.source_type=='packet' and r.observation_time>=115 else r for r in e.evidence_records])
        self.assertEqual(a,extract_transport(transport_projection(altered).restrict(15)))

    def test_no_payload_size_uformat_or_parent_traversal_in_public_surface(self):
        e=extended();p=transport_projection(e).restrict(15)
        data=public_evidence(e,p,include_e=True)
        text=json.dumps(data)
        for forbidden in ['asdu_type','cause_of_transmission','apci_format','packet_length','parent_ids','source_file']:
            self.assertNotIn(forbidden,text)
        for r in e.evidence_records:
            if r.source_type=='message':
                with self.assertRaises(PermissionError):p.lookup(r.evidence_id)
        self.assertEqual([r['value'] for r in data['electrical']],[1.,.8])
        self.assertNotIn('electrical',public_evidence(e,p))

    def test_public_e_fails_closed_on_semantic_injection(self):
        e=extended();r=e.evidence_records[2]
        bad=replace(e,evidence_records=[replace(x,fields={**x.fields,'asdu_type':13}) if x.evidence_id==r.evidence_id else x for x in e.evidence_records])
        with self.assertRaises(ValueError):public_evidence(bad,transport_projection(e),True)

    def test_actual_source_removal_differs_from_view_restriction(self):
        e=extended();before=extract(e,'E');full=transport_projection(e)
        # Hide all post roots as a true source intervention, unlike export-view T15.
        raw=remove_sources(e,[r.evidence_id for r in e.evidence_records if r.source_type=='packet' and r.observation_time>=100])
        self.assertIsNone(extract(raw,'E')['e_voltage_relative_change'])
        full.restrict(15);self.assertEqual(extract(e,'E'),before)
        receipt=visibility_receipt(e,full)
        visible=set(receipt['levels']['15']['visible_packet_ids']);hidden=set(receipt['levels']['15']['hidden_packet_ids'])
        self.assertFalse(visible&hidden);self.assertEqual(visible|hidden,{p.evidence_id for p in full.packets})

    def test_observed_empty_interval_not_hidden_duration(self):
        e=episode_fixture();e=replace(e,evidence_records=[])
        f=extract_transport(transport_projection(e).restrict(30))
        self.assertEqual(f['nt_post_log_packet_rate'],0);self.assertEqual(f['nt_post_max_packet_gap_fraction'],1)

    def test_all_level_masks_nested_and_E_identical(self):
        e=extended();full=transport_projection(e);last=None;surface=None
        for t in [60,45,30,15]:
            p=full.restrict(t);ids={x.evidence_id for x in p.packets}
            if last is not None:self.assertTrue(ids<=last)
            last=ids;es=public_evidence(e,p,True)['electrical']
            if surface is not None:self.assertEqual(es,surface)
            surface=es

    def test_matrix_allowlist_and_numeric_only(self):
        e=extended();ev=extract(e,'E');nv=extract_transport(transport_projection(e))
        row={'E':ev,'network_regimes':{'N_TRANSPORT_T60':nv},'label':'ignored metadata'}
        x,names=predictor_matrix([row],'N_TRANSPORT_T60','EN')
        self.assertEqual(x.shape,(1,15));self.assertTrue(all(n.startswith(('e_','nt_')) for n in names))
        bad={**row,'network_regimes':{'N_TRANSPORT_T60':{**nv,'label':1}}}
        with self.assertRaises(ValueError):predictor_matrix([bad],'N_TRANSPORT_T60','N')

if __name__=='__main__':unittest.main()
