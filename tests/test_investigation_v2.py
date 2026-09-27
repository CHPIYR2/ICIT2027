import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from test_evidence_pipeline import episode_fixture
from evidence.command_address_v2 import static_mapping,address_children,parse_addresses
from retrieval.evidence_formatter_v2 import export_episode,validate_public
from retrieval.investigation_retriever_v2 import retrieve,validate_bundle
from retrieval.investigation_retriever import difference
from investigation.schema_v2 import validate,check,schema,require_id,validate_claim_shape
from investigation.timeline_v2 import timeline
from investigation.support_v2 import validate_supported_claim
from investigation.pilot_audit_v2 import supportability


def packet(kind=45,ioa=1,count=1,sequential=False,fill=0):
    size={45:1,47:1,50:5}[kind]
    objects=b''.join((b'' if sequential and i else (ioa+i).to_bytes(3,'little'))+bytes([fill])*size for i in range(count))
    body=b'\x00'*4+bytes([kind,count|(128 if sequential else 0),6,0,1,0])+objects
    return bytes([104,len(body)])+body


def mapping(raw=None):
    return static_mapping(raw or b'{"1.1":{"element":"private.bus","context":"CONFIGURATION","attribute":"closed","initial_value":999,"family":"secret"}}','src_'+'a'*20)


def fixture(view='EN',raw=None,payload=None):
    ep=episode_fixture();mp=mapping(raw);asset=next(iter(mp['public_metadata'].values()))['asset_id'] if mp['public_metadata'] else ep.assets[0] if hasattr(ep,'assets') else 'asset_'+'f'*16
    records=[replace(r,fields={**r.fields,'asdu_type':45,'cause_of_transmission':6}) if r.evidence_id=='m_'+'1'*24 else replace(r,asset_id=asset) if r.view=='E' else r for r in ep.evidence_records]
    ep=replace(ep,evidence_records=records,channels={c:{**v,'asset_id':asset} for c,v in ep.channels.items()},asset_scope=[asset])
    message={'evidence_id':'m_'+'1'*24,'asdu_type':45,'cause_of_transmission':6,'observation_time':-10}
    children,_=address_children(message,payload if payload is not None else packet(),0,mp)
    public,private,visibility=export_episode(ep,view,{'event_id':ep.episode_id,'records':children},mp['public_metadata'])
    return public,private,visibility


