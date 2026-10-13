"""Optional Ollama explanation only; model output cannot create graph edges."""
import json
from pathlib import Path
from urllib.request import Request, urlopen


def explain_graph(graph: dict, *, model: str = 'qwen3.5:9b-q4_K_M',
                  endpoint: str = 'http://127.0.0.1:11434', timeout=180) -> str:
    evidence = {
        'nodes': [{'id': n['id'], 'kind': n['modality'],
                   'entity': n['entity'], 'source_ids': n['source_ids'][:3]}
                  for n in graph['nodes']],
        'edges': [{'source': e['source'], 'target': e['target'],
                   'relation': e['type'], 'association_score': e['score'],
                   'evidence_ids': e['evidence_ids'][:4]}
                  for e in graph['edges'][:60]]}
    instructions = (
        'You are analyzing an already-alerted OT incident. Interpret only the given '
        'observed nodes and LEARNED statistical graph edges. Explain network-network, '
        'physical-physical and network-physical associations if observed. Explicitly '
        'state that edges are NOT proof of causation, attack attribution, or operational '
        'success. Do NOT assign a numerical correctness probability or hallucinate '
        'evidence IDs, raw fields, or attack labels. Discuss alternative explanations '
        'and missing evidence. Answer in Traditional Chinese. Cite only IDs appearing '
        'in input. Do not change the graph or scores. Input follows:\n'
    )
    payload = {'model': model,
               'messages': [{'role': 'user', 'content': instructions + json.dumps(evidence, ensure_ascii=False)}],
               'stream': False, 'options': {'temperature': 0, 'num_ctx': 8192}}
    req = Request(endpoint.rstrip('/') + '/api/chat',
                  json.dumps(payload).encode('utf-8'),
                  headers={'Content-Type': 'application/json'})
    with urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data['message']['content']
