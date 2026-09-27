"""Pre-run synthetic/sealed-development conformance, never a recovery score."""
import copy
import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_investigation_dryrun_regression import (ROOT,EID,bundle_fixture,claim_fixture,output_fixture,provider_output,FakeTransport)
from investigation_dryrun import claims as C
from investigation_dryrun.common import load,dumps,digest,file_hash,create_json
from investigation_dryrun.schema import check,schema,validate_claim_shape
from investigation_dryrun.structured import compile_schema
from investigation_dryrun import runner
from investigation_dryrun.custody import development_ids,verify_access_log

REL='observation_channel_maps_to_asset'
def mapping_claim(bundle,rid=None):
    e=next(e for e in bundle['entries'] if e['evidence_id']==rid) if rid else next(e for e in bundle['entries'] if e['source_type']=='process')
    ch=e['fields']['channel_id'];m=bundle['metadata'][ch]
    c={'claim_id':'c_1','question_ids':['Q3'],'claim_type':'asset_relationship','claim_text':'pending','support_assertion':'asserted','evidence_ids':[e['evidence_id'],m['evidence_id']],'asset_ids':[e['asset_id']],'channel_ids':[ch],'endpoint_ids':[],'payload':{'relation':REL,'record_ids':[e['evidence_id']],'mapping_ids':[m['evidence_id']],'mapped_asset_id':e['asset_id']}}
    c['claim_text']=C.typed_support(c,bundle)['canonical_text'];return c

class MappingAmendment(unittest.TestCase):
    def test_positive_exact_mapping(self):
        b,_=bundle_fixture();c=mapping_claim(b);validate_claim_shape(c)
        self.assertEqual(C.verify_claim(c,b)['disposition'],'SUPPORTED')
        self.assertEqual(C.typed_support(c,b)['key_kind'],REL)
    def test_all_four_sealed_gold_keys_and_bytes_unchanged(self):
        from retrieval.investigation_retriever_v2 import bundle_for
        mp=ROOT/'annotations/gold/pilot-v1/manifest.json';mh=file_hash(mp);n=0
        for event in load(mp)['events']:
            ap=ROOT/event['annotation']['snapshot_path'];ah=file_hash(ap)
            public=json.loads(gzip.decompress((ROOT/event['source_evidence_hashes']['EN/eligible.json.gz']['snapshot_path']).read_bytes()))
            index={r['evidence_id']:r for r in public['records']}
            for g in load(ap)['facts']:
                if g.get('key_kind')!=REL:continue
                rid=g['key_identity']['record_id'];b=bundle_for(public,[index[rid]])
                c=mapping_claim(b,rid);self.assertTrue(C.matches_gold(c,b,g));self.assertEqual(C.verify_claim(c,b)['disposition'],'SUPPORTED');n+=1
            self.assertEqual(file_hash(ap),ah);self.assertEqual(file_hash(ROOT/event['annotation']['original_path']),ah)
        self.assertEqual(n,4);self.assertEqual(file_hash(mp),mh)
    def test_wrong_record_channel_asset_metadata_lineage_visibility(self):
        for field in ['record','channel','asset','mapped_asset','metadata','metadata_fields','lineage','visibility','quality','missing_metadata','two_records','hidden_citation']:
            with self.subTest(field=field):
                b,_=bundle_fixture();c=mapping_claim(b);p=c['payload'];e=next(e for e in b['entries'] if e['evidence_id']==p['record_ids'][0])
                if field=='record':p['record_ids']=['e_'+'f'*24]
                elif field=='channel':c['channel_ids']=['ch_'+'f'*16]
                elif field=='asset':c['asset_ids']=['asset_'+'f'*16]
                elif field=='mapped_asset':p['mapped_asset_id']='asset_'+'f'*16
                elif field=='metadata':p['mapping_ids']=['meta_'+'f'*24]
                elif field=='metadata_fields':b['metadata'][e['fields']['channel_id']]['context']='WRONG'
                elif field=='lineage':e['lineage_ref']='lin_'+'f'*24
                elif field=='visibility':b['scope']['view']='N';b['scope']['available_domains']=['N']
                elif field=='quality':e['quality_flags']=['invalid']
                elif field=='missing_metadata':b['metadata']={}
                elif field=='two_records':p['record_ids'].append(next(x['evidence_id'] for x in b['entries'] if x['source_type']=='process' and x!=e))
                else:c['evidence_ids'].append('e_'+'f'*24)
                with self.assertRaises((ValueError,KeyError)):C.typed_support(c,b)
    def test_mapping_cannot_assert_stronger_semantics(self):
        for text in ['physical state truth','physical change','command execution','command effect','causation','malicious intent','successful compromise','attribution']:
            b,_=bundle_fixture();c=mapping_claim(b);c['claim_text']+=' This proves '+text+'.'
            self.assertEqual(C.verify_claim(c,b)['disposition'],'INSUFFICIENT')
    def test_optional_vs_required_citation_without_semantic_change(self):
        b,_=bundle_fixture();c=mapping_claim(b);c['evidence_ids']=[]
        C.validate_raw_support(c,b)
        with self.assertRaises(ValueError):C.validate_raw_support(c,b,require_citations=True)
    def test_unrelated_definitions_byte_equivalent(self):
        for name in ['claim','verification']:
            old=load(ROOT/f'schemas/investigation_{name}.v2.json');new=load(ROOT/f'schemas/investigation_{name}.v3.json')
            for k in old['$defs']:
                if k!='asset':self.assertEqual(old['$defs'][k],new['$defs'][k])
            amended=copy.deepcopy(new['$defs']['asset']);amended['properties']['relation']['enum'].remove(REL);amended['allOf'].pop()
            self.assertEqual(amended,old['$defs']['asset'])

