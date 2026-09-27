import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from investigation.fact_keys_phase2a import propose_fact_key,duplicate_proposals
from investigation.review_phase2a import blank_fact,summarize,validate_fact,load_universe,VIEWS

EID='ev_'+'0'*20
E1='e_'+'1'*24
E2='e_'+'2'*24


def fact(gid='g_1',kind='reported_value'):
    f=blank_fact(EID)
    f.update(gold_claim_id=gid,question_ids=['Q2'],claim_type=kind,epistemic_category='observation',
        atomic_statement='Synthetic test fixture only.',reviewer_id='test-human',review_status='HUMAN_REVIEWED',
        checkability='mechanically_checkable',alias_decision='distinct',key_kind=kind,
        key_identity={'record_id':E1} if kind=='reported_value' else {'before_id':E1,'after_id':E2,'quantity':'difference','unit':'WATT'})
    f['proposed_fact_key']=propose_fact_key(EID,kind,f['key_identity']);f['fact_key']=f['proposed_fact_key']
    for v in VIEWS:
        f[v+'_answerability']='insufficient' if v=='N' else 'supported'
        f['acceptable_action'][v]='withhold' if v=='N' else 'assert'
        f['minimal_support_sets'][v]=[] if v=='N' else [[E1]]
    return f


def template(facts):
    return {'event_id':EID,'facts':facts,'signoff':None,'question_review':[{'question_id':f'Q{i}',
        'answerability':{v:None for v in VIEWS},'gold_claim_ids':[],'reviewer_id':None,'review_status':'UNREVIEWED'} for i in range(1,8)]}


