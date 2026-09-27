"""Build a reviewable NOT-FROZEN package only after the complete dry run audit."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,file_hash,binding,create_json,utc
OUT=ROOT/'results/investigation-dryrun-v1'
usage=load(OUT/'api_usage_and_cost.json')
r=load(OUT/'final_conformance_report.json');effective=r['effective_144_slots'];allruns=r['all_retained_delivery_cells'];b4=r['B4']
assert effective['generation_cells']==144 and r['authorized_recovery']['generation_cells']==86 and b4['effective_replays']==48
prompt=load(ROOT/'prompts/investigation-v1-r4/manifest.v1.json')
model=load(ROOT/'configs/investigation-dryrun-v1/model.candidate.json')
truncated=effective['truncation_count']
counts='\n'.join(f"| {b} | {x.get('DELIVERED',0)} | {x.get('DELIVERED_SCHEMA_INVALID',0)} | {x.get('PROVIDER_INCOMPLETE',0)} | {48-sum(x.get(k,0) for k in ['DELIVERED','DELIVERED_SCHEMA_INVALID','PROVIDER_INCOMPLETE'])} |" for b,x in effective['statuses_by_baseline'].items())
tokens='\n'.join(f"| {k} | {v['distribution']['minimum']} | {v['distribution']['median']} | {v['distribution']['p95']} | {v['distribution']['maximum']} | {v['total']} |" for k,v in allruns['usage'].items())
hashes='\n'.join(f"| {ref['path']} | `{ref['sha256']}` |" for ref in [*prompt['prompts'].values(),binding(ROOT/'schemas/investigation_claim.v3.json'),binding(ROOT/'schemas/investigation_verification.v3.json'),binding(ROOT/'schemas/investigation_response.v3.required.json'),binding(ROOT/'schemas/investigation_response.v3.optional_baseline.json'),binding(ROOT/'configs/investigation-dryrun-v1/model.candidate.json'),binding(ROOT/'configs/investigation-dryrun-v1/token_budget.candidate.json')])
text=f'''# Investigation Protocol v1 — Development Dry Run Freeze-Readiness Report

**NOT FROZEN. DEVELOPMENT ONLY. 未執行 32 個評估事件，未讀取評估 gold 或評估結果。**

## 執行與保留紀錄

原排程 144 個 B1/B2/B3 事件×方法×輪次項目全部保留。初次並行排程遇到帳號 30,000 TPM 限制，其中 86 項用完三次傳輸嘗試。作者另行批准這 86 項以相同請求補跑，原紀錄未刪除。總計保留 230 個交付項目；正式開發矩陣仍是 144 個位置，每個事件、方法的三輪皆保留。

補跑來源選擇僅限事先列明、沒有交付答案的純 429 失敗，沒有品質排序、best-of、提示詞修改或規則調整。兩次中斷嘗試沒有可恢復回應，記錄為交付未知並占原本三次上限，沒有捏造 provider status、用量或零費用。

| 方法 | 完成且 schema 通過 | 完成但 schema 不通過 | provider incomplete | 其他失敗 |
|---|---:|---:|---:|---:|
{counts}

有效矩陣的 B4 有 {b4['effective_replays']} 筆重播紀錄，狀態為 `{json.dumps(b4['statuses'],sort_keys=True)}`。其中 {b4['stored_B3_output_count']} 筆有 B3 原始輸出，全部通過 exact-byte hash 檢核；其餘沒有 B3 輸出，不能聲稱完成重播或輸入 identity 檢核。B4 模型呼叫數為 0。沒有完整 B3 時明確記錄 replay unavailable，不補寫 JSON、不重新生成。原排程的 B4 及另批 B3 的 B4 也都保留。

B0 沿用每事件一份既有 deterministic EN timeline，共 16 份，三輪僅引用同一份；不宣稱 48 次獨立 B0 執行。

## 模型、完成狀態與 token

Requested model: `{model['exact_callable_model']}`；實際回傳模型統計：`{json.dumps(allruns['models'],sort_keys=True)}`。API completion status、response ID、HTTP status、request ID、usage、termination reason、request/output hashes 詳見逐次 manifest 與 `final_conformance_report.json`。Temperature 0 不保證位元級重現，Responses seed 不支援。

以下分布涵蓋原排程及補跑全部有 provider usage 的嘗試，不把兩個交付未知嘗試當成零用量；429 無 usage 亦保持缺值。

| token 欄位 | 最小 | 中位數 | p95 | 最大 | 已知總量 |
|---|---:|---:|---:|---:|---:|
{tokens}

有 usage 的嘗試：{allruns['usage_record_count']}；無 usage 的嘗試：{allruns['attempts_without_usage']}。HTTP 統計：`{json.dumps(allruns['HTTP_responses'],sort_keys=True)}`。原有限次重試原因：`{json.dumps(allruns['retry_reasons'],sort_keys=True)}`；另批 86 項授權補跑單独列帳，不隱藏成原輪成功。

有效 144 項每項均記錄 actual evidence tokens，分布：`{json.dumps(effective['evidence_tokens'],sort_keys=True)}`。這與 API input tokens（包括 prompt、strict schema 與 provider framing）不同。

4,096 上限的有效矩陣截斷數：**{truncated}**。每筆截斷須有 `status=incomplete` 且 `incomplete_details.reason=max_output_tokens`，完整證據清單含 response IDs、usage、raw response hashes，位於 JSON 報告。

{('基於這些實際截斷證據，提出 8,192 作為下一個開發候選上限，等待作者批准；本輪沒有自動提高，也沒有因答案品質或分數增加上限。是否再做完整開發验证及其範圍亦需作者決定。' if truncated else '目前沒有實際 max_output_tokens 截斷證據，不提出提高至 8,192。')}

## API usage 與可計算成本

全部有 usage 的原排程及補跑回應，input tokens = {usage['known_usage_totals'].get('input_tokens',0):,}；其中 cached input tokens = {usage['known_usage_totals'].get('cached_input_tokens',0):,}；output tokens = {usage['known_usage_totals'].get('output_tokens',0):,}。Cached input 已包含於 input，不重複相加。

依 [OpenAI 官方 API 單價](https://developers.openai.com/api/docs/pricing)，可計算的已知用量小計為 **USD {usage['known_usage_list_price_subtotal_USD']}**。這不是帳單總額；{usage['unmetered_attempt_count']} 筆嘗試未回傳 usage，不能將交付未知的費用假設為 0。各次 provider meter、cache 分項、原排程／補跑拆分與計算式另見 `results/investigation-dryrun-v1/api_usage_and_cost.json` 及 `docs/investigation_api_usage.r4.md`。

## 規約檢查與語意界線

執行前 185 項測試通過；傳輸續跑的三項追加測試及三項 cached-token 成本計算測試通過。四筆 single-observation channel→asset gold 的既有 fact keys 可由新格式精確表達，原人工標註與 sealed snapshot bytes 完全未改。負向測試涵蓋錯誤 record/channel/asset/metadata/visibility/lineage、缺 metadata、錯 quality、多筆觀測及更強解讀。其他 claim definitions 保持不變。

16,384 safety ceiling 邊界測試：11,163 和 16,384 允許，16,385 拒絕；拒絕時不裁切、不額外檢索、不呼叫模型。N=64、EN=32+32、48,000-byte 上限及排序/序列化均維持原規約。

Strict Structured Outputs 的 API schema 使用封閉物件與 tagged anyOf；uniqueness 與 exclusive numeric bounds 仍由完整本機 schema 嚴格檢查，不能把 API 成功視為內容正確。原始 claim types 保留；reported_change/electrical_change 只在通過證據與原始內容檢查後採用既定 numeric projection。不增加 gold aliases，不調整分母。

有限檢查統計：`{json.dumps(r['finite_conformance_counts'],sort_keys=True)}`。

未通過或不可機械判定原因：`{json.dumps(r['not_supported_or_not_checkable_reasons'],sort_keys=True)}`。

B4 disposition 統計：`{json.dumps(b4['dispositions'],sort_keys=True)}`。

以上為 **conformance diagnostics**，不是研究 precision/recall 或 verifier accuracy。自由文字與 Q6 relevance 可能是 NOT_CHECKABLE，不等於已證明錯誤；只有具備由 R1 完成、與 verifier 自動判定分開的人工作業 ledger，才能計算相關評估指標；這不表示另有第二位獨立 reviewer。本輪沒有利用輸出分數修改提示詞、matching、verifier、retrieval、claim semantics 或 metrics。

## 實作缺陷、容量限制與模型內容分開記錄

- 基礎設施缺陷：起始並行與短退避未配合實際帳號 TPM，造成 86 項純限流失敗。修正為單一請求、起始間隔至少 60 秒；補跑獲另行授權，研究規則與請求保持相同。
- 中斷復原限制：兩次請求交付未知，已留下紀錄與既定額度消耗；不推測其內容或費用。
- 無 HTTP 回應且無 usage 的嘗試合計四筆：上述兩次操作中斷、一次 ConnectionResetError、一次 TimeoutError。TimeoutError 依原核准傳輸政策使用下一次嘗試，後續交付與原未知紀錄皆保留；這四筆皆無法由本機紀錄確定實際計費。
- 執行前發現的 strict-schema 編譯及測試匯入問題已於模型呼叫前修正並通過測試；傳輸復原的缺少 JSON 匯入也由合成測試在呼叫前修正。沒有依模型答案修正 verifier。
- 另有 ConnectionResetError 被既有 runner 記為 terminal implementation failure；原紀錄保留，本輪未修改傳輸例外處理或自行重跑。
- 輸出容量不足由 provider termination reason 證明，與研究分數及模型事實錯誤分開。
- 模型文字、引用或證據支持檢查失敗按原規則保留；不自動視為程式缺陷或改規則提升通過率。

## Custody 與待核准事項

Gold reviewer = R1；evaluation custodian = Author/R1。方法是 single-reviewer gold，不宣稱獨立第二 custodian、雙人標註、adjudication 或 IAA。應用程式開發 allowlist、拒絕事件的 access log、路徑與 hash binding 已實作；外部 gold 目錄與 OS/account ACL、custodian access logging 尚需實際 provision/驗證，不能把應用程式保護當成 OS 隔離。

Scenario strata 僅取自既有 frozen event/scenario selection mapping 的已綁定版本；沒有從模型表現挑選。Q5/Q6、numeric specialization B、原 matching/metric/statistical plan 未變。所有原候選及新增檔案的精確 inventory 另列，尚未封存協定。

正式 freeze 前仍須：

1. 接受本次基礎設施處理、完整 conformance 結果與模型／機械檢查限制。
2. 依實際截斷證據決定是否批准 8,192 與下一輪開發驗證；目前固定 4,096。
3. 完成並驗證外部 evaluation custody/ACL/access logging。
4. 作者明確批准最終檔案 inventory 與 Investigation Protocol v1 freeze；评估執行需要另行授權。

## 更新的 prompt/config/schema hashes

| 檔案 | SHA-256 |
|---|---|
{hashes}

完整逐筆紀錄：`results/investigation-dryrun-v1/final_conformance_report.json`。完整候選清單：`configs/investigation_protocol.v1.freeze_inventory.r4.json`。本報告不凍結協定，不啟動評估集。
'''
report_path=ROOT/'docs/investigation_protocol.v1.dryrun_report.r4.md';report_path.write_text(text)
candidate={'version':'investigation-protocol-v1-dryrun-candidate-r4','status':'DEVELOPMENT_DRYRUN_COMPLETE_AWAITING_AUTHOR_NOT_FROZEN','protocol_frozen':False,'evaluation_authorized':False,'model':model['exact_callable_model'],'max_output_tokens_executed':4096,'proposed_output_tokens_pending_approval':8192 if truncated else None,'evidence_token_safety_ceiling':16384,'active_development_entrypoint':'scripts/resume_investigation_dryrun_v2.py','historical_initial_entrypoint':'scripts/run_investigation_dryrun.py (initial concurrent transport superseded for this run)','pilot_gold_methodology':'single-reviewer gold','custodian':'Author/R1; not an independent custodian','preflight':binding(OUT/'preflight_manifest.json'),'prior_candidate':binding(ROOT/'configs/investigation_protocol.v1.development_candidate.json'),'report':binding(report_path),'machine_report':binding(OUT/'final_conformance_report.json'),'api_usage':binding(OUT/'api_usage_and_cost.json'),'prompt_manifest':binding(ROOT/'prompts/investigation-v1-r4/manifest.v1.json'),'remaining_decisions':r['remaining_freeze_decisions']}
create_json(ROOT/'configs/investigation_protocol.v1.dryrun_candidate.r4.json',candidate)
paths={x['path'] for x in load(ROOT/'configs/investigation_protocol.v1.freeze_inventory.r3.json')['existing_files_to_seal_on_future_protocol_freeze']}
for folder in ['src/investigation_dryrun','configs/investigation-dryrun-v1','prompts/investigation-v1-r4','results/investigation-dryrun-v1']:
 paths.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'schemas').glob('*.v3*.json'))
paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'scripts').glob('*investigation_dryrun*.py'))
paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_investigation_dryrun*.py'))
paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_investigation_transport_resume*.py'))
paths.update(['scripts/report_investigation_api_usage.py','tests/test_investigation_api_usage.py','docs/investigation_api_usage.r4.md','.gitignore','configs/investigation_protocol.v1.dryrun_candidate.r4.json','docs/investigation_protocol.v1.dryrun_amendment.r4.md',str(report_path.relative_to(ROOT))])
paths.discard('results/investigation-dryrun-v1/delivery_manifest.json')
assert 'api_key.txt' not in paths
inventory={'version':'investigation-protocol-v1-freeze-inventory-r4','status':'FOR_AUTHOR_REVIEW_NOT_FROZEN','protocol_frozen':False,'prior_inventory':binding(ROOT/'configs/investigation_protocol.v1.freeze_inventory.r3.json'),'candidate':binding(ROOT/'configs/investigation_protocol.v1.dryrun_candidate.r4.json'),'existing_files_to_seal_on_future_protocol_freeze':[binding(ROOT/p) for p in sorted(paths)]}
ip=ROOT/'configs/investigation_protocol.v1.freeze_inventory.r4.json';create_json(ip,inventory)
delivery={'version':'investigation-development-dryrun-r4-delivery','protocol_frozen':False,'inventory':binding(ip),'candidate':binding(ROOT/'configs/investigation_protocol.v1.dryrun_candidate.r4.json'),'report':binding(report_path),'conformance':binding(OUT/'final_conformance_report.json'),'immutable_file_count_if_approved':len(paths),'credentials_excluded':True}
p=OUT/'delivery_manifest.json';create_json(p,delivery);Path(str(p)+'.sha256').write_text(file_hash(p)+'  delivery_manifest.json\n')
print(json.dumps(delivery,indent=2))
