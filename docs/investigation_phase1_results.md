# Investigation Phase 1 — 完成回報

作者核准範圍內的第一里程碑已完成。原始 review 見 results/investigation-v1/approval/author_review.txt。
**未呼叫 LLM；未實作 B1–B4；事件 IDs 已凍結，但最終 investigation protocol 未凍結。**
所有自動整理與 annotation 都是 DRAFT_UNREVIEWED，人工 gold 仍為 0 件。
既有 classification／observability 的 frozen files 已再次查核未改動。

## 1. Command-target feasibility

完整報告：[command_target_feasibility.md](command_target_feasibility.md)。

48 事件中 28 件（58.33%）有 command-type activation request。49 個 request objects 的 exact CA.IOA
均能在 raw static map 找到，且都指向存在於 E metadata 的 opaque asset。98 個 command objects
（requests/responses 合計）與 canonical evidence IDs 核對一致，實際類型為 45/47/50。
types 46/48/49/51 未被實測，不能聲稱全面支援。

**49/49 是 raw static mapping 可用，不是現有 sanitized mapping 已可用。** 全部 request 地址屬 CONFIGURATION，
現有 MEASUREMENT-only sanitized lookup 為 0/49；因此需要 M/export amendment。44/49 requests
在當窗還有同 asset 的有效 E 回報（且有較晚回報），但不能因此推論 execution 或 causality。
其餘 5 個 requests 只能對上 static asset，不能補造同資產 E。

五份 mapping 無 duplicate JSON keys、所觀察 request 無 unmapped address；但有 122 個 source-scoped
element+attribute 的 configuration/measurement collision groups，必須保留 exact address/context，不能靠名稱合併。

## 2. Amendment 待核准

[精確欄位與 allowlist 提案](command_target_amendment.proposed.json)；
[child-record JSON Schema](command_address_observation.schema.proposed.json)。

新增旁掛的 address observation，parent 指向原 canonical m ID，輸出 opaque control-point/asset/M IDs；
CA/IOA 與原始 mapping key 留 private provenance，不輸出 setpoint、select/execute 或 initial value。
command_observed 只增加「地址對應資產 X 控制點」；asset_relationship 可查 mapping，temporal_association
可查同資產捕獲先後。全部仍不支持命令執行、物理成功、惡意意圖或因果。
目前 B0 target_asset_id 仍為 null；稽核 sidecar 沒有接入 export/retrieval/review packets。

## 3. 已凍結事件集

- configs/investigation_events.v1.json：16 Basic development、32 evaluation（Semiurban 18、Rural 14）。
- configs/investigation_events.v1.lock.json：IDs、原提案、作者授權與 pilot selection hashes。
- configs/investigation_pilots.v1.json：四個固定開發 pilot。
- configs/investigation_phase1.lock.json：B0 建構前的本里程碑 code/config/tests snapshot；不是正式 LLM protocol lock。

評估子集為 16 cyber/16 benign 的 balanced investigation benchmark，非實務 prevalence；Sherlock 資料
此前已被分析，不是新 unseen dataset。四個 pilot 滿足不同家族的 2 cyber+2 benign、numeric missing、
post state observation 條件，選取未用 LLM 輸出。label/family selection audit 與 reviewer packets 隔離。

## 4. Export／retrieval 設計與實際產物

src/retrieval/evidence_formatter.py 先驗 canonical schema，再 field-scoped export。E-only 不含 N headers，
N-only 不含 E values；三者共享同一准許靜態 M。原始路徑、來源 resolver、絕對 event 時間、G 均不公開。
私有 provenance 在 results/investigation-v1/private_provenance/；export object 無 canonical back-reference。

src/retrieval/investigation_retriever.py 固定 E64、N64、EN32+32，raw 與 derived entries 都計入。
E 依 family/channel round-robin，prioritize 可配對 observations；N 依 request/response/RST/frame/activity
round-robin，普通 packets 跨固定 time bins；gap 從完整 visible TCP/2404 universe 計算，非 top-k silence。
derived pair 和 gap 的直接 support records 原子化納入，超額不留下孤立 aggregate。
numeric pair 是 earliest valid pre + latest valid post；不足時可用同側 first/last，必須保留時間與 pair scope。
不按最大電氣變化、分類成績或標籤排名。

48×3=144 條件均取回 64 entries；最大 bundle 36,863 bytes，低於 48,000 cap（含必要 M）。
LLM tokenizer 預算仍需未來選模型後定案，bytes 不是 token 的替代。
每個 event/view 保存 eligible.json.gz、retrieved.json、receipt.json、timeline.json。

每份 receipt 分開保存 eligible count/hash、retrieved IDs/hash、omitted count、domain quota、query provenance；
final_recovered_investigation_facts=null。將來 gold 的三欄 supportable / retrieved / recovered 不能互相代替。
目前這是完整性工程查核，沒有用 B0 候選數宣稱調查 completeness。

