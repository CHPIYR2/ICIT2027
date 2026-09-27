# Claim-type supportability — Phase 1 DRAFT_UNREVIEWED

本表是對四個完整允許 universe 的自動 feasibility inventory，不是人工 gold、LLM 表現或 accuracy。
各欄以完整 event ID 對應；相同事實的 aliases 與 shared lineage 尚需人工去重。
`候選 / 不足 probes` 的單位各異，不能相除成比率；人審確認數目前全部為 null。

| Claim type | Pilot 1 | Pilot 2 | Pilot 3 | Pilot 4 |
|---|---:|---:|---:|---:|
| network_activity | 2358 / 0 | 2397 / 0 | 2433 / 0 | 2685 / 0 |
| command_observed | 4 / 0 | 0 / 1 | 0 / 1 | 1 / 0 |
| acknowledgement_observed | 1953 / 0 | 1978 / 0 | 1952 / 0 | 2168 / 0 |
| communication_gap | 1 / 0 | 1 / 0 | 1 / 0 | 1 / 0 |
| reported_value | 2991 / 62 | 2973 / 65 | 2900 / 65 | 2988 / 65 |
| reported_change | 249 / 0 | 249 / 0 | 249 / 0 | 249 / 0 |
| reported_state_change | 0 / 65 | 0 / 65 | 0 / 65 | 0 / 65 |
| electrical_change | 249 / 0 | 249 / 0 | 249 / 0 | 249 / 0 |
| temporal_association | 4 / 4 | 0 / 0 | 0 / 0 | 1 / 1 |
| asset_relationship | 252 / 4 | 249 / 0 | 249 / 0 | 249 / 1 |
| security_indicator | 0 / 1 | 0 / 1 | 0 / 1 | 0 / 1 |
| security_interpretation | 0 / 4 | 0 / 4 | 0 / 4 | 0 / 4 |
| unknown | 7 / 0 | 7 / 0 | 7 / 0 | 7 / 0 |

- Pilot 1: `ev_0961f1c2da8a257e3ebc`
- Pilot 2: `ev_21f18503563e6a677ae5`
- Pilot 3: `ev_812f8057d7c974d9cf36`
- Pilot 4: `ev_ab03f537915a04bff66c`

## 必須在正式 protocol 前由作者／reviewer 處理

- reported_state_change：四個 pilot 都是 0。有一件有 3 筆 post state observations，但沒有同 channel 的有效 unequal ordered pair；不可因此宣稱 unchanged。
- asset_relationship：已能檢查 E observation→channel→asset；尚未核准 command address→asset amendment，command targets 一律 unknown。
- temporal_association：本表只數 request 之後有 E 的 episode-level opportunities。0 不代表沒有其他 timestamp ordering；B0 仍能列 capture timeline。同 asset 關聯需 amendment，因果仍不允許。
- security_indicator / security_interpretation：自動候選 0 是「未由 B0 核准安全語意」，不是資料完全沒有安全相關觀測。command、RST、numeric pair 的機械 primitive counts 另在各 packet 中；其安全價值須人審。不要把 0 解讀為這些類型已被實證證偽。
- reported_change / electrical_change：同一組候選 pair，有 996 組 channel pairs，不能當成 1,992 個 gold facts。
- Pilot 3 有 13 個 numeric channel 無有效 post。其 249 組 within-window candidates 中 236 是 pre/post、13 是 pre-only；後者不能用來聲稱事件後變化。
- unknown：每件 7 個固定未支持結論主題；不是 7 個獨立事件，也不是自動完成了人工 unknown 標註。

## 不足 probes 的意義

它們是固定的 availability／overclaim 檢查機會，不是觀察到 LLM 犯錯：無 command 的 request 問題、
缺少 valid E channel 的 value 問題、無 state pair、command target 尚不可映射、command→E causal overclaim、
以及 execution/causation/intent/benign-from-absence 四個 security guardrails。0 表示沒有計數該 probe，
不代表該 claim type 的所有可能句子都有支持。精確 probe_definition、ambiguities 與 mechanical_checkability
逐 type 保存在每個 claim_supportability.DRAFT.json。

下一步是 reviewer 依 annotations/guidelines.md 填 annotation.DRAFT.json，逐 type 確認有意義的例子、
不足、歧義、alias 與 verifier 可操作性；沒有人工 signoff 不能把上述計數當 gold。
