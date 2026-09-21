import unittest
from pathlib import Path
import sys
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
import numpy as np
from sherlock.parser import Packet
from sherlock.parser_v2 import APDUDeduplicator
from sherlock.capture_v2 import order_packets
from paired_bootstrap import sampled_indices,metric_vector,contrasts
from sklearn.metrics import f1_score,balanced_accuracy_score
from sherlock.io import ROOT,read_json

A=bytes.fromhex('680443000000');B=bytes.fromhex('680483000000')
def packet(index=1,t=100.,seq=1000,payload=A,flags=24):
    return Packet(index,t,66+len(payload),6,'a','b',2404,5000,flags,seq,payload)

class EvaluationTests(unittest.TestCase):
    def test_segment_regrouping(self):
        d=APDUDeduplicator()
        self.assertEqual(len(d.messages(packet(payload=A+B))),2)
        self.assertEqual(d.messages(packet(index=2,payload=A)),[])
        self.assertEqual(d.messages(packet(index=3,seq=1006,payload=B)),[])
        self.assertEqual(len(d.messages(packet(index=4,payload=B))),1)
        self.assertEqual(d.messages(packet(index=5,payload=B)),[])

    def test_connection_restart(self):
        d=APDUDeduplicator();d.messages(packet())
        d.messages(packet(index=2,payload=b'',flags=2))
        self.assertEqual(len(d.messages(packet(index=3))),1)

    def test_sequence_wrap_and_partial_failure(self):
        d=APDUDeduplicator()
        self.assertEqual(len(d.messages(packet(seq=2**32-3,payload=A+B))),2)
        self.assertEqual(d.messages(packet(index=2,seq=3,payload=B)),[])
        with self.assertRaises(ValueError):d.messages(packet(index=3,seq=9,payload=A[:-1]))

    def test_capture_jitter_order_and_ids(self):
        ps=[packet(1,100.000002),packet(2,100.000001),packet(3,100.002)]
        stats={};got=list(order_packets(ps,stats=stats))
        self.assertEqual([p.index for p in got],[2,1,3])
        self.assertEqual({p.timestamp for p in got},{p.timestamp for p in ps})
        self.assertEqual(stats['out_of_order_packets'],1)
        with self.assertRaises(ValueError):list(order_packets([packet(1,100),packet(2,99.9)]))

    def test_bootstrap_preserves_strata_and_pairing(self):
        y=np.array([0,0,1,1,0,1]);g=np.array(['a','a','a','a','b','b'])
        ix=sampled_indices(y,g,100,42)
        np.testing.assert_array_equal(ix,sampled_indices(y,g,100,42))
        for row in ix:
            for scene in ['a','b']:
                for label in [0,1]:
                    self.assertEqual(int(((g[row]==scene)&(y[row]==label)).sum()),int(((g==scene)&(y==label)).sum()))
        cfg=read_json(ROOT/'configs/evaluation.v1.json')['bootstrap']
        result=contrasts(y,{'E':y*.8+.1,'N':y*.8+.1,'EN':y*.8+.1},g,cfg)
        for contrast in result.values():
            for metric in contrast.values():self.assertEqual(metric['ci95'],[0.,0.]);self.assertEqual(metric['point'],0.)

    def test_bootstrap_metric_matches_sklearn(self):
        y=np.array([0,0,0,1,1]);p=np.array([0,1,0,0,1]);m=metric_vector(y,p)
        self.assertAlmostEqual(float(m['macro_f1']),f1_score(y,p,average='macro'))
        self.assertAlmostEqual(float(m['balanced_accuracy']),balanced_accuracy_score(y,p))
        cfg=read_json(ROOT/'configs/evaluation.v1.json')['bootstrap']
        self.assertIsNone(contrasts([0,0],{'E':[0,0],'N':[0,0],'EN':[0,0]},['a','a'],cfg))

if __name__=='__main__':unittest.main()