class StrictAndCeiling(unittest.TestCase):
    def test_wire_subset_closed_required_no_unsupported_keywords(self):
        def visit(n):
            if isinstance(n,dict):
                self.assertFalse(set(n)&{'allOf','if','then','else','oneOf','uniqueItems','exclusiveMaximum','exclusiveMinimum'})
                if n.get('type')=='object':
                    self.assertIs(n['additionalProperties'],False);self.assertEqual(set(n['required']),set(n['properties']))
                for v in n.values():visit(v)
            elif isinstance(n,list):
                for v in n:visit(v)
        for mode in ['required','optional_baseline']:
            s=compile_schema(mode);visit(s);self.assertEqual(s,load(ROOT/f'schemas/investigation_response.v3.{mode}.json'))
    def test_actual_request_strict_and_candidate_limits(self):
        model,budget,_=runner.approved_configuration(FakeTransport());b,_=bundle_fixture()
        body,_=runner.build_request(EID,'B3',b,model,budget)
        self.assertEqual(body['text']['format']['type'],'json_schema');self.assertIs(body['text']['format']['strict'],True)
        self.assertEqual(body['max_output_tokens'],4096);self.assertEqual(budget['evidence_token_safety_ceiling'],16384)
        self.assertNotIn('seed',body);self.assertEqual(body['truncation'],'disabled')
    def test_exact_ceiling_boundary_no_mutation(self):
        model,budget,_=runner.approved_configuration(FakeTransport());b,_=bundle_fixture();before=digest(b);encoded=dumps(b)
        for value,accepted in [(11163,True),(16384,True),(16385,False)]:
            with patch.object(runner,'count',side_effect=lambda t:value if t==encoded else 1):
                if accepted:runner.build_request(EID,'B3',b,model,budget)
                else:
                    with self.assertRaisesRegex(ValueError,'evidence_token_budget'):runner.build_request(EID,'B3',b,model,budget)
            self.assertEqual(digest(b),before)
    def test_local_full_validator_retains_uniqueness(self):
        b,_=bundle_fixture();c=mapping_claim(b);out=output_fixture(claims=[c]);c['evidence_ids']*=2
        # API subset cannot enforce uniqueItems; application fails closed.
        check(out,compile_schema('required'))
        self.assertTrue(runner.delivery_validation(out,EID,'EN','required'))
    def test_wire_accepts_mapping_and_numeric_specialization(self):
        b,_,c=claim_fixture();m=mapping_claim(b);m['claim_id']='c_2';out=output_fixture(claims=[c,m])
        check(out,compile_schema('required'));check(out,schema('investigation_claim.v3.json'))
        c['claim_type']='electrical_change';check(out,compile_schema('required'))
    def test_unknown_cannot_be_asserted_in_wire_schema(self):
        s=compile_schema('required')
        branches=[c for c in s['$defs']['claim']['anyOf'] if c['properties']['claim_type']['const']=='unknown']
        self.assertEqual(len(branches),1)
        self.assertEqual(branches[0]['properties']['support_assertion']['const'],'insufficient')
    def test_truncation_4096_retained_no_retry_B4_no_generation(self):
        obj=provider_output({},'incomplete');obj['incomplete_details']={'reason':'max_output_tokens'};obj['usage']={'input_tokens':100,'output_tokens':4096,'total_tokens':4196};obj['output'][0]['content'][0]['text']='{"claims":['
        fake=FakeTransport([(200,{},json.dumps(obj).encode())])
        with tempfile.TemporaryDirectory(dir=ROOT/'results/investigation-dryrun-v1') as tmp:
            path=Path(tmp);m=runner.generate(EID,'B3',1,'fixture',fake,path,sleep=lambda _:None)
            self.assertEqual(m['status'],'PROVIDER_INCOMPLETE');self.assertEqual(len(fake.requests),1)
            self.assertGreater(m['actual_evidence_tokens'],0)
            with patch.object(runner,'RUNS',path):replay=runner.replay(EID,1,'fixture')
            self.assertEqual(replay['status'],'REPLAY_UNAVAILABLE');self.assertEqual(replay['B3_input_sha256'],m['output_sha256']);self.assertEqual(replay['llm_calls'],0)
    def test_denied_generation_is_logged_before_transport(self):
        fake=FakeTransport();eid=load(ROOT/'configs/investigation_events.v1.json')['evaluation'][0]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(PermissionError):runner.generate(eid,'B1',1,'fixture',fake,Path(tmp))
            self.assertFalse(fake.requests);self.assertIsNotNone(verify_access_log(Path(tmp)/'denied_access.jsonl'))
    def test_frozen_scenario_mapping_not_from_performance(self):
        s=load(ROOT/'configs/investigation-dryrun-v1/scenario_strata.custodian.json');ref=s['source'];self.assertEqual(file_hash(ROOT/ref['path']),ref['sha256']);self.assertEqual(len(s['mapping']),48)
        self.assertTrue(set(development_ids())<=set(s['mapping']))
