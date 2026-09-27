"""Approved investigation-only address metadata. Never decodes control values."""
import hashlib
import json
from collections import defaultdict
from sherlock.io import opaque
from investigation.schema_v2 import validate,require_id

ATTRIBUTES={'closed','connected','tap_position','target_active_power','target_active_power_percentage'}
OBJECT_BYTES={45:1,47:1,50:5}


def static_mapping(raw_bytes,source_id):
    # Preserve duplicate address keys. Only project the three approved row fields.
    pairs=json.loads(raw_bytes,object_pairs_hook=lambda pairs:pairs)
    projected=defaultdict(list)
    for address,row_pairs in pairs:
        selected=[(key,value) for key,value in row_pairs if key in ('element','context','attribute')]
        if len(selected)!=3 or len({key for key,_ in selected})!=3:
            projected[address].append(None)
        else:projected[address].append(dict(selected))
    by_address={};public={}
    for address,rows in projected.items():
        status='exact_static_match';reason='exact_allowlisted_static_mapping';meta=None
        if len(rows)!=1 or rows[0] is None:
            status,reason='ambiguous','duplicate_address'
        elif rows[0]['context']!='CONFIGURATION':status=reason='context_not_allowlisted'
        elif rows[0]['attribute'] not in ATTRIBUTES or not isinstance(rows[0]['element'],str):status=reason='attribute_not_allowlisted'
        else:
            row=rows[0]
            cp=opaque('cp_',source_id+'|'+address+'|CONFIGURATION')
            mid=opaque('meta_','command-control|'+source_id+'|'+address+'|'+row['element']+'|'+row['attribute'],24)
            meta={'evidence_id':mid,'control_point_id':cp,'asset_id':opaque('asset_',source_id+'|'+row['element']),
                  'context':'CONFIGURATION','attribute':row['attribute']}
            public[mid]=meta
        by_address[address]={'status':status,'reason':reason,'metadata':meta}
    return {'private_address_lookup':by_address,'public_metadata':public,
            'mapping_sha256':hashlib.sha256(raw_bytes).hexdigest(),'source_id':source_id}


def parse_addresses(payload,offset,expected_type,expected_cot):
    if expected_type not in OBJECT_BYTES:raise ValueError('Type not approved')
    if type(offset) is not int or offset<0 or offset+2>len(payload) or payload[offset]!=0x68:raise ValueError('Invalid APDU start')
    end=offset+payload[offset+1]+2
    if end>len(payload):raise ValueError('Truncated APDU')
    pdu=payload[offset:end]
    if len(pdu)<12 or pdu[2]&1 or pdu[6]!=expected_type or pdu[8]&63!=expected_cot:raise ValueError('Header mismatch')
    count=pdu[7]&127;sequential=bool(pdu[7]&128);ca=int.from_bytes(pdu[10:12],'little')
    if count==0:raise ValueError('Empty address list')
    pos=12;ioa=None;result=[]
    for index in range(count):
        if index==0 or not sequential:
            if pos+3>len(pdu):raise ValueError('Missing address bytes')
            ioa=int.from_bytes(pdu[pos:pos+3],'little');pos+=3
        else:ioa+=1
        if ioa>0xffffff or pos+OBJECT_BYTES[expected_type]>len(pdu):raise ValueError('Invalid object bounds')
        result.append({'ca':ca,'ioa':ioa,'object_index':index,'address_encoding':'sequential_increment' if sequential and index else 'explicit_address'})
        pos+=OBJECT_BYTES[expected_type]  # Skip setpoint/qualifier, never decode it.
    if pos!=len(pdu):raise ValueError('Unexplained bytes')
    return result


def address_children(message,payload,offset,mapping):
    require_id(message['evidence_id'],'command_message')
    if message['asdu_type'] not in OBJECT_BYTES:raise ValueError('Unaudited command type')
    invalid=False
    try:addresses=parse_addresses(payload,offset,message['asdu_type'],message['cause_of_transmission'])
    except ValueError:addresses=[{'object_index':None}];invalid=True
    children=[];provenance={}
    for item in addresses:
        if invalid:
            match={'status':'invalid_layout','reason':'invalid_address_layout','metadata':None}
        else:
            match=mapping['private_address_lookup'].get(f"{item['ca']}.{item['ioa']}",
                {'status':'unmapped','reason':'address_missing','metadata':None})
        meta=match['metadata'];aid=opaque('a_',message['evidence_id']+'|address|'+str(item['object_index']),24)
        child={'evidence_id':aid,'source_type':'command_address_observation','view':'N','parent_ids':[message['evidence_id']],
            'asdu_type':message['asdu_type'],'cause_of_transmission':message['cause_of_transmission'],
            'object_index':item['object_index'],'observation_time':message['observation_time'],
            'mapped_control_point_id':meta['control_point_id'] if meta else None,
            'mapped_target_asset_id':meta['asset_id'] if meta else None,'mapping_evidence_id':meta['evidence_id'] if meta else None,
            'mapping_status':match['status'],'reason':match['reason']}
        validate('command_address.v2.json',child)
        children.append(child)
        provenance[aid]={'parent_ids':[message['evidence_id']],**item,'apdu_offset':offset,
            'mapping_sha256':mapping['mapping_sha256'],'source_id':mapping['source_id'],'access':'PRIVATE_ADDRESS_PROVENANCE'}
    return children,provenance