## 5. 代表性 B0

可讀版本：../annotations/events/ev_0961f1c2da8a257e3ebc/review.md。
原始 JSON：../annotations/events/ev_0961f1c2da8a257e3ebc/B0_EN.json。

此事件完整 universe 5,349 筆；EN 取回 64 entries，列出 54 個 observation rows、10 個 numerical differences。
例如 `m_81c335db83989561408ba943` 在相對 t0 的 +0.022887 秒觀察到 ASDU45/COT6 request；
target 與 execution 均 unknown。通道 `ch_076a19f4adcfcfee` 的两筆回報電壓由
0.9995936751 pu（−58.154169 秒）到 1.0001730919 pu（+51.899538 秒），差 0.0005794168 pu。
其 before/after IDs 與 derivation ID 都在 JSON 可追溯；上述兩類觀測沒有被連成因果敘事。

B0 由 src/investigation/timeline.py 產生網路／process observations、channel→asset mapping、
捕獲時間排序、直接數值差與明確 unknown；security_interpretation 為空。

## 6. 四份 blinded pilot packets

| Event ID | p / m / E records | 完整 records | 缺有效 post 的 numeric channels | Post state observations |
|---|---|---:|---:|---:|
| ev_0961f1c2da8a257e3ebc | 1576 / 782 / 2991 | 5349 | 0 | 3 |
| ev_21f18503563e6a677ae5 | 1606 / 791 / 2973 | 5370 | 0 | 0 |
| ev_812f8057d7c974d9cf36 | 1649 / 784 / 2900 | 5333 | 13 | 0 |
| ev_ab03f537915a04bff66c | 1794 / 891 / 2988 | 5673 | 0 | 0 |

每包位於 annotations/events/<event_id>/，含完整 allowed evidence、完整 allowed lineage、全 universe
數值候選、三視圖 retrieved/B0、13-type audit、annotation 草稿與可讀 review.md。沒有 label、family、
attack point、gold narrative、playbook、physical truth 或 command-target audit sidecar。
annotations/guidelines.md 說明如何 review；annotations/gold/ 沒有 gold data。

## 7. Claim-type supportability

完整 13-type 計數、probe 分母與限制：[investigation_claim_supportability_phase1.md](investigation_claim_supportability_phase1.md)。

- reported_state_change：四件均 0 候選；一件有 state 值但沒有可定義的 transition，待作者決定是否僅保留為不足／邊界測試。
- asset_relationship：已具 E channel→asset 支援；command→asset 要先核准 amendment。
- temporal_association：可做 capture sequence 與 episode-level request/later-E，不能自行改成同 target 或 causality。
- reported_change/electrical_change：同一批 996 channel-pair 候選，不可重複加分。含 13 pre-only pairs，不能假冒事件後變化。
- security_indicator/security_interpretation：B0 不自動確立安全意義；primitive observations 可供人審。需 reviewer
  判斷有限 review_required 結論是否足夠有用，不能把「拒絕一切」包裝為高品質 investigation。

這是自動可行性盤點，不是四件已完成的人工 annotation。human_confirmed counts 與 signoff 都是 null。

## 8. LLM 前尚待定案

1. 作者是否核准 command-address sidecar、CONFIGURATION 的窄 M allowlist、asset/temporal claim amendment。
2. 人工審四個 packets，決定 state_change 與 security 類型的主實驗定位；保留或降為不足／邊界測試均需明示。
3. reviewer 人選、雙人審查與 adjudication，完成 human-reviewed gold；未完成前不作正式分數。
4. 根據 pilot 核准最終 claim schema、retrieval 細則、support/sufficiency policy；模型、snapshot、sampling、token 上限與成本另定。
5. 之後才凍結正式 protocol 並取得 LLM 使用授權。本輪不跨到 B1–B4。

## 查核與執行方式

67 項測試通過（原 48 + 新 19）。scripts/verify_investigation_phase1.py 查核了 144 bundles、
2,400,790 個跨 views 的 exported record instances（不是獨立事件）、完整 private lineage、引用、
pair 數值、full-universe gap、預算、無 G 欄位、四份完整 review packets，以及舊 frozen hashes。
結果見 results/investigation-v1/verification.json；全部通過。

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_investigation_phase1.py
.venv/bin/python scripts/inspect_investigation_packet.py annotations/events/ev_0961f1c2da8a257e3ebc --limit 5
```

baseline runner 與 raw audit 拒絕覆寫已完成產物。docs/ 繼續被 gitignore；本輪新程式與產物尚未 commit/push。
依作者 review 第 9 節，本里程碑完成後停止；沒有任何 LLM API call。
