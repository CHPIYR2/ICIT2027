"""Exact metric arithmetic over completed, hash-bound human review ledgers.

No verifier verdict is used as a human support/semantic oracle. This module never
loads gold, model outputs, or arbitrary paths itself. Pending reviews block scoring.
"""
from .common import digest
from .custody import require_development

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
    if ledger['baseline'] not in ('B0','B1','B2','B3','B4') or ledger['repetition'] not in (1,2,3):raise ValueError('Invalid cell')
    expected_view='N' if ledger['baseline']=='B1' else 'EN'
    if gold_contract['event_id']!=ledger['event_id'] or gold_contract['view']!=expected_view or ledger['gold']!=gold_contract['gold']:
        raise ValueError('Review denominator differs from the independently bound gold contract')
    gold=ledger['gold'];byid={g['gold_id']:g for g in gold}
    if len(byid)!=len(gold):raise ValueError('Duplicate gold ID')
    groups={}
    for g in gold:
        if g['kind'] not in ('positive','guardrail'):raise ValueError('Invalid gold kind')
        boolean(g['view_eligible']);groups.setdefault(g['canonical_gold_id'],[]).append(g)
    for group in groups.values():
        if len({(g['kind'],g['view_eligible']) for g in group})!=1:raise ValueError('Divergent gold alias decisions')
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
        if a['cited_complete_support'] and (not a['citations'] or not a['supported']):raise ValueError('Complete support requires citations and support')
        cites={}
        for c in a['citations']:
            boolean(c['valid'])
            if c['evidence_id'] in cites and cites[c['evidence_id']]!=c['valid']:raise ValueError('Conflicting citation review')
            cites[c['evidence_id']]=c['valid']
        if a['cited_complete_support'] and not all(cites.values()):raise ValueError('Invalid citation in complete support')
        a={**a,'canonical_matches':mapped,'citation_pairs':cites}
        target=a.get('duplicate_of')
        if target:
            if target not in ids or ids[target].get('duplicate_of'):raise ValueError('Duplicate target must be a direct root')
            b=ids[target]
            # Human-assigned proposition fingerprint plus exact support/quantity/content review.
            for field in ('proposition_fingerprint','supported','substantive','cited_complete_support','security_interpretation'):
                if a[field]!=b[field]:raise ValueError('Conflicting variants cannot collapse')
            if not a.get('duplicate_rationale'):raise PendingReview('Duplicate equivalence needs reviewed rationale')
            if mapped!={byid[i]['canonical_gold_id'] for i in b['matched_gold_ids']} or cites!={c['evidence_id']:c['valid'] for c in b['citations']}:
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
    verifier_diagnostics=None
    if ledger['baseline']=='B4':
        units=ledger['verifier_input_units'];uid={u['unit_id']:u for u in units}
        if len(uid)!=len(units):raise ValueError('Duplicate verifier oracle unit')
        retained=[]
        for u in units:
            boolean(u['disposition_correct']);boolean(u['content_and_reason_correct'])
            if u['expected_disposition'] not in ('SUPPORTED','QUALIFIED','INSUFFICIENT') or u['actual_disposition'] not in ('SUPPORTED','QUALIFIED','INSUFFICIENT','MISSING'):
                raise ValueError('Invalid independent disposition oracle')
            if u['disposition_correct'] != (u['actual_disposition']==u['expected_disposition']):raise ValueError('Disposition correctness disagrees with oracle')
            if u.get('duplicate_of'):
                b=uid[u['duplicate_of']]
                if b.get('duplicate_of') or any(u[f]!=b[f] for f in ('proposition_fingerprint','disposition_correct','content_and_reason_correct','expected_disposition','actual_disposition')):raise ValueError('Conflicting verifier duplicate')
            else:retained.append(u)
        confusion={e:{a:sum(u['expected_disposition']==e and u['actual_disposition']==a for u in retained) for a in ('SUPPORTED','QUALIFIED','INSUFFICIENT','MISSING')} for e in ('SUPPORTED','QUALIFIED','INSUFFICIENT')}
        supported_oracle=[u for u in retained if u['expected_disposition']=='SUPPORTED']
        verifier_diagnostics={'confusion_counts':confusion,'class_denominators':{e:sum(row.values()) for e,row in confusion.items()},'supported_claim_false_withhold_rate':ratio(sum(u['actual_disposition'] in ('INSUFFICIENT','MISSING') for u in supported_oracle),len(supported_oracle))}
        metrics['verifier_disposition_accuracy']=ratio(sum(u['disposition_correct'] and u['content_and_reason_correct'] for u in retained),len(retained))
        slots=ledger['opportunity_actions']
        if len(slots)!=len(G|H) or {s['canonical_gold_id'] for s in slots}!=G|H:raise ValueError('Every fixed opportunity must be reviewed')
        for s in slots:
            boolean(s['addressed']);boolean(s['correct_action_scope_reason'])
            if not s['addressed'] and s['correct_action_scope_reason']:raise ValueError('Unaddressed is not successful withholding')
        for name,keys in [('fixed_opportunity_action_accuracy',G|H),('positive_action_accuracy',G),('guardrail_action_accuracy',H)]:
            metrics[name]=ratio(sum(s['addressed'] and s['correct_action_scope_reason'] for s in slots if s['canonical_gold_id'] in keys),len(keys))
    return {'event_id':ledger['event_id'],'baseline':ledger['baseline'],'repetition':ledger['repetition'],
            'output_sha256':raw_output_sha256,'review_ledger_sha256':digest(ledger),'gold_contract_sha256':digest(gold_contract),'methodology':'single-reviewer gold',
            'metrics':metrics,'verifier_diagnostics':verifier_diagnostics,'counts':{'gold_positive':len(G),'gold_guardrails':len(H),'raw_assertions':len(assertions),'unique_assertions':len(unique),'substantive_assertions':len(substantive),'duplicate_assertions':len(assertions)-len(unique)}}

def failure_scores(event_id,baseline,repetition,positive_denominator,view_positive_denominator):
    require_development(event_id)
    # Recoverable raw text still requires a human ledger; no false perfect precision.
    return {'event_id':event_id,'baseline':baseline,'repetition':repetition,'failure':True,
            'raw_assertion_review_required':True,'metrics':{
            'gold_fact_recall':ratio(0,positive_denominator),'view_conditional_recall':ratio(0,view_positive_denominator),
            'question_coverage':ratio(0,6),'sufficiency_accuracy':ratio(0,7),
            'full_view_decision_accuracy':ratio(0,7),'retrieved_action_accuracy':ratio(0,7),
            'supported_claim_precision':ratio(0,0),'unsupported_claim_rate':ratio(0,0),'citation_validity':ratio(0,0)}}
