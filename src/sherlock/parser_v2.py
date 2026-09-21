"""APDU byte-range deduplication, independent of TCP segment grouping.

Different bytes at the same stream offset remain distinct capture observations.
Complete APDUs are required; this is not a receiver-state reconstruction.
"""
import hashlib
from sherlock.parser import decode_apdus


class APDUDeduplicator:
    def __init__(self):
        self.flows={}
        self.duplicates=0

    def messages(self,p):
        self.duplicates=0
        if p.ip_protocol!=6 or 2404 not in (p.sport,p.dport):return []
        key=(p.src,p.sport,p.dst,p.dport)
        if p.flags&2:self.flows.pop(key,None)
        if not p.payload:return []
        data=self.flows.setdefault(key,{'reference':p.sequence,'seen':set()})
        ref=data['reference'];seq=ref+((p.sequence-ref+2**31)%2**32-2**31)
        data['reference']=max(ref,seq+len(p.payload))
        fresh=[]
        for m in decode_apdus(p.payload):
            offset=m['offset'];size=p.payload[offset+1]+2
            identity=(seq+offset,hashlib.sha256(p.payload[offset:offset+size]).digest())
            if identity in data['seen']:self.duplicates+=1
            else:fresh.append(m);data['seen'].add(identity)
        return fresh
