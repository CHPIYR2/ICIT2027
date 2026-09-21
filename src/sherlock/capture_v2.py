"""Preserve PCAP time/index; stably reorder capture jitter up to 1 ms.

The bounded reorder operates offline; it never changes a timestamp or includes an
observation at/after an episode cutoff. Larger regressions fail closed.
"""
import heapq
import math
import struct
from sherlock.parser import Packet

def raw_packets(stream):
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


def order_packets(packets, max_lateness=.001, stats=None):
    stats={} if stats is None else stats
    heap=[];maximum=-math.inf
    for p in packets:
        if p.timestamp<maximum:
            lag=maximum-p.timestamp
            stats['out_of_order_packets']=stats.get('out_of_order_packets',0)+1
            stats['maximum_lag_seconds']=max(stats.get('maximum_lag_seconds',0),lag)
            if lag>max_lateness:raise ValueError('Capture regression exceeds fixed 1 ms reorder limit')
        maximum=max(maximum,p.timestamp)
        heapq.heappush(heap,(p.timestamp,p.index,p))
        while heap and heap[0][0]<=maximum-max_lateness:
            yield heapq.heappop(heap)[2]
    while heap:yield heapq.heappop(heap)[2]


def read_pcap(stream,stats=None):
    yield from order_packets(raw_packets(stream),stats=stats)
