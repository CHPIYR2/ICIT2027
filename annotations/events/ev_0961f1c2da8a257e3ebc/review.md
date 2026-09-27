# Pilot evidence review — DRAFT_UNREVIEWED

Event: `ev_0961f1c2da8a257e3ebc`。本文件是自動整理的審查入口，不是 gold。

## 完整證據與 retrieval accounting

完整允許的 record counts：{'packet': 1576, 'message': 782, 'process': 2991}。共 5349 筆。
mapped numeric channels 中 0 個沒有有效 post observation；post state observations 3 筆。
完整來源數值候選 pair 範圍：{'pre_post': 249}；pre-only pair 不能描述為事件後變化。

| View | Eligible 原始 records | Retrieved entries | B0 觀測列 | B0 differences | Gold recovered |
|---|---:|---:|---:|---:|---|
| E | 2991 | 64 | 44 | 20 | 未評分 |
| N | 2358 | 64 | 64 | 0 | 未評分 |
| EN | 5349 | 64 | 54 | 10 | 未評分 |

## 代表性 B0 網路觀測（capture seconds relative to anchor）

| Time | Claim type | Evidence ID | 可說的內容 |
|---:|---|---|---|
| 0.02288723 | command_observed | `m_81c335db83989561408ba943` | 命令型 activation request；target 與 execution 仍 unknown |
| 0.0721302 | acknowledgement_observed | `m_a052dda75d6ad650ae9eee19` | protocol response；不代表 physical success |
| 11.08039 | command_observed | `m_5d2f2a548ee91e883e97cb6c` | 命令型 activation request；target 與 execution 仍 unknown |
| 11.13011 | acknowledgement_observed | `m_93f0f5b9dd4f859ff7bc901f` | protocol response；不代表 physical success |
| 22.13832 | command_observed | `m_63249b4168eac3854c63d52b` | 命令型 activation request；target 與 execution 仍 unknown |
| 22.20787 | acknowledgement_observed | `m_76c7710ecab1e8f55eac20f2` | protocol response；不代表 physical success |
| 33.21649 | command_observed | `m_d6b73974cd0ed46afb4321f0` | 命令型 activation request；target 與 execution 仍 unknown |
| 33.266 | acknowledgement_observed | `m_0cb54e34217416dc7ef009dd` | protocol response；不代表 physical success |

## B0 數值差（僅兩筆 reported values）

| Family | Channel | Before time/value | After time/value | Δ | Unit |
|---|---|---|---|---:|---|
| voltage | `ch_076a19f4adcfcfee` | -58.15417 / 0.9995937 | 51.89954 / 1.000173 | 0.0005794168 | PER_UNIT |
| voltage | `ch_0df799387203cb49` | -57.80423 / 0.9856657 | 52.1822 / 0.9845548 | -0.001110911 | PER_UNIT |
| active_power | `ch_0270f5cae2a7db0e` | -57.80423 / 65318.14 | 52.1822 / -264395 | -329713.1 | WATT |
| active_power | `ch_001bab0aa0d8aca6` | -56.91923 / 0 | 53.1418 / 0 | 0 | WATT |
| reactive_power | `ch_0ae2e038e7d56a1d` | -56.68624 / 6589520 | 53.36657 / 6598665 | 9144.5 | VAR |
| current | `ch_1038cbb1a8c65915` | -55.57306 / 19.6056 | 54.47087 / 18.04773 | -1.557867 | AMPERE |
| reactive_power | `ch_01b8d2ffcf69123e` | -53.83675 / 0 | 56.1741 / 0 | 0 | VAR |
| current | `ch_01e1fd95179ba1da` | -51.63035 / 28.60183 | 58.42262 / 29.26837 | 0.6665382 | AMPERE |
| current | `ch_1172139178576b3b` | -51.25246 / 10.32528 | 58.81133 / 16.92008 | 6.594797 | AMPERE |
| voltage | `ch_1050b0e0a5f690c5` | -51.25246 / 0.9858717 | 58.81133 / 0.9849843 | -0.0008874536 | PER_UNIT |

完整精度與 before/after evidence IDs 在 B0_EN.json；不以截取表格取代原始引用。
所有數字是 captured reported measurements；沒有物理因果或惡意意圖結論。

## 全部原始來源的 claim-type 可行性草稿

| Type | 可支持候選／機會 | 不足 probes | 人工確認 |
|---|---:|---:|---|
| network_activity | 2358 | 0 | 尚未 |
| command_observed | 4 | 0 | 尚未 |
| acknowledgement_observed | 1953 | 0 | 尚未 |
| communication_gap | 1 | 0 | 尚未 |
| reported_value | 2991 | 62 | 尚未 |
| reported_change | 249 | 0 | 尚未 |
| reported_state_change | 0 | 65 | 尚未 |
| electrical_change | 249 | 0 | 尚未 |
| temporal_association | 4 | 4 | 尚未 |
| asset_relationship | 252 | 4 | 尚未 |
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
