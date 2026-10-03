"""Evaluator-side blank review packet; no evaluation reading or annotation."""
from .contracts import VERSION,sha,digest
from .scoring import decode,surfaces

def review_worksheet(event_id,cell_id,repetition,raw_bytes,stage_bytes,bundle,gold_sha256):
 source=decode(stage_bytes)
 if cell_id=='V1-EN':
  source={k:source[k] for k in ('published_report','dispositions','question_actions')}
 return {'version':VERSION,'status':'PENDING_R1_NOT_SCOREABLE','event_id':event_id,'cell_id':cell_id,
 'repetition':repetition,'output_stage':'VERIFIED_PUBLISHED' if cell_id=='V1-EN' else ('DETERMINISTIC_REFERENCE' if cell_id=='D0' else 'RAW_GENERATED'),
 'raw_output_sha256':sha(raw_bytes),'stage_artifact_sha256':sha(stage_bytes),'bundle_sha256':digest(bundle),
 'gold_sha256':gold_sha256,'reviewer_id':'R1','reviewed_at':None,'all_text_reviewed':False,
 'reviewed_surfaces':[{'pointer':p,'text':s,'assertion_ids':[],'nonassertive_reason':None} for p,s in surfaces(source).items()],
 'assertions':[],'questions':[{'question_id':f'Q{i}','adequate_assertion_ids':[],'adequate':None,'reason':None} for i in range(1,8)],
 'actions':[],'instructions':'R1 inspects every actual text surface and atomizes every substantive proposition, including free prose and disguised security claims; fill the strict review_ledger schema. This worksheet is not a completed review.'}
