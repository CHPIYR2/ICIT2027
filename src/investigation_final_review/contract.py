"""Authenticated scope-context binding around the unchanged Chapter 5 scorer.

Gold's inventory describes source evidence. Bundle scope describes the visible
observation contract and is already a valid unknown-claim citation in the frozen
verifier. Keep these inventories separate on disk; merge only their identity
indexes at the scorer boundary. No facts, support sets, or arithmetic change.
"""
import ast
import copy
import inspect
import types
from pathlib import Path

from investigation_dryrun.common import ROOT, load, file_hash, digest as evidence_digest
from investigation_final_offline.contracts import digest, VIEWS
from investigation_final_offline import scoring, pipeline
from retrieval.investigation_retriever_v2 import validate_bundle


def need(ok, message):
    if not ok:
        raise ValueError(message)


def scoring_view(bundle):
    records = [*bundle['entries'], *bundle['metadata'].values(),
               *bundle['control_metadata'].values(), bundle['scope']]
    ids = [r['evidence_id'] for r in records]
    need(len(ids) == len(set(ids)), 'Duplicate source/context identity')
    return {'event_id': bundle['scope']['event_id'], 'view': bundle['scope']['view'],
            'source_bundle_sha256': evidence_digest(bundle),
            'visible_evidence_ids': sorted(ids), 'visible_records': records}


def mapping_row(gold, bundle, receipt, gold_path, bundle_path, receipt_path):
    """Only frozen gold/evidence metadata are inputs; no generated text."""
    facts, _, _, evidence = scoring.validate_gold(gold, gold['policy_sha256'])
    validate_bundle(bundle)
    event, view = bundle['scope']['event_id'], bundle['scope']['view']
    need(event == gold['event_id'] == receipt['event_id'], 'Event mismatch')
    need(view == receipt['view'] and evidence_digest(bundle) == receipt['retrieved_bundle_sha256'], 'Receipt mismatch')
    source = [*bundle['entries'], *bundle['metadata'].values(), *bundle['control_metadata'].values()]
    need(all(r['evidence_id'] in evidence and view in evidence[r['evidence_id']]['views'] for r in source), 'Source outside gold view inventory')
    scope = bundle['scope']
    need(scope['evidence_id'] not in evidence, 'Scope unexpectedly collides with source inventory')
    full = sorted(facts)
    supportable = sorted(k for k, f in facts.items() if f['views'][view]['supportable'])
    inventory = [copy.deepcopy(evidence[k]) for k in sorted(evidence) if view in evidence[k]['views']]
    def ref(path):
        return {'path': str(Path(path).absolute()), 'sha256': file_hash(path)}
    return {'event_id': event, 'view': view, 'bundle': ref(bundle_path), 'receipt': ref(receipt_path),
            'bundle_sha256': evidence_digest(bundle), 'gold': ref(gold_path),
            'gold_sha256': digest(gold), 'gold_commitment_sha256': gold['commitment_sha256'],
            'full_EN_gold_ids': full, 'full_EN_inventory_sha256': digest(gold['positive_facts']),
            'view_supportable_gold_ids': supportable,
            'view_supportability_sha256': digest([{'gold_id': f['gold_id'], 'fields': f['fields'],
                'supportability': f['views'][view]} for f in gold['positive_facts']]),
            'view_source_inventory': inventory, 'view_source_inventory_sha256': digest(inventory),
            'scope_context': copy.deepcopy(scope), 'scope_context_sha256': digest(scope),
            'scorer_bundle_sha256': digest(scoring_view(bundle)),
            'EC_denominator_inventory': 'full_EN_gold_ids',
            'VCC_denominator_inventory': 'view_supportable_gold_ids',
            'scope_role': 'visible observation-contract context; not a positive gold fact or source observation'}


