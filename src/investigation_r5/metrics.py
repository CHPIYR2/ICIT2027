"""Exact metric arithmetic over completed, hash-bound human review ledgers.

No verifier verdict is used as a human support/semantic oracle. This module never
loads gold, model outputs, or arbitrary paths itself. Pending reviews block scoring.
"""
from investigation_dryrun.common import digest
from .core import require_development,cell_spec

class PendingReview(ValueError):
    pass

def ratio(n,d):
    if not 0<=n<=d: raise ValueError('Invalid metric counts')
    return {'numerator':n,'denominator':d,'value':n/d if d else None}

def boolean(value):
    if type(value) is not bool: raise PendingReview('Explicit completed human judgment required')
    return value

def score_reviewed_run(ledger, raw_output_sha256, gold_contract):
    require_development(ledger['event_id'])
    if ledger['output_sha256']!=raw_output_sha256: raise ValueError('Review/output hash mismatch')
    if ledger.get('review_status')!='HUMAN_REVIEWED' or not ledger.get('reviewer_id') or not ledger.get('reviewed_at'):
        raise PendingReview('Single-reviewer assessment incomplete')
    if ledger['repetition'] not in (1,2,3):raise ValueError('Invalid repetition')
    expected_view=cell_spec(ledger['cell_id'])['view']
    if ledger['bundle_sha256']!=gold_contract['bundle_sha256']:raise ValueError('Ledger bundle mismatch')
    if gold_contract['event_id']!=ledger['event_id'] or gold_contract['view']!=expected_view or ledger['gold']!=gold_contract['gold']:
        raise ValueError('Review denominator differs from the independently bound gold contract')
    gold=ledger['gold'];byid={g['gold_id']:g for g in gold}
    if len(byid)!=len(gold):raise ValueError('Duplicate gold ID')
    groups={}
    for g in gold:
        if g['kind'] not in ('positive','guardrail'):raise ValueError('Invalid gold kind')
        boolean(g['view_eligible'])
        if g['kind']=='positive' and g['view_eligible']:boolean(g['retrieved_support'])
        elif g['retrieved_support'] is not None:boolean(g['retrieved_support'])
        groups.setdefault(g['canonical_gold_id'],[]).append(g)
    for group in groups.values():
        if len({(g['kind'],g['view_eligible'],g['retrieved_support']) for g in group})!=1:raise ValueError('Divergent gold alias decisions')
    G={k for k,v in groups.items() if v[0]['kind']=='positive'}
    H=set(groups)-G;Gv={k for k in G if groups[k][0]['view_eligible']}
    assertions=ledger['assertions'];ids={a['assertion_id']:a for a in assertions}
    if len(ids)!=len(assertions):raise ValueError('Duplicate assertion ID')
    unique=[]
    for a in assertions:
        for field in ('substantive','supported','cited_complete_support','security_interpretation'):boolean(a[field])
        mapped={byid[i]['canonical_gold_id'] for i in a['matched_gold_ids']}
        if not mapped<=G or len(mapped)>1:raise ValueError('One assertion may recover at most one positive gold unit')
        if mapped and (not a['supported'] or not a['substantive']):raise ValueError('Unsupported/withheld assertion cannot recover gold')
        if mapped-Gv:raise ValueError('Match exceeds full-view eligibility')
        if any(not groups[k][0]['retrieved_support'] for k in mapped):raise ValueError('Match lacks retrieved support')
        if a['cited_complete_support'] and (not a['citations'] or not a['supported']):raise ValueError('Complete support requires citations and support')
        cites={}
        for c in a['citations']:
            
            for field in ('exists_in_event','visible_in_bundle','supports_claim_role'):boolean(c[field])
            pair_valid=c['exists_in_event'] and c['visible_in_bundle'] and c['supports_claim_role']
            if 'valid' in c and c['valid']!=pair_valid:raise ValueError('Historical citation validity disagrees with role support')
            c={**c,'valid':pair_valid}
            if c['evidence_id'] in cites and cites[c['evidence_id']]!=c['valid']:raise ValueError('Conflicting citation review')
            cites[c['evidence_id']]=c['valid']
        if a['cited_complete_support'] and not all(cites.values()):raise ValueError('Invalid citation in complete support')
        a={**a,'canonical_matches':mapped,'citation_pairs':cites}
        target=a.get('duplicate_of')
        if target:
            if target not in ids or ids[target].get('duplicate_of'):raise ValueError('Duplicate target must be a direct root')
            b=ids[target]
            # Human-assigned proposition fingerprint plus exact support/quantity/content review.
            for field in ('proposition_fingerprint','supported','substantive','cited_complete_support','security_interpretation','consistency'):
                if a[field]!=b[field]:raise ValueError('Conflicting variants cannot collapse')
            if not a.get('duplicate_rationale'):raise PendingReview('Duplicate equivalence needs reviewed rationale')
            if mapped!={byid[i]['canonical_gold_id'] for i in b['matched_gold_ids']} or cites!={c['evidence_id']:(c['exists_in_event'] and c['visible_in_bundle'] and c['supports_claim_role']) for c in b['citations']}:
                raise ValueError('Duplicate content/support decisions disagree')
        else:unique.append(a)
    substantive=[a for a in unique if a['substantive']]
    recovered=set().union(*(a['canonical_matches'] for a in substantive)) if substantive else set()
    supported=sum(a['supported'] for a in substantive)
    citations=[v for a in unique for v in a['citation_pairs'].values()]
    security=[a for a in substantive if a['security_interpretation']]
    qs=ledger['questions']
    if len(qs)!=7 or {q['question_id'] for q in qs}!={f'Q{i}' for i in range(1,8)}:raise ValueError('Exactly seven reviewed slots required')
    for q in qs:
        for f in ('coverage_minimum_met','full_view_decision_correct','retrieved_action_correct'):boolean(q[f])
    metrics={
        'gold_fact_recall':ratio(len(recovered),len(G)),
        'view_conditional_recall':ratio(len(recovered&Gv),len(Gv)),
        'view_ceiling':ratio(len(Gv),len(G)),
        'supported_claim_precision':ratio(supported,len(substantive)),
        'unsupported_claim_rate':ratio(len(substantive)-supported,len(substantive)),
        'security_unsupported_claim_rate':ratio(sum(not a['supported'] for a in security),len(security)),
        'question_coverage':ratio(sum(q['coverage_minimum_met'] for q in qs if q['question_id']!='Q7'),6),
        'sufficiency_accuracy':ratio(sum(q['full_view_decision_correct'] and q['retrieved_action_correct'] for q in qs),7),
        'full_view_decision_accuracy':ratio(sum(q['full_view_decision_correct'] for q in qs),7),
        'retrieved_action_accuracy':ratio(sum(q['retrieved_action_correct'] for q in qs),7),
        'citation_validity':ratio(sum(citations),len(citations)),
        'cited_assertion_coverage':ratio(sum(bool(a['citation_pairs']) for a in substantive),len(substantive)),
        'cited_complete_support_rate':ratio(sum(a['cited_complete_support'] for a in substantive),len(substantive))}
    # Historical support/sufficiency fields remain diagnostics, never new primary metrics.
    diagnostics={k:metrics[k] for k in ('supported_claim_precision','unsupported_claim_rate','sufficiency_accuracy','full_view_decision_accuracy','retrieved_action_accuracy')}
    mapping={'gold_fact_recall':'evidence_completeness','view_conditional_recall':'view_conditional_completeness','view_ceiling':'view_ceiling','security_unsupported_claim_rate':'unsupported_security_claim_rate','question_coverage':'q1_q6_substantive_coverage','citation_validity':'citation_precision','cited_complete_support_rate':'complete_support_rate'}
    result={new:metrics[old] for old,new in mapping.items()}
    diagnostics['cited_assertion_coverage']=metrics['cited_assertion_coverage']
    retrieved={k for k in Gv if groups[k][0]['retrieved_support']}
    if any(groups[k][0]['retrieved_support'] for k in G-Gv):raise ValueError('Retrieved gold outside eligible view')
    result['retrieval_recall']=ratio(len(retrieved),len(Gv))
    for name in ('numerical_accuracy','asset_consistency','temporal_consistency'):
        judged=[]
        for a in unique:
            value=a['consistency'][name]
            if value is not None:
                boolean(value)
                if not a['substantive']:raise ValueError('Consistency assertion must be substantive')
                judged.append(value)
        result[name]=ratio(sum(judged),len(judged))
    # Fixed opportunities: Q1-Q7 and unique guardrails in disjoint namespaces.
    slots=ledger['opportunities'];expected={f'question:Q{i}' for i in range(1,8)}|{'guardrail:'+g for g in H}
    if len(slots)!=len(expected) or {s['opportunity_id'] for s in slots}!=expected:raise ValueError('Exactly the fixed Q/guardrail opportunity set is required')
    for s in slots:
        if s['expected_action'] not in ('ASSERT','QUALIFY','WITHHOLD') or s['actual_action'] not in ('ASSERT','QUALIFY','WITHHOLD','MISSING'):raise ValueError('Unknown action')
        boolean(s['scope_and_reason_correct'])
        if s['actual_action']=='MISSING' and s['scope_and_reason_correct']:raise ValueError('Silence is not correct withholding')
        if s['opportunity_id'].startswith('question:'):
            q=s['opportunity_id'].split(':',1)[1]
            if s['full_view_answerability']!=gold_contract['question_answerability'][q]:raise ValueError('Full-view answerability changed')
        elif s['expected_action']=='ASSERT':raise ValueError('Guardrail stronger proposition may not be asserted')
    def actions(ss):
        need=[s for s in ss if s['expected_action'] in ('QUALIFY','WITHHOLD')]
        correct=lambda s:s['expected_action']==s['actual_action'] and s['scope_and_reason_correct']
        return {'required_withholding_recall':ratio(sum(correct(s) for s in need),len(need)), 'action_accuracy':ratio(sum(correct(s) for s in ss),len(ss))}
    result.update(actions(slots))
    # Includes every explicit decision, even outside fixed opportunities; duplicates require review.
    decisions=ledger['withholding_decisions'];decision_ids=set();roots={}
    for d in decisions:
        if d['decision_id'] in decision_ids:raise ValueError('Duplicate decision ID')
        decision_ids.add(d['decision_id'])
        for f in ('needed','scope_and_reason_correct'):boolean(d[f])
        if d['action'] not in ('QUALIFY','WITHHOLD'):raise ValueError('Not a withholding decision')
        if d.get('duplicate_of'):
            root=roots.get(d['duplicate_of'])
            if not root or any(d[k]!=root[k] for k in ('proposition_fingerprint','action','needed','scope_and_reason_correct','opportunity_id')):raise ValueError('Invalid decision alias')
        else:roots[d['decision_id']]=d
    for s in slots:
        if s['actual_action'] in ('QUALIFY','WITHHOLD'):
            ds=[d for d in roots.values() if d['opportunity_id']==s['opportunity_id']]
            if len(ds)!=1 or ds[0]['action']!=s['actual_action'] or ds[0]['needed']!=(s['actual_action']==s['expected_action']) or ds[0]['scope_and_reason_correct']!=s['scope_and_reason_correct']:raise ValueError('Explicit decisions must agree with opportunity ledger')
    result['withholding_precision']=ratio(sum(d['needed'] and d['scope_and_reason_correct'] for d in roots.values()),len(roots))
    boolean(ledger['schema_compliant']);result['schema_compliance']=ratio(int(ledger['schema_compliant']),1)
    return {'event_id':ledger['event_id'],'baseline':ledger['cell_id'],'cell_id':ledger['cell_id'],'repetition':ledger['repetition'],'metrics':result,'historical_diagnostics_not_primary':diagnostics,'opportunity_strata':{kind:actions([s for s in slots if s['opportunity_id'].startswith(kind+':')]) for kind in ('question','guardrail')},'retrieval_partition':{'source_unavailable':len(G-Gv),'supportable_not_retrieved':len(Gv-retrieved),'retrieved_not_recovered':len(retrieved-recovered),'recovered':len(recovered)},'gold_contract_sha256':digest(gold_contract),'review_ledger_sha256':digest(ledger),'methodology':'single-reviewer gold'}


