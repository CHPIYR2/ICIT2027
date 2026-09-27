"""Compile the authoritative v3 contract into the Responses strict schema subset.

Conditionals become tagged anyOf branches. Array uniqueness and exclusive numeric
bounds remain mandatory in the local authoritative validator, never ignored.
"""
import copy
from .common import ROOT, load

LOCAL_ONLY = {'uniqueItems', 'exclusiveMinimum', 'exclusiveMaximum'}

def merge(a,b):
    if '$ref' in b:return copy.deepcopy(b)
    out=copy.deepcopy(a)
    for k,v in b.items():
        out[k]=merge(out[k],v) if k in out and isinstance(out[k],dict) and isinstance(v,dict) else copy.deepcopy(v)
    return out

def expand_tagged(node,tag):
    variants=[]
    for value in node['properties'][tag]['enum']:
        n=copy.deepcopy(node);conditions=n.pop('allOf',[])
        n['properties'][tag]={'type':'string','const':value}
        for cond in conditions:
            if cond['if']['properties'][tag]['const']==value:n=merge(n,cond['then'])
        variants.append(n)
    return {'anyOf':variants}

def clean(node):
    if isinstance(node,list):return [clean(x) for x in node]
    if not isinstance(node,dict):return node
    result={k:clean(v) for k,v in node.items() if k not in LOCAL_ONLY|{'$schema','title'}}
    if 'const' in result and 'type' not in result:
        result['type']='string' if isinstance(result['const'],str) else 'integer'
    if 'enum' in result and 'type' not in result:
        result['type']='string' if all(isinstance(x,str) for x in result['enum']) else 'integer'
    return result

def compile_schema(citation_mode):
    if citation_mode not in ('required','optional_baseline'):raise ValueError('Bad citation mode')
    source=load(ROOT/'schemas/investigation_claim.v3.json');out=copy.deepcopy(source)
    out.pop('allOf')
    out['$defs']['asset']=expand_tagged(out['$defs']['asset'],'relation')
    claims=expand_tagged(out['$defs']['claim'],'claim_type')['anyOf'];branches=[]
    for c in claims:
        assertion=c['properties']['support_assertion']
        statuses=[assertion['const']] if 'const' in assertion else assertion['enum']
        for status in statuses:
            v=copy.deepcopy(c);v['properties']['support_assertion']={'type':'string','const':status}
            if citation_mode=='required' and status=='asserted':v['properties']['evidence_ids']['minItems']=1
            branches.append(v)
    out['$defs']['claim']={'anyOf':branches}
    out['properties']['citation_mode']={'type':'string','const':citation_mode}
    return clean(out)

def strict_format(baseline):
    mode='required' if baseline=='B3' else 'optional_baseline'
    return {'type':'json_schema','name':'investigation_v3','strict':True,'schema':compile_schema(mode)}