class AmendmentTests(unittest.TestCase):
    def test_audited_types_and_sequential_layout(self):
        for kind in (45,47,50):
            for sq in (False,True):
                self.assertEqual([r['ioa'] for r in parse_addresses(packet(kind,count=2,sequential=sq),0,kind,6)],[1,2])

    def test_values_and_qualifiers_do_not_change_public_address(self):
        for kind in (45,47,50):
            msg={'evidence_id':'m_'+'1'*24,'asdu_type':kind,'cause_of_transmission':6,'observation_time':0}
            self.assertEqual(address_children(msg,packet(kind,fill=0),0,mapping())[0],address_children(msg,packet(kind,fill=255),0,mapping())[0])

    def test_unaudited_types_rejected(self):
        for kind in (46,48,49,51):
            with self.assertRaises(ValueError):parse_addresses(packet(),0,kind,6)

    def test_bad_layouts_preserve_null_child(self):
        msg={'evidence_id':'m_'+'1'*24,'asdu_type':45,'cause_of_transmission':6,'observation_time':0}
        for data in (b'',packet()[:-1],packet(count=0),packet()+b''):
            if data==packet():continue
            children,_=address_children(msg,data,0,mapping());a=children[0]
            self.assertEqual(a['mapping_status'],'invalid_layout');self.assertIsNone(a['mapped_target_asset_id']);self.assertIsNone(a['object_index'])

    def test_missing_ambiguous_context_attribute_no_guess(self):
        row='{"element":"x","context":"CONFIGURATION","attribute":"closed"}'
        examples=[('{}','unmapped'),('{"1.1":'+row+',"1.1":'+row+'}','ambiguous'),
            ('{"1.1":'+row.replace('CONFIGURATION','MEASUREMENT')+'}','context_not_allowlisted'),
            ('{"1.1":'+row.replace('closed','voltage')+'}','attribute_not_allowlisted')]
        msg={'evidence_id':'m_'+'1'*24,'asdu_type':45,'cause_of_transmission':6,'observation_time':0}
        for raw,status in examples:
            a=address_children(msg,packet(),0,mapping(raw.encode()))[0][0]
            self.assertEqual(a['mapping_status'],status)
            self.assertTrue(all(a[k] is None for k in ('mapped_target_asset_id','mapped_control_point_id','mapping_evidence_id')))
            self.assertTrue(a['reason'])

    def test_mapping_secrets_absent(self):
        mp=mapping();data=json.dumps(mp['public_metadata'])
        for word in ('private.bus','initial_value','family','secret','999','1.1'):self.assertNotIn(word,data)
        public,_,_=fixture();a=next(r for r in public['records'] if r['source_type']=='command_address_observation')
        for key in ('ca','ioa','family','value','setpoint','initial_value','select_execute','raw_identifier'):self.assertNotIn(key,a)

    def test_E_view_never_exports_a_or_command_observation(self):
        p,_,vis=fixture('E');self.assertFalse(vis['address_parents'])
        self.assertTrue(all(r['source_type']=='process' for r in p['records']))
        self.assertNotIn('cause_of_transmission',json.dumps(p))

    def test_static_metadata_identical_across_views(self):
        exports=[fixture(v)[0] for v in ('E','N','EN')]
        self.assertEqual(exports[0]['control_metadata'],exports[1]['control_metadata']);self.assertEqual(exports[1]['control_metadata'],exports[2]['control_metadata'])

    def test_all_role_namespaces_are_selective(self):
        allowed={'citation','command_address','temporal_observation','asset_observation','eligible_record','retrieved_record'}
        for role in schema('evidence_id_roles.v2.json'):
            if role in allowed:require_id('a_'+'1'*24,role)
            else:
                with self.assertRaises(ValueError):require_id('a_'+'1'*24,role)

    def test_payload_namespaces_in_claim_and_verification(self):
        for name in ('investigation_claim.v2.json','investigation_verification.v2.json'):
            defs=schema(name)['$defs']
            for kind,keys in {'network':['record_id'],'ack':['record_id'],'command':['record_id'],'value':['record_id'],
                'delta':['before_id','after_id'],'state':['before_id','after_id'],'gap':['coverage_id','left_id','right_id'],'unknown':['scope_id']}.items():
                for key in keys:
                    with self.assertRaises(ValueError):check('a_'+'1'*24,defs[kind]['properties'][key])
            for key in ('earlier_id','later_id'):check('a_'+'1'*24,defs['temporal']['properties'][key])
            check('a_'+'1'*24,defs['command']['properties']['address_evidence_id'])
            check(['a_'+'1'*24],defs['claim']['properties']['evidence_ids'])
            for kind in ('indicator','interpretation'):
                with self.assertRaises(ValueError):check(['a_'+'1'*24],defs[kind]['properties']['basis_ids'])

    def test_address_parent_only_message(self):
        public,_,_=fixture();a=copy.deepcopy(public['records'][-1]);a['parent_ids']=['a_'+'1'*24]
        with self.assertRaises(ValueError):validate('command_address.v2.json',a)

    def test_retrieval_visibility_namespace_envelopes(self):
        public,_,vis=fixture();b,r=retrieve(public)
        validate('visibility_ids.v2.json',vis);validate('retrieval_ids.v2.json',r['namespace_envelope'])
        for key in ('scope_id','mapping_ids'):
            bad=copy.deepcopy(r['namespace_envelope']);bad[key]=['a_'+'1'*24] if key=='mapping_ids' else 'a_'+'1'*24
            with self.assertRaises(ValueError):validate('retrieval_ids.v2.json',bad)
        bad=copy.deepcopy(vis);bad['address_parents']={next(iter(vis['address_parents'])):'e_'+'1'*24}
        with self.assertRaises(ValueError):validate('visibility_ids.v2.json',bad)

    def test_export_wrong_parent_time_mapping_rejected(self):
        p,_,_=fixture()
        for key,value in [('parent_ids',['m_'+'9'*24]),('observation_time',12),('mapped_target_asset_id','asset_'+'9'*16)]:
            bad=copy.deepcopy(p);bad['records'][-1][key]=value
            with self.assertRaises(ValueError):validate_public(bad)

    def test_retrieval_budget_and_atomic_closure(self):
        for view in ('E','N','EN'):
            p,_,_=fixture(view)
            for cap in (48000,3500,1200):
                b,r=retrieve(p,max_bytes=cap);validate_bundle(b)
                self.assertLessEqual(r['serialized_bundle_bytes'],cap)
                for domain,n in r['retrieved_by_domain'].items():self.assertLessEqual(n,r['budget'][domain])
                self.assertIsNone(r['final_recovered_investigation_facts'])

    def test_retrieval_deterministic(self):
        p,_,_=fixture();self.assertEqual(retrieve(p),retrieve(p))

    def test_bundle_missing_parent_or_mapping_fails(self):
        p,_,_=fixture();b,_=retrieve(p)
        for mode in ('parent','mapping'):
            bad=copy.deepcopy(b)
            if mode=='parent':bad['entries']=[r for r in bad['entries'] if r['evidence_id']!='m_'+'1'*24]
            else:bad['control_metadata']={}
            with self.assertRaises(ValueError):validate_bundle(bad)

    def test_supported_cross_source_has_both_edges(self):
        p,_,_=fixture();b,r=retrieve(p);report=timeline(b,r)
        c=next(c for c in report['amendment_claims'] if c['claim_type']=='temporal_association')
        self.assertTrue(validate_supported_claim(c,b));self.assertEqual(len(c['payload']['mapping_ids']),2)
        self.assertIn('asset-linked temporal evidence',c['claim_text']);self.assertEqual(c['payload']['delta_seconds'],20)

    def test_wrong_asset_or_quality_or_time_rejects_link(self):
        p,_,_=fixture();b,r=retrieve(p);c=next(c for c in timeline(b,r)['amendment_claims'] if c['claim_type']=='temporal_association')
        for key,value in [('asset_id','asset_'+'9'*16),('quality_flags',['invalid']),('observation_time',-10)]:
            bad=copy.deepcopy(b);e=next(e for e in bad['entries'] if e['evidence_id']==c['payload']['later_id']);e[key]=value
            with self.assertRaises(ValueError):validate_supported_claim(c,bad)

    def test_causal_language_and_false_payload_rejected(self):
        p,_,_=fixture();b,r=retrieve(p);c=next(c for c in timeline(b,r)['amendment_claims'] if c['claim_type']=='temporal_association')
        for text in ('The command caused the change.','Asset executed the malicious command.','The attack succeeded.'):
            bad=copy.deepcopy(c);bad['claim_text']=text
            with self.assertRaises(ValueError):validate_supported_claim(bad,b)
        bad=copy.deepcopy(c);bad['payload']['delta_seconds']=999
        with self.assertRaises(ValueError):validate_supported_claim(bad,b)

    def test_uncited_or_missing_mapping_edge_rejected(self):
        p,_,_=fixture();b,r=retrieve(p);c=next(c for c in timeline(b,r)['amendment_claims'] if c['claim_type']=='temporal_association')
        for key in ('evidence_ids','mapping_ids'):
            bad=copy.deepcopy(c)
            (bad if key=='evidence_ids' else bad['payload'])[key].pop()
            with self.assertRaises(ValueError):validate_claim_shape(bad)

    def test_asset_relation_disallows_blind_namespace_broadening(self):
        p,_,_=fixture();b,r=retrieve(p);c=next(c for c in timeline(b,r)['amendment_claims'] if c['claim_type']=='asset_relationship')
        for relation in ('same_mapped_asset','packet_endpoint_pair'):
            bad=copy.deepcopy(c);bad['payload']['relation']=relation
            with self.assertRaises(ValueError):validate_claim_shape(bad)

    def test_no_E_view_returns_insufficient(self):
        p,_,_=fixture('N');b,r=retrieve(p);report=timeline(b,r)
        self.assertFalse(any(c['claim_type']=='temporal_association' for c in report['amendment_claims']))
        self.assertTrue(any(x['reason']=='view_excluded' for x in report['amendment_insufficiency']))

    def test_no_later_E_is_not_retrieval_absence_or_safe(self):
        p,_,_=fixture();p['records']=[r for r in p['records'] if r['source_type']!='process'];b,r=retrieve(p)
        report=timeline(b,r)
        self.assertTrue(any(x['reason']=='no_valid_later_same_asset_E_in_allowed_window' for x in report['amendment_insufficiency']))
        self.assertEqual(report['security_interpretation'],[])

    def test_unmapped_retains_weak_request(self):
        p,_,_=fixture(payload=packet(ioa=9));b,r=retrieve(p);report=timeline(b,r)
        c=next(c for c in report['amendment_claims'] if c['claim_type']=='command_observed')
        self.assertIsNone(c['payload']['mapped_target_asset_id']);self.assertEqual(c['claim_text'],'A command-type activation request was observed.')

    def test_state_change_optional_and_not_in_sufficiency(self):
        p,_,_=fixture();b,r=retrieve(p);report=timeline(b,r);audit=supportability(p)
        self.assertFalse(any(u['subject']=='reported_state_change' for u in report['unknowns']))
        self.assertFalse(next(x for x in audit['rows'] if x['claim_type']=='reported_state_change')['required_for_minimum_question_sufficiency'])

    def test_boolean_pair_guardrails(self):
        p,_,_=fixture();a,b=[copy.deepcopy(r) for r in p['records'] if r['source_type']=='process'];a['value']=False;b['value']=True
        self.assertEqual(difference(a,b)['fields']['kind'],'reported_state_change')
        b['value']=False
        with self.assertRaises(ValueError):difference(a,b)
        b['value']=True;b['observation_time']=a['observation_time']
        with self.assertRaises(ValueError):difference(a,b)

    def test_state_single_observation_not_change(self):
        p,_,_=fixture();p['records']=[r for r in p['records'] if r['evidence_id']!='e_'+'2'*24]
        e=next(r for r in p['records'] if r['source_type']=='process');e['value']=True
        b,r=retrieve(p);report=timeline(b,r)
        self.assertFalse(report['numerical_differences']);self.assertTrue(any(c['claim_type']=='reported_value' for c in report['observations']))


if __name__=='__main__':unittest.main()
