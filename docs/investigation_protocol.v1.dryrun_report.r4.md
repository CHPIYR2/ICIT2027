# Investigation Protocol v1 — Development Dry Run Freeze-Readiness Report

**NOT FROZEN. DEVELOPMENT ONLY. 未執行 32 個評估事件，未讀取評估 gold 或評估結果。**

## 執行與保留紀錄

原排程 144 個 B1/B2/B3 事件×方法×輪次項目全部保留。初次並行排程遇到帳號 30,000 TPM 限制，其中 86 項用完三次傳輸嘗試。作者另行批准這 86 項以相同請求補跑，原紀錄未刪除。總計保留 230 個交付項目；正式開發矩陣仍是 144 個位置，每個事件、方法的三輪皆保留。

補跑來源選擇僅限事先列明、沒有交付答案的純 429 失敗，沒有品質排序、best-of、提示詞修改或規則調整。兩次中斷嘗試沒有可恢復回應，記錄為交付未知並占原本三次上限，沒有捏造 provider status、用量或零費用。

| 方法 | 完成且 schema 通過 | 完成但 schema 不通過 | provider incomplete | 其他失敗 |
|---|---:|---:|---:|---:|
| B1 | 33 | 0 | 15 | 0 |
| B2 | 29 | 0 | 19 | 0 |
| B3 | 26 | 0 | 21 | 1 |

有效矩陣的 B4 有 48 筆重播紀錄，狀態為 `{"REPLAYED": 26, "REPLAY_UNAVAILABLE": 22}`。其中 47 筆有 B3 原始輸出，全部通過 exact-byte hash 檢核；其餘沒有 B3 輸出，不能聲稱完成重播或輸入 identity 檢核。B4 模型呼叫數為 0。沒有完整 B3 時明確記錄 replay unavailable，不補寫 JSON、不重新生成。原排程的 B4 及另批 B3 的 B4 也都保留。

B0 沿用每事件一份既有 deterministic EN timeline，共 16 份，三輪僅引用同一份；不宣稱 48 次獨立 B0 執行。

## 模型、完成狀態與 token

Requested model: `gpt-4.1-2025-04-14`；實際回傳模型統計：`{"gpt-4.1-2025-04-14": 143}`。API completion status、response ID、HTTP status、request ID、usage、termination reason、request/output hashes 詳見逐次 manifest 與 `final_conformance_report.json`。Temperature 0 不保證位元級重現，Responses seed 不支援。

以下分布涵蓋原排程及補跑全部有 provider usage 的嘗試，不把兩個交付未知嘗試當成零用量；429 無 usage 亦保持缺值。

| token 欄位 | 最小 | 中位數 | p95 | 最大 | 已知總量 |
|---|---:|---:|---:|---:|---:|
| input_tokens | 18409 | 20851 | 21288.6 | 21336 | 2885559 |
| output_tokens | 1920 | 3859 | 4096.0 | 4096 | 521815 |
| total_tokens | 20345 | 24212 | 25374.7 | 25432 | 3407374 |

有 usage 的嘗試：143；無 usage 的嘗試：270。HTTP 統計：`{"200": 143, "429": 266, "None": 4}`。原有限次重試原因：`{"OPERATOR_TRANSPORT_INTERRUPTION_NO_RECOVERABLE_DELIVERY": 2, "TimeoutError": 1, "retryable_HTTP_transport_status": 180}`；另批 86 項授權補跑單独列帳，不隱藏成原輪成功。

有效 144 項每項均記錄 actual evidence tokens，分布：`{"maximum": 11162, "median": 10693.5, "minimum": 8239, "n": 144, "p90": 11048.0, "p95": 11115.0}`。這與 API input tokens（包括 prompt、strict schema 與 provider framing）不同。

4,096 上限的有效矩陣截斷數：**55**。每筆截斷須有 `status=incomplete` 且 `incomplete_details.reason=max_output_tokens`，完整證據清單含 response IDs、usage、raw response hashes，位於 JSON 報告。

基於這些實際截斷證據，提出 8,192 作為下一個開發候選上限，等待作者批准；本輪沒有自動提高，也沒有因答案品質或分數增加上限。是否再做完整開發验证及其範圍亦需作者決定。

## API usage 與可計算成本

全部有 usage 的原排程及補跑回應，input tokens = 2,885,559；其中 cached input tokens = 1,860,096；output tokens = 521,815。Cached input 已包含於 input，不重複相加。