class ScopeContract:
    def __init__(self, document, expected_sha256, *, expected_events=None):
        need(document['mapping_sha256'] == expected_sha256 == digest({k: v for k, v in document.items() if k != 'mapping_sha256'}), 'Mapping seal changed')
        rows = document['mappings']
        self.rows = {(r['event_id'], r['view']): r for r in rows}
        events = document['event_ids']
        if expected_events is not None:
            need(events == list(expected_events), 'Canonical event set/order changed')
        need(len(events) == len(set(events)) and len(self.rows) == len(rows) == len(events) * 3, 'Duplicate/missing mappings')
        need(set(self.rows) == {(e, v) for e in events for v in ('E', 'N', 'EN')}, 'Orphan/missing view')
        self.policy = document['matching_support_policy_sha256']
        self.gold, self.bundles, self.context = {}, {}, {}
        for key, row in self.rows.items():
            for kind in ('bundle', 'receipt', 'gold'):
                ref = row[kind]
                need(file_hash(ref['path']) == ref['sha256'], 'Frozen mapping input changed: ' + kind)
            g, b, receipt = (load(row[k]['path']) for k in ('gold', 'bundle', 'receipt'))
            need(g['policy_sha256'] == self.policy, 'Mapping policy mismatch')
            rebuilt = mapping_row(g, b, receipt, row['gold']['path'], row['bundle']['path'], row['receipt']['path'])
            need(rebuilt == row, 'Mapping is not mechanically derived from frozen inputs')
            self.gold[key[0]] = g
            self.bundles[key] = scoring_view(b)
            sid = b['scope']['evidence_id']
            event_context = self.context.setdefault(key[0], {})
            need(sid not in event_context, 'Scope reused across views')
            event_context[sid] = {'evidence_id': sid, 'sha256': digest(b['scope']), 'views': [key[1]]}

    def evidence_index(self, gold, policy):
        event = gold['event_id']
        need(event in self.gold and digest(gold) == digest(self.gold[event]) and policy == self.policy, 'Unbound gold/policy')
        facts, aliases, opportunities, evidence = scoring.validate_gold(gold, policy)
        need(not (set(evidence) & set(self.context[event])), 'Context/source collision')
        return facts, aliases, opportunities, {**evidence, **self.context[event]}

    def check_bundle(self, bundle):
        key = bundle['event_id'], bundle['view']
        need(key in self.bundles and bundle == self.bundles[key], 'Scorer view differs from frozen mapping')

    def scoped_function(self, fn):
        namespace = {**fn.__globals__, 'validate_gold': self.evidence_index}
        return types.FunctionType(fn.__code__, namespace, fn.__name__, fn.__defaults__, fn.__closure__)

    def score(self, ledger, gold, bundle, raw, stage, **kwargs):
        """Future scoring entry; never called on final data during preparation."""
        self.check_bundle(bundle)
        return self.scoped_function(scoring.score)(ledger, gold, bundle, raw, stage, **kwargs)

    def score_delivery_failure(self, event, cell, rep, gold, bundle, receipt, **kwargs):
        self.check_bundle(bundle)
        return self.scoped_function(scoring.score_delivery_failure)(event, cell, rep, gold, bundle, receipt, **kwargs)

    def score_committed_packet(self, packet, *, trusted_commitment_sha256):
        """Preserve the original committed-matrix boundary and all arithmetic."""
        fn = pipeline.score_committed_packet
        namespace = {**fn.__globals__, 'score': self.score, 'score_delivery_failure': self.score_delivery_failure}
        return types.FunctionType(fn.__code__, namespace)(packet, trusted_commitment_sha256=trusted_commitment_sha256)

    def validate_ledger(self, ledger, gold, bundle, raw, stage):
        """Run the frozen score function's validation prefix, without metrics.

        Stop before its first metrics assignment. This preserves every existing
        text/span, citation, support, coverage and action validation expression.
        """
        self.check_bundle(bundle)
        need(ledger['delivery'] == 'VALID' and scoring.delivery_valid(ledger['delivery_receipt'], ledger['event_id'], ledger['cell_id'], ledger['repetition']), 'Invalid provider delivery is not reviewable')
        tree = ast.parse(inspect.getsource(scoring.score))
        fn = tree.body[0]
        cut = next(i for i, node in enumerate(fn.body) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'metrics' for t in node.targets))
        fn.body = fn.body[:cut] + [ast.Return(value=ast.Constant(value=None))]
        ast.fix_missing_locations(tree)
        namespace = {**scoring.score.__globals__, 'validate_gold': self.evidence_index}
        exec(compile(tree, '<frozen-review-validation-prefix>', 'exec'), namespace)
        namespace['score'](ledger, gold, bundle, raw, stage, matching_policy_sha256=self.policy)


def mechanical_fields(ledger, evidence):
    """Recompute only identity/bookkeeping and Boolean consequences of R1 inputs."""
    visible = set(evidence['visible_evidence_ids'])
    # Existence is supplied by the complete mapped event inventory at caller.
    for row in ledger['reviewed_surfaces']:
        row['assertion_ids'] = [a['assertion_id'] for a in ledger['assertions'] if a['source']['pointer'] == row['pointer']]
        if row['assertion_ids'] and row['nonassertive_reason'] is None:
            row['nonassertive_reason'] = ''
    for q in ledger['questions']:
        if q['adequate_assertion_ids'] is not None:
            q['adequate'] = bool(q['adequate_assertion_ids'])
    for a in ledger['assertions']:
        for c in a['citations']:
            c['visible'] = c['evidence_id'] in visible
        if a['substantive'] is not None and a['supported'] is not None and a['required_support_sets'] is not None and all(c['role_supported'] is not None for c in a['citations']):
            cs = a['citations']
            full = bool(cs) and all(c['exists'] and c['visible'] and c['role_supported'] for c in cs) and any(set(s) <= {c['evidence_id'] for c in cs} for s in a['required_support_sets'])
            a['cited_complete_support'] = bool(a['substantive'] and a['supported'] and full)
    return ledger
