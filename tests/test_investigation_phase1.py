import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from test_evidence_pipeline import episode_fixture, apdu
from evidence.lineage import remove_sources
from retrieval.evidence_formatter import export_episode,digest,validate_public
from retrieval.investigation_retriever import retrieve,difference,largest_gap,fact_accounting,BUDGETS
from investigation.timeline import timeline
from investigation.pilot_audit import supportability
from audit_command_targets import command_addresses
from sherlock.parser import decode_apdus


class InvestigationPhase1Tests(unittest.TestCase):
    def test_view_exports_are_field_scoped_and_have_no_parent_resolver(self):
        episode=episode_fixture()
        e,private=export_episode(episode,'E');n,_=export_episode(episode,'N')
        self.assertEqual({r['source_type'] for r in e['records']},{'process'})
        self.assertEqual({r['source_type'] for r in n['records']},{'packet','message'})
        self.assertNotIn('cause_of_transmission',json.dumps(e))
        for word in ['source_file','parent_ids','initial_value','malicious','attack_point','raw_path']:
            self.assertNotIn(word,json.dumps(e))
        self.assertTrue(private['records'])
        self.assertTrue(all(r['value'] is None for r in n['records']))

    def test_N_invariant_to_E_values(self):
        episode=episode_fixture();n,_=export_episode(episode,'N')
        altered=replace(episode,evidence_records=[replace(r,value=99.) if r.view=='E' else r for r in episode.evidence_records])
        self.assertEqual(n,export_episode(altered,'N')[0])

    def test_E_invariant_to_hidden_network_semantics(self):
        episode=episode_fixture();e,_=export_episode(episode,'E')
        altered=replace(episode,evidence_records=[replace(r,fields={**r.fields,'cause_of_transmission':7}) if r.source_type=='message' else r for r in episode.evidence_records])
        self.assertEqual(e,export_episode(altered,'E')[0])

    def test_injected_fields_and_cross_view_fail_closed(self):
        public,_=export_episode(episode_fixture(),'E')
        changed=copy.deepcopy(public);changed['records'][0]['fields']['malicious']=True
        with self.assertRaises(ValueError):retrieve(changed)
        n,_=export_episode(episode_fixture(),'N')
        changed=copy.deepcopy(public);changed['records'].append(n['records'][0])
        with self.assertRaises(ValueError):retrieve(changed)

    def test_source_removal_removes_E_but_view_restriction_does_not(self):
        episode=episode_fixture();removed=remove_sources(episode,['p_'+'2'*24])
        self.assertEqual(len(export_episode(removed,'E')[0]['records']),1)
        self.assertEqual(len(export_episode(episode,'E')[0]['records']),2)

    def test_future_observation_and_bad_asset_rejected(self):
        public,_=export_episode(episode_fixture(),'E')
        for key,value in [('observation_time',60),('asset_id','asset_'+'0'*16)]:
            bad=copy.deepcopy(public);bad['records'][0][key]=value
            with self.assertRaises(ValueError):validate_public(bad)

    def test_exact_pair_calculation_and_zero_baseline(self):
        public,_=export_episode(episode_fixture(),'E');a,b=public['records']
        d=difference(a,b)
        self.assertAlmostEqual(d['fields']['difference'],-.2)
        self.assertAlmostEqual(d['fields']['percent_change'],-20.)
        a=copy.deepcopy(a);a['value']=0
        self.assertIsNone(difference(a,b)['fields']['percent_change'])
        self.assertEqual(difference(a,b)['fields']['percent_unavailable_reason'],'zero_baseline')

    def test_pair_invalid_unit_asset_time_quality_rejected(self):
        public,_=export_episode(episode_fixture(),'E');a,b=public['records']
        for key,value in [('unit','WATT'),('asset_id','asset_'+'0'*16),('observation_time',a['observation_time']),('quality_flags',['invalid'])]:
            bad=copy.deepcopy(b);bad[key]=value
            with self.assertRaises(ValueError):difference(a,bad)

    def test_retrieval_is_deterministic_atomic_and_within_budgets(self):
        for view in ('E','N','EN'):
            public,_=export_episode(episode_fixture(),view)
            one,receipt=retrieve(public);two,again=retrieve(public)
            self.assertEqual(one,two);self.assertEqual(receipt,again)
            self.assertLessEqual(receipt['serialized_bundle_bytes'],48000)
            for domain,n in receipt['retrieved_by_domain'].items():self.assertLessEqual(n,BUDGETS[view][domain])
            ids={r['evidence_id'] for r in one['entries']}
            for r in one['entries']:
                if r['source_type']=='derived':self.assertTrue(set(r['parent_ids'])<=ids)
            self.assertIsNone(receipt['final_recovered_investigation_facts'])

    def test_byte_truncation_preserves_dependencies(self):
        public,_=export_episode(episode_fixture(),'EN')
        bundle,receipt=retrieve(public,max_bytes=2000)
        ids={r['evidence_id'] for r in bundle['entries']}
        self.assertLessEqual(receipt['serialized_bundle_bytes'],2000)
        for r in bundle['entries']:
            if r['source_type']=='derived':self.assertTrue(set(r['parent_ids'])<=ids)

    def test_gap_uses_complete_eligible_population(self):
        public,_=export_episode(episode_fixture(),'N')
        gap=largest_gap(public)
        self.assertEqual(gap['fields']['eligible_count'],2)
        self.assertEqual(gap['fields']['duration_seconds'],50)
        self.assertTrue(gap['fields']['left_censored'])
        self.assertTrue(gap['fields']['complete_visible_query'])

    def test_empty_N_is_explicit_capture_gap_not_outage(self):
        episode=replace(episode_fixture(),evidence_records=[])
        public,_=export_episode(episode,'N');bundle,receipt=retrieve(public)
        self.assertEqual(receipt['eligible_original_count'],0)
        gap=bundle['entries'][0]
        self.assertEqual(gap['fields']['duration_seconds'],120)
        self.assertIn('not proof of outage',gap['fields']['interpretation'])

    def test_B0_no_security_narrative_and_no_measured_recovery(self):
        public,_=export_episode(episode_fixture(),'EN');bundle,receipt=retrieve(public)
        report=timeline(bundle,receipt)
        self.assertEqual(report['security_interpretation'],[])
        self.assertEqual(report['review_status'],'DRAFT_UNREVIEWED')
        self.assertEqual(len(report['numerical_differences']),1)
        self.assertIsNone(report['accounting']['final_recovered_gold_facts'])
        self.assertTrue(any(r['subject']=='causal_link' for r in report['unknowns']))

    def test_B0_tampered_bundle_rejected(self):
        public,_=export_episode(episode_fixture(),'EN');bundle,receipt=retrieve(public)
        bundle['entries'][0]['observation_time']+=1
        with self.assertRaises(ValueError):timeline(bundle,receipt)

    def test_three_way_fact_accounting_never_infers_recovery(self):
        self.assertEqual(fact_accounting([['a','b']],['a','b'],['a']),{'supportable_from_eligible_universe':True,'complete_support_retrieved':False,'correctly_recovered_by_system':None})
        with self.assertRaises(ValueError):fact_accounting([['b']],['a'],['b'])

    def test_supportability_is_not_gold_or_security_truth(self):
        public,_=export_episode(episode_fixture(),'EN');audit=supportability(public)
        self.assertEqual(len(audit['rows']),13)
        self.assertTrue(all(r['human_confirmed_supportable_examples'] is None for r in audit['rows']))
        self.assertEqual(next(r for r in audit['rows'] if r['claim_type']=='security_interpretation')['supportable_candidate_examples'],0)

    def test_raw_address_audit_skips_command_value(self):
        first=apdu(type_id=45,value=0);second=apdu(type_id=45,value=1)
        a=command_addresses(first,decode_apdus(first)[0]);b=command_addresses(second,decode_apdus(second)[0])
        self.assertEqual(a,b);self.assertEqual(a,[{'ca':1,'ioa':1,'object_index':0}])
        self.assertNotIn('value',a[0])

    def test_raw_address_sequential_and_nonsequential(self):
        for sequential in (False,True):
            body=b'\0'*4+bytes([45,(0x80 if sequential else 0)|2,6,0,1,0])+b'\x01\x00\x00'+b'\0'
            body+=(b'' if sequential else b'\x02\x00\x00')+b'\1'
            payload=bytes([0x68,len(body)])+body
            addresses=command_addresses(payload,decode_apdus(payload)[0])
            self.assertEqual([a['ioa'] for a in addresses],[1,2])

    def test_frozen_event_counts_and_phase1_policy(self):
        events=json.loads((ROOT/'configs/investigation_events.v1.json').read_text())
        config=json.loads((ROOT/'configs/investigation.phase1.json').read_text())
        self.assertEqual(len(events['development']),16);self.assertEqual(len(events['evaluation']),32)
        self.assertFalse(set(events['development'])&set(events['evaluation']))
        self.assertEqual(config['budget'],BUDGETS)
        self.assertFalse(config['llm_calls_authorized']);self.assertFalse(config['command_target_amendment_enabled'])


if __name__=='__main__':unittest.main()
