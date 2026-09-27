# Phase 2A 人工標註指南（提案）

本階段只準備四個 development pilot 的人工標註。所有初始人工判斷為空；
`DRAFT_UNREVIEWED` 候選不是 gold。既有 `annotations/events-v2/` 與所有 v2
證據、schema、retrieval、B0 都保持原樣。此指南仍待作者定稿。

## 開始審查

每個 `annotations/phase2a/pilots/<event_id>/` 有四個檔案：

- `reviewer_annotation.BLANK.json`：空白工作表。
- `observation_candidates.DRAFT.json`：取自完整允許 universe 的機械候選。
- `deduplication_proposals.DRAFT.json`：只建議可能同義的鍵群組，沒有合併任何事實。
- `guardrail_opportunities.DRAFT.json`：禁止的較強推論及留白的人審欄位。

請將每個 BLANK 檔複製為同目錄 `reviewer_annotation.json` 後填寫，保留原始空白檔。
不要把 candidate 檔改名成 gold。先查看完整證據、選出有意義的原子事實，
再查看 production retrieval / B0，以減少只沿用系統輸出的偏差。
`source_packet`、hash、event ID 與 partition 是來源資訊，並非預填的人工判斷。

## 完整證據與 64-entry retrieval

完整證據仍在 `annotations/events-v2/<event_id>/complete_allowed_evidence.json.gz`；
父子關係在 `allowed_lineage.json.gz`。工作表引用這些不可變來源並記錄 hash。
以下工具預設查完整 universe，分頁只是顯示限制，不是 production top-k：

```sh
.venv/bin/python scripts/inspect_pilot_evidence_phase2a.py ev_0961f1c2da8a257e3ebc --source-type command_address_observation --all
.venv/bin/python scripts/inspect_pilot_evidence_phase2a.py ev_0961f1c2da8a257e3ebc --channel ch_139683601a10167d --all
.venv/bin/python scripts/inspect_pilot_evidence_phase2a.py ev_0961f1c2da8a257e3ebc --evidence-id meta_70711efe18cc741b8c651f4b
.venv/bin/python scripts/inspect_pilot_evidence_phase2a.py ev_0961f1c2da8a257e3ebc --view N --production --all
```

工具可依 `--asset`、`--channel`、`--source-type`、時間、ID 查詢；以 `--offset` / `--limit`
分頁，或 `--all` 顯示全部匹配筆數。metadata 與已批准的 derived query 可用 ID 查詢。
只接受四個核准 pilot；不讀取 32 個 evaluation 事件或其未來 gold。

## 一筆人工事實怎麼填

複製 `blank_fact_template` 到 `facts` 陣列，保留空白模板本身。每列只填一個可判定
的原子命題，避免把「request 被捕獲」「某資產執行」「造成變化」包成一句。

| 欄位 | 填寫規則 |
|---|---|
| gold_claim_id | event 內唯一，例 `g_0001`；只在人工選定事實後填入 |
| question_ids | 關聯 Q1–Q7，可多題，但不是多個獨立事實 |
| claim_type | 使用現有 13 類 ontology；reported_change/electrical_change 須去重 |
| epistemic_category | observation / derived_observation / static_relationship / temporal_association / weak_review_interpretation / guardrail_insufficiency |
| atomic_statement | 人工撰寫的單一命題，明確說明時間、映射及可知範圍 |
| fact_key | 接受機械提案鍵或以人審理由覆寫；不是語意正確性的證明 |
| proposed_fact_key / key_kind / key_identity | 若使用機械候選，複製三個對應欄位；純語意命題可留 null 並填 key_override_reason |
| minimal_support_sets | 按 E/N/EN 填寫替代最小支援集合：外層是 OR，每個內層 ID 列表是 AND |
| E/N/EN_answerability | supported / partially_supported / insufficient；不得依 top-k 缺少而判完整 universe 不可回答 |
| acceptable_action | 各 view 人工選 assert / qualify / withhold；不足命題不得 assert |
| prohibited_stronger_interpretation | 此事實不能被升級成哪些更強說法 |
| ambiguity_notes | 語意、別名、時序、映射、部分支持或替代支援的疑義 |
| reviewer_id / review_status | 人工 reviewer ID；UNREVIEWED / IN_REVIEW / HUMAN_REVIEWED |
| checkability | mechanically_checkable / human_semantic_judgment / both；指所需檢查，不表示已驗證 |
| alias_of / alias_decision / alias_rationale | distinct / merge_alias / ambiguous；只有人審明確指定的 merge_alias 才合併 |

