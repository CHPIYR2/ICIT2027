# Investigation Phase 1 — command-target amendment v2 results

本次作者核准範圍已完成：schema/policy、address adapter、static mapping、retrieval/receipts、B0、四份人工審查包。已停在 Phase 1；未實作 B1–B4，LLM calls = 0，human gold = 0。

## 1. 版本與邊界

`investigation-export-v2`、`investigation-command-address-v2`、`investigation-retrieval-v2`、`investigation-claim-v2`、`investigation-verification-v2`、`investigation-b0-v2`。
設定：configs/investigation.phase1.v2.json；實作快照：configs/investigation_phase1.v2.lock.json。此為本次實作快照，並非 Investigation Protocol v1 最終凍結。
B0 保留原有決定性觀測索引，新增 amendment_claims 採 typed claim v2 並逐條有限一致性檢查；verification schema 已修正，但完整 B3/任意自然語言 verifier 尚未實作。
只解析已審核的 45/47/50；46/48/49/51 沒有 evaluated support。Raw CA/IOA 只在 private_provenance；控制值、初始值、select/execute、G/labels 不進 public address evidence。
舊分類鎖、Phase1 v1 鎖均通過；144 份新版的 canonical E/N 投影逐份等於舊版，分類 contracts/features/models/results 未修改。

## 2. 驗證

94 / 94 tests PASS，包含 27 項新增 amendment 測試。144 條件的 output hashes、retrieval/B0 replay、原始 E/N 投影、映射雙邊、時間差、derived arithmetic、gap 與四包 lineage 均通過。
完整機械驗證：results/investigation-v2/verification.json。測試指令：`.venv/bin/python -m unittest discover -s tests -q`。

## 3–4. 精確數量

| 完整 48 事件 EN universe | 數量 |
|---|---:|
| command-address children | 98 |
| exact_static_match | 98 |
| 有同資產有效 E | 88 / 98 |
| 有較晚同資產有效 E | 88 / 98 |
| activation request children（COT=6） | 49 |
| request 有較晚同資產有效 E | 44 / 49 |
| EN B0 實際呈現同資產 temporal candidates | 44 |

98 = 49 request + 49 activation-confirmation 地址子證據。類型 45:76、47:4、50:18。88 包含 request 與 response；44 是 request 的同資產時間關聯候選。其餘 5 個 request 雖 mapped 但缺同資產有效 E。
以上為 evidence/candidate counts，不是 98 個事件，也不是 gold recall、模型準確率或 fusion superiority。

## 5. 有支援的 B0 範例

Event `ev_0961f1c2da8a257e3ebc`，EN，claim `c_3`。

- request `m_81c335db83989561408ba943`：ASDU 45、COT 6、capture t=0.022887230s。
- address `a_201ac60a2dfa3237d1cef218` → `cp_6c4f3c31996c2844` → `asset_5c5dca51985d37c3`，static M `meta_70711efe18cc741b8c651f4b`。
- E `e_8606b7842af56e3d54832106` → channel `ch_139683601a10167d` → 同一 asset，static M `meta_4d4540079d9a2a1c6b19fd04`；capture t=0.272304296s，reported value=True。
- capture Δt=0.249417067s，兩條靜態映射一致。

**這是 asset-linked temporal evidence。不是 execution proof、causal proof 或 malicious-intent proof。** 本例所引用的 boolean 僅支援 reported_value，並非 state change。
完整可核對範例：results/investigation-v2/supported_example.DRAFT.json。

## 6. 不足範例

Event `ev_363ad64e92cfa74fd5f6`：asset `asset_6cfe2ffd19aa6fd8` 的 command mapping 成功，但完整窗口同資產有效 E = 0；B0 明列 `no_valid_later_same_asset_E_in_allowed_window`。這不是 top-k 遺漏，也不代表命令失敗或安全。
完整範例：results/investigation-v2/insufficient_example.DRAFT.json。

## 7. 四份核准 pilot 包

