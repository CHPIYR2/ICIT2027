"""Dependency-free validator for the finite schema vocabulary shipped in schemas/.

This validates structure and identifier roles, not natural-language truth. Unknown
schema keywords are rejected so an unsupported rule cannot silently be ignored.
"""
import json
import math
import re
from pathlib import Path
from functools import lru_cache

SCHEMAS=Path(__file__).resolve().parents[2]/'schemas'
KEYWORDS={'$schema','$defs','$ref','title','description','type','const','enum','properties','required',
    'additionalProperties','items','minItems','maxItems','uniqueItems','minLength','maxLength','pattern',
    'minimum','maximum','exclusiveMaximum','exclusiveMinimum','anyOf','oneOf','allOf','if','then','else','propertyNames'}


@lru_cache(None)
def schema(name):
    return json.loads((SCHEMAS/name).read_text())


def check(value, rule, root=None):
    root=rule if root is None else root
    if rule is True:return
    if rule is False:raise ValueError('Forbidden schema value')
    if set(rule)-KEYWORDS:raise ValueError('Unsupported schema keyword')
    if '$ref' in rule:
        target=root
        if not rule['$ref'].startswith('#/'):raise ValueError('External schema references forbidden')
        for part in rule['$ref'][2:].split('/'):target=target[part]
        check(value,target,root)
    def matches(branch):
        try:check(value,branch,root);return True
        except (ValueError,TypeError):return False
    if 'anyOf' in rule and not any(matches(r) for r in rule['anyOf']):raise ValueError('No schema alternative')
    if 'oneOf' in rule and sum(matches(r) for r in rule['oneOf'])!=1:raise ValueError('Ambiguous schema alternatives')
    for branch in rule.get('allOf',[]):check(value,branch,root)
    if 'if' in rule:
        branch=rule.get('then' if matches(rule['if']) else 'else',{})
        check(value,branch,root)
    kind={'null':lambda x:x is None,'boolean':lambda x:type(x) is bool,'integer':lambda x:type(x) is int,
        'number':lambda x:type(x) in (int,float) and math.isfinite(x),'string':lambda x:type(x) is str,
        'array':lambda x:type(x) is list,'object':lambda x:type(x) is dict}
    if 'type' in rule:
        types=rule['type'] if isinstance(rule['type'],list) else [rule['type']]
        if not any(kind[t](value) for t in types):raise ValueError('Wrong JSON type')
    def equal(a,b):return a==b and not ((type(a) is bool)!=(type(b) is bool))
    if 'const' in rule and not equal(value,rule['const']):raise ValueError('Wrong constant')
    if 'enum' in rule and not any(equal(value,x) for x in rule['enum']):raise ValueError('Wrong enumeration')
    if type(value) is dict:
        if not set(rule.get('required',[]))<=set(value):raise ValueError('Missing required fields')
        properties=rule.get('properties',{})
        for key,item in value.items():
            if 'propertyNames' in rule:check(key,rule['propertyNames'],root)
            if key in properties:check(item,properties[key],root)
            elif 'additionalProperties' in rule:check(item,rule['additionalProperties'],root)
    if type(value) is list:
        if len(value)<rule.get('minItems',0) or len(value)>rule.get('maxItems',math.inf):raise ValueError('Wrong array length')
        if rule.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in value})!=len(value):raise ValueError('Duplicate array items')
        for item in value:
            if 'items' in rule:check(item,rule['items'],root)
    if type(value) is str:
        if len(value)<rule.get('minLength',0) or len(value)>rule.get('maxLength',math.inf):raise ValueError('Wrong string length')
        if 'pattern' in rule and not re.search(rule['pattern'],value):raise ValueError('Illegal identifier/format')
    if type(value) in (int,float):
        if not math.isfinite(value):raise ValueError('Nonfinite JSON number')
        for key,predicate in [('minimum',lambda x:x>=rule[key]),('maximum',lambda x:x<=rule[key]),
                              ('exclusiveMaximum',lambda x:x<rule[key]),('exclusiveMinimum',lambda x:x>rule[key])]:
            if key in rule and not predicate(value):raise ValueError('Number out of bounds')


def validate(name,value):
    check(value,schema(name))
    return value


def require_id(value,role):
    if type(value) is not str or re.fullmatch(schema('evidence_id_roles.v2.json')[role],value) is None:
        raise ValueError('Illegal evidence ID for '+role)


def validate_claim_shape(claim):
    root=schema('investigation_claim.v2.json')
    check(claim,root['$defs']['claim'],root)
    payload=claim['payload'];cited=set(claim['evidence_ids'])
    for key in ('record_id','address_evidence_id','mapping_evidence_id','coverage_id','left_id','right_id',
                'before_id','after_id','earlier_id','later_id','scope_id'):
        if payload.get(key) is not None and payload[key] not in cited:raise ValueError('Uncited payload reference')
    for key in ('record_ids','mapping_ids','basis_ids'):
        if not set(payload.get(key,[]))<=cited:raise ValueError('Uncited payload references')
    if claim['claim_type']=='asset_relationship':
        role={'same_mapped_asset':'process_observation','packet_endpoint_pair':'packet','command_address_maps_to_asset':'asset_observation'}[payload['relation']]
        for rid in payload['record_ids']:require_id(rid,role)
        if payload['relation']=='command_address_maps_to_asset' and not ({'m','a'}<={x.split('_')[0] for x in payload['record_ids']}):
            raise ValueError('Address mapping needs message and address evidence')
        if payload['relation']=='command_address_maps_to_asset' and (len(payload['mapping_ids'])!=1 or payload['mapped_asset_id'] is None):
            raise ValueError('Exact static mapping edge required')
    if claim['claim_type']=='command_observed':
        fields=[payload[k] for k in ('address_evidence_id','mapping_evidence_id','mapped_control_point_id','mapped_target_asset_id')]
        if any(x is not None for x in fields) and not all(x is not None for x in fields):raise ValueError('Partial mapped command payload')
    if claim['claim_type']=='temporal_association' and payload['scope']=='same_observed_asset':
        if {payload['earlier_id'].split('_')[0],payload['later_id'].split('_')[0]}!={'a','e'}:
            raise ValueError('Cross-source same-asset relation needs a and e')
        if len(payload['mapping_ids'])!=2 or payload['mapped_asset_id'] is None:raise ValueError('Both mapping edges required')
    if claim['claim_type']=='temporal_association' and payload['scope']=='episode_only':
        if payload['mapping_ids'] or payload['mapped_asset_id'] is not None:raise ValueError('Episode-only order has no asserted asset edge')
    if claim['claim_type']=='reported_state_change':
        if payload['before_time']>=payload['after_time'] or payload['before_value']==payload['after_value'] or payload['before_id']==payload['after_id']:
            raise ValueError('State change requires distinct ordered unequal observations')
    return claim