class HumanGoldPreparationTests(unittest.TestCase):
    def test_blank_has_required_human_fields_unfilled(self):
        f=blank_fact(EID)
        for key in ('gold_claim_id','claim_type','epistemic_category','atomic_statement','fact_key','E_answerability','N_answerability','EN_answerability','reviewer_id'):self.assertIsNone(f[key])
        self.assertFalse(validate_fact(f,EID));self.assertEqual(f['minimal_support_sets'],{v:[] for v in VIEWS})

    def test_blank_summary_not_gold_or_performance(self):
        result=summarize([template([])])
        self.assertEqual(result['status'],'ANNOTATION_PENDING');self.assertEqual(result['counts']['unique_reviewed_facts'],0)
        self.assertFalse(result['research_performance_metrics_computed']);self.assertEqual(result['question_level_answerability']['Q1']['E']['pending'],1)

    def test_numeric_alias_same_key_and_direction_distinct(self):
        identity={'before_id':E1,'after_id':E2,'quantity':'difference','unit':'WATT'}
        key=propose_fact_key(EID,'reported_change',identity)
        self.assertEqual(key,propose_fact_key(EID,'electrical_change',identity))
        self.assertNotEqual(key,propose_fact_key(EID,'reported_change',{**identity,'before_id':E2,'after_id':E1}))
        self.assertNotEqual(key,propose_fact_key(EID,'reported_change',{**identity,'quantity':'percent_change'}))

    def test_key_event_scope_and_namespace(self):
        self.assertNotEqual(propose_fact_key(EID,'reported_value',{'record_id':E1}),propose_fact_key('ev_'+'1'*20,'reported_value',{'record_id':E1}))
        with self.assertRaises(ValueError):propose_fact_key(EID,'reported_value',{'record_id':'a_'+'1'*24})
        with self.assertRaises(ValueError):propose_fact_key(EID,'security_interpretation',{})

    def test_command_strengths_not_merged(self):
        m='m_'+'1'*24;weak=propose_fact_key(EID,'command_observed',{'message_id':m})
        strong=propose_fact_key(EID,'mapped_command_observed',{'message_id':m,'address_id':'a_'+'1'*24,'mapping_id':'meta_'+'1'*24,'asset_id':'asset_'+'1'*16,'control_point_id':'cp_'+'1'*16})
        self.assertNotEqual(weak,strong)

    def test_equal_timestamp_symmetry_precedes_directionality(self):
        d={'earlier_id':E1,'later_id':E2,'relation':'same_capture_time','scope':'episode_only','mapping_ids':[],'asset_id':None}
        swapped={**d,'earlier_id':E2,'later_id':E1}
        self.assertEqual(propose_fact_key(EID,'temporal_association',d),propose_fact_key(EID,'temporal_association',swapped))
        self.assertNotEqual(propose_fact_key(EID,'temporal_association',{**d,'relation':'precedes'}),propose_fact_key(EID,'temporal_association',{**swapped,'relation':'precedes'}))

    def test_duplicate_proposal_not_merge(self):
        rows=[{'candidate_id':'x','proposed_fact_key':'fk_same'},{'candidate_id':'y','proposed_fact_key':'fk_same'}]
        group=duplicate_proposals(rows)[0];self.assertIsNone(group['decision']);self.assertEqual(group['status'],'DRAFT_UNREVIEWED')

    def test_explicit_alias_counted_once(self):
        a=fact(kind='reported_change');b=fact('g_2','electrical_change');b.update(alias_of='g_1',alias_decision='merge_alias',alias_rationale='Same underlying numerical pair/quantity.')
        result=summarize([template([a,b])]);self.assertEqual(result['counts']['aliases_merged'],1)
        self.assertEqual(result['unique_facts_by_canonical_claim_type']['reported_change'],1)
        self.assertEqual(result['by_view']['E']['actions']['assert'],1)

    def test_unresolved_duplicate_and_alias_cycles_fail(self):
        a=fact();b=fact('g_2')
        with self.assertRaises(ValueError):summarize([template([a,b])])
        a.update(alias_of='g_2',alias_decision='merge_alias',alias_rationale='test');b.update(alias_of='g_1',alias_decision='merge_alias',alias_rationale='test')
        with self.assertRaises(ValueError):summarize([template([a,b])])

    def test_override_cannot_double_count_numeric_alias(self):
        a=fact(kind='reported_change');b=fact('g_2','electrical_change');b.update(fact_key='human_other',key_override_reason='test override')
        with self.assertRaises(ValueError):summarize([template([a,b])])

    def test_override_requires_reason(self):
        f=fact();f['fact_key']='human_1'
        with self.assertRaises(ValueError):validate_fact(f,EID)
        f['key_override_reason']='Reviewed distinct proposition';self.assertTrue(validate_fact(f,EID))

    def test_recovery_never_inferred_from_availability(self):
        result=summarize([template([fact()])],lambda eid,v:({E1},{E1}) if v!='N' else (set(),set()))
        e=next(r for r in result['fact_view_accounting'] if r['view']=='E')
        self.assertTrue(e['mechanical_support_set_in_production_bundle']);self.assertIsNone(e['recovered_by_system'])
        self.assertIsNone(e['eligible_in_view'])

    def test_full_eligible_not_production_is_distinct(self):
        result=summarize([template([fact()])],lambda eid,v:({E1},set()) if v!='N' else (set(),set()))
        e=next(r for r in result['fact_view_accounting'] if r['view']=='E')
        self.assertTrue(e['mechanical_support_set_available_in_full_view']);self.assertFalse(e['mechanical_support_set_in_production_bundle'])

    def test_missing_support_and_hidden_ids_rejected(self):
        f=fact();f['minimal_support_sets']['E']=[]
        with self.assertRaises(ValueError):validate_fact(f,EID)
        with self.assertRaises(ValueError):summarize([template([fact()])],lambda eid,v:(set(),set()))

    def test_accounting_contradiction_and_recovery_rejected(self):
        f=fact();f['view_accounting']['E']['retrieved_in_production_bundle']=True
        with self.assertRaises(ValueError):summarize([template([f])],lambda eid,v:({E1},set()))
        f=fact();f['view_accounting']['E']['recovered_by_system']=True
        with self.assertRaises(ValueError):validate_fact(f,EID)

    def test_question_answerability_is_independent(self):
        result=summarize([template([fact()])]);self.assertEqual(result['question_level_answerability']['Q2']['E']['pending'],1)
        t=template([fact()]);q=t['question_review'][1];q.update(review_status='HUMAN_REVIEWED',reviewer_id='test-human',gold_claim_ids=['g_1'],answerability={'E':'supported','N':'insufficient','EN':'supported'})
        result=summarize([t]);self.assertEqual(result['question_level_answerability']['Q2']['E']['supported'],1)

    def test_signed_off_requires_completed_questions(self):
        t=template([fact()]);t['signoff']={'reviewer_id':'test-human','reviewed_at':'test-time','notes':'test'}
        with self.assertRaises(ValueError):summarize([t])

    def test_strong_security_positive_rejected(self):
        f=fact();f['claim_type']='security_interpretation'
        with self.assertRaises(ValueError):validate_fact(f,EID)

    def test_ambiguous_alias_not_final(self):
        f=fact();f['alias_decision']='ambiguous'
        with self.assertRaises(ValueError):validate_fact(f,EID)

    def test_evaluation_event_access_rejected_before_file_read(self):
        with self.assertRaises(ValueError):load_universe('ev_eda32c84a9cf2952b292')


if __name__=='__main__':unittest.main()
