# Investigation claim-support policy — 待核准提案

適用有限、機械可檢查的 evidence consistency/support；不是 arbitrary semantic truth oracle。
主張詞彙共 13 種。新增 asset_relationship 是明列的提案，對應 RQ1／Q3，不自行擴 ontology。

## 每類規則

| Claim type | 必要證據 | 允許結論 | 禁止更強解釋 | 機械檢查 |
|---|---|---|---|---|
| network_activity | 可見 p record；若說 IEC frame 則 m record | 在監測點看到 packet、I/S/U frame 或 RST | 惡意、入侵、接收端接受 | header/type、capture time、scope、p/m lineage；不由 U 泛稱特定 TESTFR |
| command_observed | 可見 I-format m，ASDU 45–51 且 COT=6；其 p 有有效 provenance | 觀察到命令型 activation request | 已 execute、設備狀態已改、指定 target asset、select/execute 判定 | 精确 ASDU/COT allowlist；無 command 地址或 flags 時拒絕更強說法 |
| acknowledgement_observed | p 的 TCP ACK bit，或 m 的 S frame，或命令型 ASDU/COT=7 | 明列是哪一種 response/ACK 被觀察 | 三種 ACK 混同、positive success、某 request 已完成 | subtype 分開；COT 高位未保留，不作 positive/negative 判斷；無 correlation key 不配對特定 request |
| communication_gap | 可見 TCP/2404 population 的完整 interval receipt，加 bounding IDs 或 scope boundary | 某可見區間沒有符合條件的 captured packets | 網路斷線／sensor outage／DoS 已發生、隱藏尾段無流量 | 以完整 eligible records 重算最大間隔；top-k 不足；明列左／右邊界是否 censoring |
| reported_value | quality-valid E record、channel/M | 量測通道回報某值／某狀態 | 獨立物理真值、命令 setpoint 當量測 | value/type、unit、asset、channel、quality、observation time |
| reported_change | 同 channel、asset、unit 的兩筆有效數值 E | 兩筆回報差值／比例差；明列 timestamps | 當成持續趨勢、因果或電氣危險閾值 | Δ=b−a；百分比=100(b−a)/abs(a)，a=0 則不足，不沿用 ML floor |
| reported_state_change | 同 channel 兩筆有效 bool E，先後可定且值不同 | 兩筆回報狀態不同 | 沒 pre 就補初始態、設備確實動作 | bool、同 channel、兩筆時間與值；119 事件無 pre/post pair，不能假裝有 |
| electrical_change | 同 reported_change，且 family 是 voltage/current/active_power/reactive_power | 有單位的 reported electrical difference | attack-caused change、severity 或實際物理因果 | 同上；與 reported_change 同內容只算一個 gold fact，不雙重加分 |
| temporal_association | 兩個受支援 visible observations；跨 N/E 必須 EN | A 的捕獲時間早於 B、或同 capture time；episode-level association | causal link、真實設備時間先後、command target 同一資產 | Δt、同 scope；same_observed_asset 必須可核對 mapping；命令無 asset 不准補 |
| asset_relationship | E+sanitized M 的同資產映射，或 p 的 endpoint pair | 兩 observations 對應同 mapped asset；packet 的 src/dst endpoints | endpoint=物理資產、topology 鄰接、command作用資產、malicious asset | asset/channel M 一致；p endpoint direction；null asset 不可 wildcard 匹配 |
| security_indicator | 有限 primitive：RST、命令 request、captured gap、reported numeric difference | 值得人工檢視的 observation | 此 indicator 證明攻擊、異常或 compromise | 逐 primitive 套上方規則；不學分類閾值、不導入 family label |
| security_interpretation | 至少一個支援的 indicator 與其 visible evidence | 明確、較弱的「值得調查；意圖／因果未確定」 | causation、malicious intent、attacker identity、successful compromise、physical execution、benign/safe | 只支援 review_required template；強結論為 INSUFFICIENT；可提出獨立較弱 qualified projection |
| unknown | scope／view／retrieval receipt + 明確缺少的 requirement | 在此 bundle／此可見 scope 下不能回答哪個問題 | 不足→BENIGN、缺證→不存在 | 區分 view_excluded、not_retrieved、no_observation、no_valid_pair、mapping unavailable、quality、policy；主張 absence 需完整 query |