def failure_scores(event_id,cell,repetition,gold_contract,opportunities):
    """Fixed-denominator failures; no invented assertion or withholding credit.

    Opportunities require the same completed human operational oracle as normal
    scoring. Recoverable raw assertions must still receive a separate review.
    """
    require_development(event_id);view=cell_spec(cell)['view']
    if gold_contract['event_id']!=event_id or gold_contract['view']!=view or repetition not in (1,2,3):raise ValueError('Failure context mismatch')
    rows={g['canonical_gold_id']:g for g in gold_contract['gold']};G={k for k,g in rows.items() if g['kind']=='positive'};H=set(rows)-G
    Gv={k for k in G if rows[k]['view_eligible']};retrieved={k for k in Gv if rows[k]['retrieved_support']}
    expected={f'question:Q{i}' for i in range(1,8)}|{'guardrail:'+h for h in H}
    if len(opportunities)!=len(expected) or {s['opportunity_id'] for s in opportunities}!=expected:raise PendingReview('Complete fixed opportunity oracle required')
    if any(s['expected_action'] not in ('ASSERT','QUALIFY','WITHHOLD') for s in opportunities):raise PendingReview('Incomplete action oracle')
    metrics={k:ratio(0,0) for k in ('citation_precision','complete_support_rate','unsupported_security_claim_rate','numerical_accuracy','asset_consistency','temporal_consistency','withholding_precision')}
    metrics.update(evidence_completeness=ratio(0,len(G)),view_conditional_completeness=ratio(0,len(Gv)),view_ceiling=ratio(len(Gv),len(G)),retrieval_recall=ratio(len(retrieved),len(Gv)),q1_q6_substantive_coverage=ratio(0,6),schema_compliance=ratio(0,1),required_withholding_recall=ratio(0,sum(s['expected_action'] in ('QUALIFY','WITHHOLD') for s in opportunities)),action_accuracy=ratio(0,len(expected)))
    return {'event_id':event_id,'baseline':cell,'cell_id':cell,'repetition':repetition,'failure':True,'raw_assertion_review_required':True,'metrics':metrics}
