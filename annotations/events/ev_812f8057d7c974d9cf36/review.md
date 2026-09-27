# Pilot evidence review — DRAFT_UNREVIEWED

Event: `ev_812f8057d7c974d9cf36`。本文件是自動整理的審查入口，不是 gold。

## 完整證據與 retrieval accounting

完整允許的 record counts：{'packet': 1649, 'message': 784, 'process': 2900}。共 5333 筆。
mapped numeric channels 中 13 個沒有有效 post observation；post state observations 0 筆。
完整來源數值候選 pair 範圍：{'pre_post': 236, 'pre_only': 13}；pre-only pair 不能描述為事件後變化。

| View | Eligible 原始 records | Retrieved entries | B0 觀測列 | B0 differences | Gold recovered |
|---|---:|---:|---:|---:|---|
| E | 2900 | 64 | 43 | 21 | 未評分 |
| N | 2433 | 64 | 64 | 0 | 未評分 |
| EN | 5333 | 64 | 54 | 10 | 未評分 |

## 代表性 B0 網路觀測（capture seconds relative to anchor）

| Time | Claim type | Evidence ID | 可說的內容 |
|---:|---|---|---|
| -59.9263 | network_activity | `m_949505eff9c219114048cb45` | iec_I_frame |
| -59.9263 | network_activity | `p_0e9a767fdccc95086e54f571` | captured_packet |
| -59.92227 | network_activity | `p_a3ba933b0939f7b395209149` | captured_packet |
| -59.84635 | network_activity | `m_d8430a6032105fe139396f26` | iec_I_frame |
| -59.82712 | network_activity | `m_e2bfc86606f860a1b48a3aee` | iec_I_frame |
| -59.7775 | network_activity | `m_164c814364759b4987f1bb12` | iec_I_frame |
| -59.70086 | network_activity | `m_126547b7767c082711961103` | iec_I_frame |
| -59.67351 | network_activity | `m_c38ad7149cffdb0001b67542` | iec_I_frame |

## B0 數值差（僅兩筆 reported values）

| Family | Channel | Before time/value | After time/value | Δ | Unit |
|---|---|---|---|---:|---|
| reactive_power | `ch_01b8d2ffcf69123e` | -58.64333 / 0 | 1.395613 / 0 | 0 | VAR |
| current | `ch_01e1fd95179ba1da` | -59.9263 / 14.04461 | 50.16439 / 13.33471 | -0.7098923 | AMPERE |
| active_power | `ch_001bab0aa0d8aca6` | -58.53906 / 0 | 51.62748 / 0 | 0 | WATT |
| voltage | `ch_076a19f4adcfcfee` | -57.64087 / 0.9972591 | 52.41377 / 0.9976875 | 0.0004283786 | PER_UNIT |
| reactive_power | `ch_0ae2e038e7d56a1d` | -56.49329 / 6092464 | 53.56847 / 5942967 | -149497 | VAR |
| voltage | `ch_0df799387203cb49` | -55.58934 / 0.9674169 | 54.48573 / 0.9707554 | 0.003338456 | PER_UNIT |
| active_power | `ch_0270f5cae2a7db0e` | -55.58934 / -664924.3 | 54.48573 / -581716.9 | 83207.38 | WATT |
| current | `ch_1038cbb1a8c65915` | -55.22752 / 23.26909 | 54.88003 / 21.67897 | -1.590118 | AMPERE |
| voltage | `ch_1050b0e0a5f690c5` | -54.74844 / 0.9680766 | 55.32999 / 0.9713996 | 0.003323019 | PER_UNIT |
| current | `ch_1172139178576b3b` | -54.74844 / 25.74979 | 55.32999 / 24.09114 | -1.658642 | AMPERE |

完整精度與 before/after evidence IDs 在 B0_EN.json；不以截取表格取代原始引用。
所有數字是 captured reported measurements；沒有物理因果或惡意意圖結論。

## 全部原始來源的 claim-type 可行性草稿

| Type | 可支持候選／機會 | 不足 probes | 人工確認 |
|---|---:|---:|---|
| network_activity | 2433 | 0 | 尚未 |
| command_observed | 0 | 1 | 尚未 |
| acknowledgement_observed | 1952 | 0 | 尚未 |
| communication_gap | 1 | 0 | 尚未 |
| reported_value | 2900 | 65 | 尚未 |
| reported_change | 249 | 0 | 尚未 |
| reported_state_change | 0 | 65 | 尚未 |
| electrical_change | 249 | 0 | 尚未 |
| temporal_association | 0 | 0 | 尚未 |
| asset_relationship | 249 | 0 | 尚未 |
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
