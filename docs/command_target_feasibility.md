# Command-target feasibility — Phase 1

結論：**對本次實際觀測到的 types 45/47/50，地址解析與靜態 control-point→asset mapping 可行；
但必須另核准一個 M/export 契約修訂。此次沒有將該修訂接入 export、retrieval 或 B0。**
types 46/48/49/51 未出現在本候選集，現有 decoder 亦未支持，不能宣稱已實證涵蓋全部 45–51。

來源：results/investigation-v1/audit/command_target_feasibility.json。
稽核程式 scripts/audit_command_targets.py 只讀 frozen event IDs、已雜湊核對的 primary PCAP、
canonical command IDs 與 data-point-map.json。未讀 event catalog、family、attack_point 或 malicious。
完整掃描五個 primary capture 至各候選最後 cutoff，沿用原 APDU dedup；98 個 command objects
（request/response 合計）逐 command evidence ID 與 canonical 核對。原三個 archive SHA256 重驗一致。

## 1. Exact bytes

以下為含 `0x68,length,APCI` 的完整 APDU，zero-based offsets，沿用既有已稽核 layout：

| 欄位 | Offset / 解析 |
|---|---|
| ASDU type | byte 6 |
| object count / SQ | byte 7，低 7 bits 為 count，bit 7 為 sequential addressing |
| COT | byte 8 低 6 bits，沿用 existing decoder；不聲稱 positive/negative、test 或執行語意 |
| CA | bytes [10:12)，2-byte little-endian |
| first IOA | bytes [12:15)，3-byte little-endian |
| 後續 IOA | SQ=0 每 object 另讀 3 bytes；SQ=1 後續 IOA 由第一個遞增 |

type45/47 的 object body 各跳過 1 byte；type50 跳過 5 bytes；不解析／輸出值或 select-execute qualifier。
count、object bounds、APDU length 全部檢查，unexpected layout fail closed。原 parser 已讀取 CA/IOA，
但只把 type1/13 monitoring objects 保留下來；command 地址在 canonical 建構前被丟棄。

## 2–5. Mapping 類別、表示及分母

| 量 | 結果 |
|---|---:|
| 已凍結候選事件 | 48 |
| 視窗內有 command-type activation request 的事件 | 28/48（58.33%） |
| 至少一個 request 有 mapping 的事件 | 28/48；在有 request 的事件中為 28/28 |
| 全部 requests 都有 mapping 的事件 | 28/28 |
| COT=6 request objects | 49 |
| exact CA.IOA 在 raw static mapping 找到 | 49/49 |
| 在現有 MEASUREMENT-only sanitized lookup 找到 | 0/49 |
| mapped asset 存在於現有 E static metadata | 49/49 |

其餘 20 事件沒有符合本定義的 request，不是 mapping failure。未見 command 也不等於 benign。
request mapping 全為 CONFIGURATION：closed 35、connected 3、tap_position 2、target_active_power 4、
target_active_power_percentage 5。這裡只讀「控制點的地址→element/context/attribute」，不是取用
configuration value、setpoint 或 initial_value。metadata 的控制點定義可以是 M；值與隱藏狀態仍不允許。
現有契約實作只允許 measurement channel，因此不能直接宣稱新 mapping 已獲准。

建議 asset ID 完全沿用 `opaque(asset_, source_id|element)`，控制點另用
`opaque(cp_, source_id|CA.IOA|context)`；namespace 加 source，避免跨 recording 誤合併。
private resolver 留 CA/IOA 與 raw mapping key；public 只給 cp/asset opaque IDs 與已核准的靜態屬性。
static asset 存在不保證事件當下有 E observation；額外 raw E linkage 計數另存
command_target_linkage_supplement.json，仍是 feasibility-only，不能作執行／因果結論。
該補充稽核顯示 44/49 requests 有同資產的 quality-valid E observation，且有後續回報；
其餘 5 個 requests 雖有 static asset mapping，但當窗未有同 asset 的有效 E 回報。

## 6. 重複、歧義與 collision

五份 map 的 entries 為 500、500、3640、3640、1908。以 object_pairs_hook 檢查 duplicate JSON keys，
均為 0；49 requests 的 exact address 未映射數為 0。
同 element+attribute 跨 CONFIGURATION/MEASUREMENT 的碰撞組分別為 2、2、58、58、2。
因此禁止用「attribute 名稱相同」替代 exact address mapping；特別是 tap_position，不能把 config 當量測。
同一 asset 有多個控制點是合法一對多；不能把 cp 合併成一筆獨立感測證據。
未來遇到 duplicate、context 不在 allowlist 或 missing address，一律 target=null，保留理由，不猜 asset。

## 7. 精確 amendment 提案（尚未實作）

machine-readable 設計見 command_target_amendment.proposed.json；完整 child-record JSON Schema
見 command_address_observation.schema.proposed.json。兩者未接入任何 runtime 或 B0。

既有 canonical m record 不改。若作者核准，另建 investigation-specific address child record：

```json
{
  "record_type": "command_address_observation",
  "evidence_id": "new_versioned_address_id",
  "parent_ids": ["existing_command_m_id"],
  "asdu_type": 45,
  "cause_of_transmission": 6,
  "object_index": 0,
  "observation_time": 0.0,
  "mapped_control_point_id": "cp_opaque_or_null",
  "mapped_target_asset_id": "asset_opaque_or_null",
  "mapping_evidence_id": "meta_opaque_or_null",
  "mapping_status": "exact_static_match_or_unmapped_or_ambiguous"
}
```

private provenance 額外保存 `ca:uint16`、`ioa:uint24`、APDU/object offset、source/map hashes；
public schema 不含 setpoint、initial value、select/execute bits、gold、raw filename 或 raw element name。
CA/IOA 若日後需要公開必須再說明必要性；本提案優先使用 opaque control point。

command_observed payload 新增可空 `address_evidence_id`、`mapped_control_point_id`、
`mapped_target_asset_id`、`mapping_evidence_id`。多 object APDU 一個 address child/object，不能把不同 target 混成單一 command。
最強敘述僅為：「觀察到一個命令型 activation request，其地址對應資產 X 的控制點」。
asset_relationship 可新增明確的 `command_address_maps_to_asset`，需 address+M；
temporal_association 的 `same_observed_asset` 需 command-address→asset 與 E-channel→同 asset 的兩條 M 邊，
加兩個有效 observation。capture ordering 依舊不表示 cause、execution 或 malicious intent。

需新增獨立 evidence/export/schema version、mapping allowlist、parser/address 測試與 amendment lock；
不得修改 frozen classification EvidenceRecord sanitizer、features、模型、results 或既有 locks。

## 8. 新 leakage 與錯誤風險

raw CA/IOA 與 element 可暴露 topology/recording 身分；使用 source-scoped opaque IDs。
完整 mapping 有 initial_value 與非允許欄位，僅擷取 exact allowlist，不把整列傳模型。
target_* attribute 容易被誤解為實測值；只作控制點類別，不輸出任何設定值。
不得用 attack_point/family 補 missing mapping；不以 asset 對上就推斷設備接受或物理因果。
source namespace 不同的同名 element 不自動視為同一 asset。

因此本輪 B0 的 command target 仍明示 unknown；待作者核准修訂後，另行實作與測試。
