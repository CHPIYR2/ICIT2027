"""Local tokenizer audit; never changes evidence selection or invokes a model."""
import os
import math
import statistics
import importlib.metadata
from .common import ROOT, dumps, digest, file_hash, binding
from .custody import development_ids, read_bundle

MODEL = 'gpt-4.1-2025-04-14'

def encoder():
    os.environ.setdefault('TIKTOKEN_CACHE_DIR', str(ROOT / '.cache/tiktoken'))
    import tiktoken
    if importlib.metadata.version('tiktoken') != '0.12.0': raise ValueError('Unpinned tokenizer')
    enc = tiktoken.encoding_for_model(MODEL)
    if enc.name != 'o200k_base': raise ValueError('Tokenizer mapping changed')
    return enc

def count(text):
    return len(encoder().encode(text, disallowed_special=()))

def quantile(values, q):
    values = sorted(values)
    if not values: return None
    i = (len(values)-1)*q; lo = math.floor(i); hi = math.ceil(i)
    return values[lo] + (values[hi]-values[lo])*(i-lo)

def summary(values):
    return {'n': len(values), 'minimum': min(values), 'median': statistics.median(values),
            'p90': quantile(values, .9), 'p95': quantile(values, .95), 'maximum': max(values)}

def audit(log_path, prompt_texts):
    rows = []
    for eid in development_ids():
        for view in ('N', 'EN'):
            b, r = read_bundle(eid, view, log_path)
            s = dumps(b)
            rows.append({'event_id': eid, 'view': view, 'tokens': count(s), 'bytes': len(s.encode()),
                         'serialization_sha256': digest(b), 'receipt_sha256': digest(r),
                         'source_files': [binding(ROOT/f'results/investigation-v2/B0/{eid}/{view}/{f}') for f in ('retrieved.json','receipt.json')]})
    maximum = max(r['tokens'] for r in rows)
    # Minimal integer cap covering both approved production views. No headroom guess/truncation.
    budget = maximum
    candidates = sorted(set([8192, 16384, 32768, budget]))
    prompt_counts = {b: count(t) for b,t in prompt_texts.items()}
    return {'status': 'DEVELOPMENT_EVIDENCE_ONLY_NO_ANSWERS', 'model_candidate': MODEL,
            'tokenizer': 'tiktoken==0.12.0/o200k_base', 'quantiles': 'linear interpolation, index=(n-1)*q',
            'serialization': 'json.dumps(sort_keys=True,separators=(comma,colon),allow_nan=False), default ensure_ascii=True; exact existing production rule',
            'views': {v: summary([r['tokens'] for r in rows if r['view']==v]) for v in ('N','EN')},
            'exceeding_evidence_token_caps': {str(c): {v: sum(r['tokens']>c for r in rows if r['view']==v) for v in ('N','EN')} for c in candidates},
            'proposed_fixed_evidence_tokens': budget, 'proposal_rule': 'maximum over all 16 development events x both production views; common cap, zero empirical exceedances; future overflow records a preflight failure and never trims/retrieves differently',
            'author_approval': 'PENDING', 'prompt_text_tokens': prompt_counts,
            'max_output_tokens_candidate': 32768, 'output_budget_basis': 'published model maximum; no answer-dependent cap tuning',
            'provider_context_tokens': 1047576,
            'context_diagnostics': {str(c): {v: sum(r['tokens']+max(prompt_counts.values())+32768>c for r in rows if r['view']==v) for v in ('N','EN')} for c in (65536,131072,1047576)},
            'context_count_limit': 'Local counts cover serialized evidence and instruction text, not provider message framing. Provider usage must be logged; API truncation disabled. No claim of exact full API input-token count.',
            'evaluation_events_accessed': 0, 'model_answers_inspected': 0, 'generation_calls': 0, 'rows': rows}
