# Pilot evidence review — DRAFT_UNREVIEWED

Event: `ev_ab03f537915a04bff66c`。本文件是自動整理的審查入口，不是 gold。

## 完整證據與 retrieval accounting

完整允許的 record counts：{'packet': 1794, 'message': 891, 'process': 2988}。共 5673 筆。
mapped numeric channels 中 0 個沒有有效 post observation；post state observations 0 筆。
完整來源數值候選 pair 範圍：{'pre_post': 249}；pre-only pair 不能描述為事件後變化。

| View | Eligible 原始 records | Retrieved entries | B0 觀測列 | B0 differences | Gold recovered |
|---|---:|---:|---:|---:|---|
| E | 2988 | 64 | 43 | 21 | 未評分 |
| N | 2685 | 64 | 64 | 0 | 未評分 |
| EN | 5673 | 64 | 54 | 10 | 未評分 |

## 代表性 B0 網路觀測（capture seconds relative to anchor）

| Time | Claim type | Evidence ID | 可說的內容 |
|---:|---|---|---|
| 0.03025818 | command_observed | `m_dd5ac24ec9c1aba6348f03a6` | 命令型 activation request；target 與 execution 仍 unknown |
| 0.06835318 | acknowledgement_observed | `m_1475b9261696f16631493e45` | protocol response；不代表 physical success |

## B0 數值差（僅兩筆 reported values）

| Family | Channel | Before time/value | After time/value | Δ | Unit |
|---|---|---|---|---:|---|
| current | `ch_029bdc536f7c7bbf` | -52.74187 / 2.78623 | 57.38534 / 2.890198 | 0.1039674 | AMPERE |
| current | `ch_01b02fa396b8aacb` | -52.63101 / 51.34472 | 57.54399 / 37.57325 | -13.77147 | AMPERE |
| voltage | `ch_0088cf6b660ba035` | -52.35931 / 1.029596 | 57.72151 / 1.0295 | -9.62019e-05 | PER_UNIT |
| reactive_power | `ch_0566adc5de7ac414` | -52.04976 / -155054.3 | 58.01279 / -155141.9 | -87.51562 | VAR |
| voltage | `ch_06d83383e88df298` | -51.50402 / 0.9953985 | 58.69144 / 0.9882454 | -0.007153094 | PER_UNIT |
| reactive_power | `ch_039148b1df69bc26` | -51.50402 / 355586.2 | 58.69144 / 355568.3 | -17.9375 | VAR |
| active_power | `ch_03ff62f697130abf` | -51.34165 / 78309.73 | 58.76256 / 78855.32 | 545.5938 | WATT |
| voltage | `ch_017a03c3172db71e` | -50.63801 / 0.9995857 | 59.42324 / 0.9968159 | -0.002769828 | PER_UNIT |
| current | `ch_1462c7778709192e` | -50.40701 / 42.76384 | 59.69812 / 19.57058 | -23.19326 | AMPERE |
| active_power | `ch_01a7a565075be594` | -50.24852 / 113447.3 | 59.84973 / 114241.2 | 793.9141 | WATT |

完整精度與 before/after evidence IDs 在 B0_EN.json；不以截取表格取代原始引用。
所有數字是 captured reported measurements；沒有物理因果或惡意意圖結論。

## 全部原始來源的 claim-type 可行性草稿

| Type | 可支持候選／機會 | 不足 probes | 人工確認 |
|---|---:|---:|---|
| network_activity | 2685 | 0 | 尚未 |
| command_observed | 1 | 0 | 尚未 |
| acknowledgement_observed | 2168 | 0 | 尚未 |
| communication_gap | 1 | 0 | 尚未 |
| reported_value | 2988 | 65 | 尚未 |
| reported_change | 249 | 0 | 尚未 |
| reported_state_change | 0 | 65 | 尚未 |
| electrical_change | 249 | 0 | 尚未 |
| temporal_association | 1 | 1 | 尚未 |
| asset_relationship | 249 | 1 | 尚未 |
| security_indicator | 0 | 1 | 尚未 |
| security_interpretation | 0 | 4 | 尚未 |
| unknown | 7 | 0 | 尚未 |

不同 claim type 的計數單位不同，詳見 claim_supportability.DRAFT.json；不能直接相除成精確率。
security_* 的 0 是未自動核准安全語意；primitive observations 仍存在，需人工判斷有無調查價值。
reported_change 與 electrical_change 是同一組 pair 的別名，不能雙重計分。
temporal candidate 計數只涵蓋 request 後出現 E 的 episode-level 機會，不是全部可能時間關係。

## 檔案與下一步

- complete_allowed_evidence.json.gz：整個允許視窗，包含 metadata、packet/message/process records。
- allowed_lineage.json.gz：包內的完整 parent edges。
- numerical_candidates.DRAFT.json：從完整 universe 產生的 candidates，不限 top-k。
- retrieved_E/N/EN.json、B0_E/N/EN.json：固定預算對照。
- annotation.DRAFT.json：待 reviewer 填寫、簽核；不要把自動候選直接當 gold。