| Event | p / m / E / a 完整筆數 | request / 同資產較晚 E | EN B0 links |
|---|---|---|---:|
| ev_0961f1c2da8a257e3ebc | 1576 / 782 / 2991 / 8 | 4 / 4 | 4 |
| ev_21f18503563e6a677ae5 | 1606 / 791 / 2973 / 0 | 0 / 0 | 0 |
| ev_812f8057d7c974d9cf36 | 1649 / 784 / 2900 / 0 | 0 / 0 | 0 |
| ev_ab03f537915a04bff66c | 1794 / 891 / 2988 / 2 | 1 / 1 | 1 |

Packets：annotations/events-v2/<event_id>/。每包都有完整允許 evidence、lineage、numeric candidates、E/N/EN retrieval+receipt+B0、13 類 supportability inventory 與空白人工 annotation/signoff。
四包全部 DRAFT_UNREVIEWED；兩個無 request pilot 保留 no_command_request_in_allowed_window。reported_state_change 在四包皆 0。

## 8–9. 修訂 ontology inventory 與目前不可用類型

下表是完整 universe 的機械候選／探測數；不是人工 gold、metric 分母或互斥事實總數。

| Claim type | 48 事件候選 | 四 pilot 候選 | 解讀 |
|---|---:|---:|---|
| network_activity | 569646 | 9873 | 需人工挑選、去重與確認 support sets |
| command_observed | 49 | 5 | 需人工挑選、去重與確認 support sets |
| acknowledgement_observed | 426617 | 8051 | TCP ACK / S-frame / COT7 候選混合，需分語意 |
| communication_gap | 48 | 4 | 完整 captured TCP2404 query，不證明 outage |
| reported_value | 630749 | 11852 | 需人工挑選、去重與確認 support sets |
| reported_change | 52736 | 996 | 與 electrical_change 共用 pair，禁止雙算 gold |
| reported_state_change | 0 | 0 | 0；留作 optional，不列最低充分性 |
| electrical_change | 52736 | 996 | reported_change alias，待人工定義合併 |
| temporal_association | 44 | 5 | 44 個 request address 有較晚同資產 E；非因果 |
| asset_relationship | 52827 | 1004 | E channel mapping + 49 command-address mapping；需人工選 meaningful facts |
| security_indicator | 0 | 0 | 0 個已建立語意的正候選；不是缺少原始 primitive |
| security_interpretation | 0 | 0 | 0；強安全結論均未建立 |
| unknown | 336 | 28 | 每事件固定 7 個 guardrail subjects，非獨立事件 |

目前 `reported_state_change` 沒有可觀察的合格正例；`security_interpretation` 沒有可支持的 execution/causal/intent/success/attribution 正例。`security_indicator` 的安全相關性尚待人工定義與審查，不把 primitive 自動升級為 attack evidence。
完整逐事件 inventory：results/investigation-v2/supportability_inventory.DRAFT.json；四包另有局部 inventory。

## 10. 最終凍結前仍待決定

1. 人工審查四包：meaningful atomic facts、aliases/duplicates、alternative minimal support sets、unknowns/較強不支持敘述與 verifier 可行性；指定 reviewer 與 adjudication 流程。
2. 根據 pilot 定稿 ontology：reported_change/electrical_change 去重；security_indicator 可操作定義；reported_state_change 保留 optional（已核准，不重問）。
3. 定稿 Q1–Q7 answerability 與最低支持組，尤其 Q5 episode-only 與 same-asset 的計分分界、Q6 不把 primitive 當惡意證據；固定 metric 分母與 NA 規則。
4. 本次 EN 新增依已觀察 command asset 優先檢索較晚 E，屬於 v2 系統改動；確認正式比較共用此版本，且每 view 預算上限 64 entries（EN 32+32）、48k bytes；待模型選定再補實際 token cap。
5. 後續階段另行核准並固定模型/provider/snapshot、sampling/seed、輸入與輸出 token cap、prompt、重試與成本；目前未做 B1–B4，也未送任何 LLM API。
6. 人工 gold、policy、retrieval、schema、prompts、metrics 與 model/code hashes 齊備後，才可稱 Investigation Protocol v1 正式凍結。事件 IDs 維持已核准的 16 development + 32 evaluation，這些資料已被檢視，不能稱 untouched test。

這次修改使可證實的跨域上限到達「同資產 capture-time 時間關聯」，尚未提供融合勝過網路單模態的效能證據。