依 [OpenAI 官方 API 單價](https://developers.openai.com/api/docs/pricing)，可計算的已知用量小計為 **USD 7.155494**。這不是帳單總額；270 筆嘗試未回傳 usage，不能將交付未知的費用假設為 0。各次 provider meter、cache 分項、原排程／補跑拆分與計算式另見 `results/investigation-dryrun-v1/api_usage_and_cost.json` 及 `docs/investigation_api_usage.r4.md`。

## 規約檢查與語意界線

執行前 185 項測試通過；傳輸續跑的三項追加測試及三項 cached-token 成本計算測試通過。四筆 single-observation channel→asset gold 的既有 fact keys 可由新格式精確表達，原人工標註與 sealed snapshot bytes 完全未改。負向測試涵蓋錯誤 record/channel/asset/metadata/visibility/lineage、缺 metadata、錯 quality、多筆觀測及更強解讀。其他 claim definitions 保持不變。

16,384 safety ceiling 邊界測試：11,163 和 16,384 允許，16,385 拒絕；拒絕時不裁切、不額外檢索、不呼叫模型。N=64、EN=32+32、48,000-byte 上限及排序/序列化均維持原規約。

Strict Structured Outputs 的 API schema 使用封閉物件與 tagged anyOf；uniqueness 與 exclusive numeric bounds 仍由完整本機 schema 嚴格檢查，不能把 API 成功視為內容正確。原始 claim types 保留；reported_change/electrical_change 只在通過證據與原始內容檢查後採用既定 numeric projection。不增加 gold aliases，不調整分母。

有限檢查統計：`{"canonical_numeric_projection_pass": 81, "channel_asset_mapping_pass": 2, "emitted_claims": 931, "finite_wording_and_support_pass": 404, "invisible_citation_edges": 0, "not_supported_or_not_checkable": 527, "parseable_citation_arrays": 931, "typed_support_pass": 487, "unique_citation_edges": 1601}`。

未通過或不可機械判定原因：`{"Q6_relevance_requires_human_review_not_deterministically_checkable": 35, "ack_subtype_mismatch": 1, "assertion_status_conflict": 1, "asset_ids_mismatch": 31, "channel_ids_mismatch": 1, "command_mismatch": 27, "duration_mismatch": 2, "endpoint_ids_mismatch": 108, "episode_scope_has_asset": 5, "irrelevant_citation": 3, "mapping_roles": 13, "noncanonical_text_requires_hash_bound_human_review": 83, "same_asset_needs_N_E": 53, "unknown_scope_mismatch": 8, "unknown_subject_not_checkable": 156}`。

B4 disposition 統計：`{"INSUFFICIENT": 106, "QUALIFIED": 13, "SUPPORTED": 136}`。

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
| prompts/investigation-v1-r4/B1.v1.txt | `957fc4ee8aa333d8a154e14ec91b928951bbbd5d3406c1c4ec723cbf500ed843` |
| prompts/investigation-v1-r4/B2.v1.txt | `5370dbd0bff2e4274e21559570bdaf1ba0d76a7c30eb2773b75af7c8bbcfe0a6` |
| prompts/investigation-v1-r4/B3.v1.txt | `c87f42a0213a3e8acdd3c3797efdbf8674782626bf95e7b016a9dd34371ff704` |
| schemas/investigation_claim.v3.json | `33c2e19af5d5515ca43557a31748159e695aa3035514f1eb4487bbb377b16ac0` |
| schemas/investigation_verification.v3.json | `28a74ed388dd01b8456ea7c47b0fd854d0fac1f8179a0a19520482de2d69659b` |
| schemas/investigation_response.v3.required.json | `c526bc28bdf40e195dfee55c35996b840d5654e9519021240c4cde848e55c809` |
| schemas/investigation_response.v3.optional_baseline.json | `8d154bfd4cd2d85e53464ea4c57d369e0452827ac7956ace2511328cc53979bc` |
| configs/investigation-dryrun-v1/model.candidate.json | `fb70c15f4cc35cf775849369b3b1109667763b1db2fe3c10e4f48dd02674dd45` |
| configs/investigation-dryrun-v1/token_budget.candidate.json | `147e976a6982441e0ed0649a79d65545661e7063dbd184e9abc7a0837459d656` |

完整逐筆紀錄：`results/investigation-dryrun-v1/final_conformance_report.json`。完整候選清單：`configs/investigation_protocol.v1.freeze_inventory.r4.json`。本報告不凍結協定，不啟動評估集。
