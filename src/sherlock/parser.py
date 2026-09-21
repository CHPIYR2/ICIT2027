"""Strict decoder for the complete-in-segment IEC-104 layout audited in Sherlock.

Not a TCP receiver reconstruction. Each complete captured APDU is an observation;
no claim is made about which bytes the receiver accepted. Partial APDUs and IP
fragments fail closed. Exact segment retransmissions are not fresh observations.
"""
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import math
import struct


@dataclass(frozen=True)
class Packet:
    index: int
    timestamp: float
    length: int
    ip_protocol: int | None
    src: str | None
    dst: str | None
    sport: int | None
    dport: int | None
    flags: int
    sequence: int | None
    payload: bytes


def read_pcap(stream):
    head = stream.read(24)
    formats={b"\xd4\xc3\xb2\xa1":("<",1e6),b"\xa1\xb2\xc3\xd4":(">",1e6),
             b"\x4d\x3c\xb2\xa1":("<",1e9),b"\xa1\xb2\x3c\x4d":(">",1e9)}
    if len(head)!=24 or head[:4] not in formats:
        raise ValueError("Unsupported PCAP")
    endian, scale=formats[head[:4]]
    _,_,_,_,snaplen,linktype=struct.unpack(endian+"HHiIII",head[4:])
    if linktype!=1:raise ValueError("Expected Ethernet capture")
    index=0;previous=-math.inf
    while header:=stream.read(16):
        if len(header)!=16:raise ValueError("Truncated packet header")
        secs,sub,caplen,orig=struct.unpack(endian+"IIII",header)
        if caplen>snaplen or caplen!=orig:raise ValueError("Truncated or invalid capture length")
        frame=stream.read(caplen)
        if len(frame)!=caplen or len(frame)<14:raise ValueError("Truncated frame")
        index+=1;t=secs+sub/scale
        if t<previous:raise ValueError("Capture timestamp regression")
        previous=t
        proto=src=dst=sport=dport=seq=None;flags=0;payload=b""
        ethertype=int.from_bytes(frame[12:14],"big");offset=14
        while ethertype in (0x8100,0x88a8):
            if len(frame)<offset+4:raise ValueError("Truncated VLAN")
            ethertype=int.from_bytes(frame[offset+2:offset+4],"big");offset+=4
        if ethertype==0x800:
            ip=frame[offset:]
            if len(ip)<20 or ip[0]>>4!=4:raise ValueError("Invalid IPv4")
            ihl=(ip[0]&15)*4;total=int.from_bytes(ip[2:4],"big")
            if ihl<20 or total<ihl or total>len(ip):raise ValueError("Invalid IP length")
            if int.from_bytes(ip[6:8],"big")&0x3fff:raise ValueError("IP fragments require an unimplemented reassembler")
            ip=ip[:total];proto=ip[9]
            src='.'.join(map(str,ip[12:16]));dst='.'.join(map(str,ip[16:20]))
            if proto==6:
                tcp=ip[ihl:]
                if len(tcp)<20:raise ValueError("Truncated TCP")
                hlen=(tcp[12]>>4)*4
                if hlen<20 or hlen>len(tcp):raise ValueError("Invalid TCP length")
                sport,dport,seq=struct.unpack('!HHI',tcp[:8]);flags=tcp[13];payload=tcp[hlen:]
        yield Packet(index,t,orig,proto,src,dst,sport,dport,flags,seq,payload)


class Deduplicator:
    def __init__(self):
        self.flows={}
        self.conflicting_packet_indices=()

    def retransmission(self,p):
        self.conflicting_packet_indices=()
        if p.ip_protocol!=6:return False
        flow=(p.src,p.sport,p.dst,p.dport)
        if p.flags&2:self.flows.pop(flow,None)
        if not p.payload:return False
        data=self.flows.setdefault(flow,{'starts':[],'segments':{},'reference':p.sequence})
        ref=data['reference'];seq=ref+((p.sequence-ref+2**31)%2**32-2**31)
        end=seq+len(p.payload);digest=hashlib.sha256(p.payload).digest()
        segments=data['segments'];starts=data['starts']
        if seq in segments:
            old_end, variants = segments[seq]
            repeated = (end,digest) in variants
            if not repeated: variants[(end,digest)] = p.index
            if len(variants)>1:
                self.conflicting_packet_indices=tuple(variants.values())+(p.index,)
            segments[seq]=(max(old_end,end),variants)
            return repeated
        position=bisect_left(starts,seq)
        starts.insert(position,seq);segments[seq]=(end,{(end,digest):p.index});data['reference']=max(ref,end)
        return False


SIZES={1:1,5:2,13:5,45:1,47:1,50:5,100:1,103:7}


def decode_apdus(payload):
    offset=0;messages=[]
    while offset<len(payload):
        if len(payload)-offset<2 or payload[offset]!=0x68:raise ValueError("Non-aligned/fragmented IEC APDU")
        size=payload[offset+1]+2
        if size<6 or offset+size>len(payload):raise ValueError("Incomplete IEC APDU")
        pdu=payload[offset:offset+size];start=offset;offset+=size
        if pdu[2]&1:
            if len(pdu)!=6:raise ValueError("Invalid S/U frame length")
            messages.append({'offset':start,'format':'S' if pdu[2]&3==1 else 'U','type':None,'cot':None,'objects':[]})
            continue
        if len(pdu)<12:raise ValueError("Short ASDU")
        type_id,vsq=pdu[6:8];cot=pdu[8]&0x3f;ca=int.from_bytes(pdu[10:12],'little')
        if type_id not in SIZES:raise ValueError(f"Unaudited ASDU type {type_id}")
        pos=12;ioa=None;objects=[]
        for i in range(vsq&0x7f):
            object_offset=pos
            if i==0 or not vsq&0x80:
                if pos+3>len(pdu):raise ValueError("Missing information object address")
                ioa=int.from_bytes(pdu[pos:pos+3],'little');pos+=3
            else:ioa+=1
            if pos+SIZES[type_id]>len(pdu):raise ValueError("Truncated information object")
            value=None;quality=[]
            if type_id in (1,13):
                if type_id==13:value=struct.unpack('<f',pdu[pos:pos+4])[0];q=pdu[pos+4]
                else:value=bool(pdu[pos]&1);q=pdu[pos]
                for bit,name in [(128,'invalid'),(64,'not_topical'),(32,'substituted'),(16,'blocked')]:
                    if q&bit:quality.append(name)
                if type_id==13 and q&1:quality.append('overflow')
                if not math.isfinite(value):value=None;quality.append('nonfinite')
                objects.append({'ca_ioa':f'{ca}.{ioa}','value':value,'quality':quality,'offset':object_offset})
            pos+=SIZES[type_id]
        if pos!=len(pdu):raise ValueError("ASDU contains unexplained bytes")
        messages.append({'offset':start,'format':'I','type':type_id,'cot':cot,'objects':objects})
    return messages
