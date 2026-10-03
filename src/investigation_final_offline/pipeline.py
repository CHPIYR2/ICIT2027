"""Offline, in-memory scoring boundary with separately trusted manifest digest.

No filesystem or API access. A future custodian loads only authorized committed
inputs under OS ACLs; this function never sends evaluator inputs to generation.
"""
from .contracts import digest,sha,VIEWS
from .scoring import score,score_delivery_failure,need
from .reporting import products

def score_committed_packet(packet,*,trusted_commitment_sha256):
 manifest=packet['manifest']
 need(digest(manifest)==trusted_commitment_sha256,'Untrusted scoring commitment')
 label=manifest['data_label'];synthetic=label=='SYNTHETIC_TEST_ONLY_NOT_PAPER_RESULTS'
 need(synthetic or (label=='FROZEN_EVALUATION_REVIEWED' and manifest['protocol_frozen'] and manifest['separate_scoring_authorization_sha256']),'Frozen scoring authorization absent')
 ids=manifest['event_ids'];need(len(ids)==len(set(ids)),'Duplicate event selection')
 if synthetic:need(all(e.startswith('SYNTHETIC_') for e in ids),'Development/final data cannot be relabeled synthetic')
 else:need(len(ids)==32 and manifest['gold_committed_before_output_review'] and manifest['custody_receipt_sha256'],'Final commitment/custody incomplete')
 expected={(e,c,r) for e in ids for c in VIEWS for r in ((0,) if c=='D0' else (1,2,3))}
 bindings={(b['event_id'],b['cell_id'],b['repetition']):b for b in manifest['positions']}
 need(len(bindings)==len(manifest['positions']) and set(bindings)==expected,'Complete 384+96+32 (or synthetic analogue) position commitment required')
 seen=set();scores=[]
 for item in packet['inputs']:
  key=(item['event_id'],item['cell_id'],item['repetition']);need(key in bindings and key not in seen,'Unexpected/duplicate position input');seen.add(key)
  ref=bindings[key];need(digest(item)==ref['input_sha256'],'Committed scoring input changed')
  for k in ('gold','bundle','delivery_receipt'):
   need(digest(item[k])==ref[k+'_sha256'],'Independent '+k+' commitment changed')
  need(item['delivery_receipt']['source_record_sha256']==ref['delivery_source_record_sha256'],'Delivery source record mismatch')
  if item['kind']=='NO_PROVIDER_DELIVERY':
   result=score_delivery_failure(*key,item['gold'],item['bundle'],item['delivery_receipt'],matching_policy_sha256=manifest['matching_policy_sha256'])
  else:
   need(item['kind']=='REVIEWED_OUTPUT','Unknown input kind')
   need(digest(item['ledger'])==ref['review_ledger_sha256'],'Review ledger not committed')
   need(item['ledger']['delivery_receipt']==item['delivery_receipt'],'Review cannot replace provider delivery receipt')
   raw=item['raw_utf8'].encode();stage=item['stage_utf8'].encode()
   need(sha(raw)==ref['raw_output_sha256'] and sha(stage)==ref['stage_output_sha256'],'Committed output bytes changed')
   result=score(item['ledger'],item['gold'],item['bundle'],raw,stage,matching_policy_sha256=manifest['matching_policy_sha256'])
   need((result['event_id'],result['cell_id'],result['repetition'])==key,'Ledger position differs')
  if not synthetic:
   result.update(frozen_evaluation_commitment=trusted_commitment_sha256,scoring_authorization=manifest['separate_scoring_authorization_sha256'])
  scores.append(result)
 need(seen==expected,'Missing planned input; no selection of completed/best repetitions')
 report=products(scores,manifest['scenario_strata'],data_label=label)
 report['protocol_frozen']=not synthetic
 report['scoring_commitment_sha256']=trusted_commitment_sha256
 return scores,report