`partially_supported` 應清楚寫出可保留的較弱命題與缺失前提；不要把不完整的引用
冒稱為原命題的完整 support set。必要時將較弱命題另立一筆原子事實。
Guardrail opportunity 的 atomic_statement 記錄待禁止／應保留不足的命題，category
使用 guardrail_insufficiency，actions 為 qualify 或 withhold，不算 positive fact。

`view_accounting` 的三層必須保留：

- `eligible_in_view`：完整允許 view 是否包含該原子命題的完整支持。
- `retrieved_in_production_bundle`：production bundle 是否帶回至少一組完整支持。
- `recovered_by_system`：本階段固定 null；未進行 system-vs-gold 評估。

未知請留 null。統計工具另報 support-ID 集合可得性，不能代替語意判斷，也不把
「取回完整支持」當成「系統正確回答」。對無正支持集合的 guardrail 可留 []；
其支持不足的 scope/absence 診斷另寫 ambiguity_notes，不能以空集視為自動成功。

## 支援與推論邊界

Mapped request 需 m+a+static control M。跨 N/E 同資產時間關聯另需有效 E 及 channel M，
兩邊 opaque asset 相同。時間是 capture time，不是真正量測／動作時間；共享封包祖先
不能當成獨立感測器的相互驗證。COT7 或 TCP ACK 都不是物理執行成功證據。

reported_state_change 為選配，不影響 event coverage 或最低問題充分性。只有兩筆有效、
同 channel、嚴格有先後且 boolean 值不同才可建立；單筆 state 是 reported_value。
禁止使用 initial/configuration 值補出 before。候選生成器不創造缺失的 state pairs。

Commands、RST、captured gaps、numeric differences 可供人審。它們是否值得採取弱的
review_required 解釋，由 reviewer 決定；不自動形成 security_interpretation gold。
Execution、physical causation、malicious intent、identity、compromise、benign/safe-from-absence
在目前政策下無法建立，主要記為 guardrail / insufficiency opportunities。

## 去重、完成與統計

機械同鍵只是提示。不同強度的 command、不同 numerical quantity、不同時間方向／scope
不自動合併。`reported_change` / `electrical_change` 的同一 pair、同一 quantity 只計一筆。
合併時讓 alias 指向同 event 的 canonical gold_claim_id，採相同定案 fact_key 和 view
judgments，並記理由；不得循環。人工可覆寫或保留 ambiguous，但須先解決才標 HUMAN_REVIEWED。

每個 Q1–Q7 的 `question_review` 必須獨立人審，不能由事實數目自動推定可回答。
全部完成後 signoff 格式為 `{ "reviewer_id": "...", "reviewed_at": "...", "notes": "..." }`。
雙 reviewer、分歧裁決及最終 gold 發布人選仍待作者核准。

```sh
.venv/bin/python scripts/summarize_human_annotations.py --filename reviewer_annotation.json
```

加 `--output results/investigation-phase2a/<new-name>.json` 可另存；不覆寫既有結果。
未填寫時可對 BLANK 檔執行 smoke check，輸出 ANNOTATION_PENDING；零值不表示 ontology
不可用。摘要只統計人工標註，不計 precision、recall、accuracy、completeness 等研究效能。