acknowledgement_observed 不包含未解析的 activation termination 或任意 application ACK。
以上 ASDU/COT 是沿用目前凍結契約與 parser 的窄解釋，不聲稱完整 IEC-104 compliance。

## 八項 checks 與判決

1. Reference：引用必須存在於本 episode 的允許 namespace，不接受別的事件 ID。payload 引用必須也列在 evidence_ids。
2. Visibility：內容必須屬本 condition 的 field allowlist 且確曾提供給該生成 run；猜中未 retrieval 的 ID 也不算合格。
3. Asset：檢查 channel→asset/unit M；packet endpoint 不是 equipment identity；未知保留 null。
4. Time：以 capture timestamp 相對 t0 的秒數運算；半開 [-60,60)，同 timestamp 不可由檔案順序宣稱嚴格先後。
   時差採 1 microsecond 的數值容忍，不將此容忍當作真實時鐘精度／同步證明。
5. Numerical：從原始 cited values 重算，`abs(error) <= 1e-6 + 1e-6*abs(expected)` 為計算容忍；
   明示不是感測器不確定度。禁止 NaN/Inf；bool 不當 numeric；percent 的 baseline=0 則不足。
6. Units：原契約 PER_UNIT/AMPERE/WATT/VAR/NONE；百分比單獨 PERCENT；時間 SECOND；count COUNT。
   不自行把 pu 變 V，不將 W 當 energy、不把不同 channel/unit 混算。
7. Lineage：canonical parents hash/ID/time 有效；source removal 關閉整條後代；derived computations 保留
   全部 parent IDs 或完整可重算 query receipt/hash。不能將同 packet 的多種表示算獨立 corroboration。
8. Policy：typed payload 滿足此表才允許固定語句。任何自由文字的更強解釋不隨 PASS 自動過關。

SUPPORTED：整個被發佈的 canonical statement 滿足規則。QUALIFIED：只發布明確較弱且可支援的 projection，
附原 stronger conclusion 被 withholding 的理由；不是保留過度主張後加一句 disclaimer。
INSUFFICIENT：不能建立支持；保留 reason，不輸出原 security conclusion。
任何未檢查的欄位標 NOT_CHECKABLE，不能假装 PASS。

## E-only 與 parent visibility 的一致定義

canonical provenance 與 LLM 可見內容分層管理。E-only 可看到 E leaf 與必要 sanitized M；私有 verifier
可以沿 opaque parent handles 查 hash、祖先存在與 source authorization，但不可把 N 的 ASDU/COT/endpoint
拿來支持 E-only 的網路主張，也不可回傳 hidden headers。這是 export view restriction，不是 source removal。
若真正移除原始 p，E leaf 亦被移除，不可藉私有 resolver 恢復。

N-only 沒有 process payload；EN 仍只能看到契約允許部分。retrieval 與 verifier 共用同一 visibility receipt，
但 verifier status 不是 gold。未取回的 evidence 不能用於驗證生成主張；完整 interval 的 receipt 可作為
已提供的 derived evidence，前提是其數值與 query 可重算且標示 provenance。

## 資訊不足不能被機械驗證「保證為真」

rules 只能判斷契約定義的支援關係，不知道攻擊者真正意圖或 sensor 值是否遭修改。
最初 security policy 很保守，可能造成機械可回答的 security interpretation 類型很少；必須量化 coverage
與人類 gold 的可用性，不能只報 unsupported claims 被清光。非模板自由文的風險由獨立人工評估揭露。
