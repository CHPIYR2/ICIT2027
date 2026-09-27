# Pilot evidence review — DRAFT_UNREVIEWED

Event: `ev_21f18503563e6a677ae5`。本文件是自動整理的審查入口，不是 gold。

## 完整證據與 retrieval accounting

完整允許的 record counts：{'packet': 1606, 'message': 791, 'process': 2973}。共 5370 筆。
mapped numeric channels 中 0 個沒有有效 post observation；post state observations 0 筆。
完整來源數值候選 pair 範圍：{'pre_post': 249}；pre-only pair 不能描述為事件後變化。

| View | Eligible 原始 records | Retrieved entries | B0 觀測列 | B0 differences | Gold recovered |
|---|---:|---:|---:|---:|---|
| E | 2973 | 64 | 43 | 21 | 未評分 |
| N | 2397 | 64 | 64 | 0 | 未評分 |
| EN | 5370 | 64 | 54 | 10 | 未評分 |

## 代表性 B0 網路觀測（capture seconds relative to anchor）

| Time | Claim type | Evidence ID | 可說的內容 |
|---:|---|---|---|
| -59.70812 | network_activity | `m_d22295e7d6c0ef4c3d4f0415` | iec_S_frame |
| -59.70812 | network_activity | `p_4693fd1a75031109b5bf979f` | captured_packet |
| -59.68915 | network_activity | `m_c43a0d245b7964000fc7fbc2` | iec_I_frame |
| -59.68915 | network_activity | `p_859a52e451c8a0a908f4ef9f` | captured_packet |
| -59.65934 | network_activity | `m_deaf308222a4578da64d0acc` | iec_S_frame |
| -59.63113 | network_activity | `m_b5784b7ef88227ea03dc3209` | iec_I_frame |
| -59.45913 | network_activity | `m_5bad319a9a2af090373032bd` | iec_S_frame |
| -59.35812 | network_activity | `m_4b7e08b5dfd2e207e293b215` | iec_S_frame |

## B0 數值差（僅兩筆 reported values）

| Family | Channel | Before time/value | After time/value | Δ | Unit |
|---|---|---|---|---:|---|
| current | `ch_1172139178576b3b` | -59.68915 / 24.556 | 50.38743 / 24.96087 | 0.4048786 | AMPERE |
| voltage | `ch_1050b0e0a5f690c5` | -59.68915 / 0.9654567 | 50.38743 / 0.9651394 | -0.0003173351 | PER_UNIT |
| reactive_power | `ch_01b8d2ffcf69123e` | -57.0766 / 0 | 53.04987 / 0 | 0 | VAR |
| active_power | `ch_001bab0aa0d8aca6` | -56.66393 / 600000.9 | 53.40296 / 600088.1 | 87.1875 | WATT |
| voltage | `ch_076a19f4adcfcfee` | -52.60283 / 0.9971074 | 57.45726 / 0.9967296 | -0.0003778338 | PER_UNIT |
| reactive_power | `ch_0ae2e038e7d56a1d` | -51.52638 / 5979875 | 58.53742 / 5996472 | 16597 | VAR |
| voltage | `ch_0df799387203cb49` | -50.58163 / 0.964868 | 59.48967 / 0.9644881 | -0.0003798604 | PER_UNIT |
| active_power | `ch_0270f5cae2a7db0e` | -50.58163 / -602983.4 | 59.48967 / -612355.7 | -9372.25 | WATT |
| current | `ch_01e1fd95179ba1da` | -50.19346 / 13.09579 | 59.88336 / 13.79852 | 0.7027273 | AMPERE |
| current | `ch_1038cbb1a8c65915` | -50.18901 / 49.5108 | 59.91904 / 50.07489 | 0.5640869 | AMPERE |

完整精度與 before/after evidence IDs 在 B0_EN.json；不以截取表格取代原始引用。
所有數字是 captured reported measurements；沒有物理因果或惡意意圖結論。

## 全部原始來源的 claim-type 可行性草稿

| Type | 可支持候選／機會 | 不足 probes | 人工確認 |
|---|---:|---:|---|
| network_activity | 2397 | 0 | 尚未 |
| command_observed | 0 | 1 | 尚未 |
| acknowledgement_observed | 1978 | 0 | 尚未 |
| communication_gap | 1 | 0 | 尚未 |
| reported_value | 2973 | 65 | 尚未 |
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
