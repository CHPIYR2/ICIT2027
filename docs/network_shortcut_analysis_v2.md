# Network shortcut analysis — Protocol v2 探索性稽核

僅重分析已凍結的 features/predictions，不重訓、不選新閾值、不產生新 observability 成績。
完整分布：results/exploratory-v2/audit/feature_distributions.json；規則分組：existing_command_rule.json。

## 直接與間接資訊路徑

- command/activation response：直接 ASDU/COT 語意。既有 >0 規則使用合法觀測欄位，未讀取 event truth 作輸入。
- APDU rates/gaps：不直接解碼命令類別，但仍需要 IEC framing，命令程序可改變 count/timing。
- U-format：IEC 控制格式，非 TCP 資訊，可能與啟停／測試程序相關；不能僅以「沒有 ASDU」稱 transport-only。
- RST：普通 TCP 行為，仍可能對應特定腳本。
- endpoint count：合法 transport 數量，但每場景固定且不同，呈現 topology/recording 結構。
- packet size、fine timing 是潛在消息型態／腳本 proxy；最小提案先不加入 packet-size 統計。

這些關聯稱 dataset-specific/procedural shortcut；未發現使用 forbidden G 的證據，不能單憑強預測性称 data leakage。

## 既有 N 按類別分布

每格為 min–max；median；IQR。全場景合併，類別組成與場景偏移需另看分層摘要。

| N 欄位 | CYBER 75 | BENIGN 44 |
|---|---|---|
| n_post_log_rate | 1.9718–4.202; 3.6082; 0.82527 | 2.0082–4.3025; 3.6422; 1.9147 |
| n_log_rate_change | -0.072287–0.017763; -0.0059239; 0.016143 | -0.0078474–0.034046; 0.0061153; 0.0090251 |
| n_command_log_count | 0–0; 0; 0 | 0.69315–1.6094; 0.69315; 0.40547 |
| n_activation_response_log_count | 0–0; 0; 0 | 0.69315–1.6094; 0.69315; 0.40547 |
| n_rst_log_count | 0–1.3863; 0; 0 | 0–0; 0; 0 |
| n_post_max_gap_fraction | 0.0019975–0.028912; 0.004867; 0.011044 | 0.0018811–0.050321; 0.0056672; 0.013438 |
| n_u_log_count | 0–1.7918; 0; 0 | 0–0; 0; 0 |
| n_endpoint_log_count | 3.5264–4.3041; 4.1271; 0.17693 | 3.5264–4.3041; 4.1271; 0.7777 |

## 原命令存在規則：按 recording／scenario／family 重列

原先已定義規則：command log count>0 判 BENIGN，否則 CYBER；本輪沒有搜尋門檻。
119 個事件（CYBER 75、BENIGN 44）全部符合，包含原 84 評估事件。這不是新增獨立驗證。
activation-response 欄在此資料亦呈現相同有／無分隔，但不新增調參規則。

| Recording | n | command log-count range | response range | post log-rate median | endpoint log-count median |
|---|---:|---|---|---:|---:|
| 01-Basic/test | 28 | 0–1.6094 | 0–1.6094 | 2.026 | 3.5264 |
| 01-Basic/train | 7 | 0.69315–1.3863 | 0.69315–1.3863 | 2.1342 | 3.5264 |
| 02-Semiurban/test | 39 | 0–1.3863 | 0–1.3863 | 4.0304 | 4.3041 |
| 02-Semiurban/train | 9 | 0.69315–1.0986 | 0.69315–1.0986 | 4.0407 | 4.3041 |
| 03-Rural/test | 36 | 0–1.3863 | 0–1.3863 | 3.6071 | 4.1271 |

| 原始家族 | n | 命令存在事件 | 原規則正確 |
|---|---:|---:|---:|
| arp-spoof:arp-spoof-dos | 14 | 0 | 14/14 |
| control center:Cable Maintenance | 4 | 4 | 4/4 |
| control center:Close Ring | 3 | 3 | 3/3 |
| control center:Generator Bootstrap | 3 | 3 | 3/3 |
| control center:Generator Control | 11 | 11 | 11/11 |
| control center:Manual Commands | 2 | 2 | 2/2 |
| control center:Open Ring | 3 | 3 | 3/3 |
| control center:Separator Movement | 6 | 6 | 6/6 |
| control center:Seperator Movement | 2 | 2 | 2/2 |
| control center:Transformer Maintenance | 4 | 4 | 4/4 |
| control center:maintenance1 | 1 | 1 | 1/1 |
| control center:maintenance2 | 1 | 1 | 1/1 |
| control center:maintenance3 | 1 | 1 | 1/1 |
| control center:sgencontrol | 1 | 1 | 1/1 |
| control center:trafostep | 1 | 1 | 1/1 |
| control center:trafostep2 | 1 | 1 | 1/1 |
| control-and-freeze:control-and-freeze | 15 | 0 | 15/15 |
| drift-off:drift-off | 22 | 0 | 22/22 |
| industroyer:industroyer | 24 | 0 | 24/24 |

全部八個 N 欄位按 scenario、recording、family 與 scenario×truth 的完整 range/median/IQR 均在 JSON；
場景分布也另表於 network_distribution_shift_v2.md。未檢查程序碼因果機制，不把統計分隔當因果證明。

## 原預測的 event transition 稽核

主比較：每個模型均 84/84 unchanged。既有兩欄消融只有 RF 改變 20 件：15 corrected_N、5 hurt_N。
其餘模型亦全部 unchanged。以下按原始家族列既有 RF 消融，並非新 Protocol-v2 regime。

| 家族 | n | N 正確 | EN 正確 | corrected_N | hurt_N | unchanged |
|---|---:|---:|---:|---:|---:|---:|
| arp-spoof:arp-spoof-dos | 12 | 12 | 12 | 0 | 0 | 12 |
| control center:Cable Maintenance | 2 | 1 | 2 | 1 | 0 | 1 |
| control center:Close Ring | 3 | 1 | 3 | 2 | 0 | 1 |
| control center:Generator Bootstrap | 2 | 0 | 2 | 2 | 0 | 0 |
| control center:Generator Control | 9 | 3 | 5 | 2 | 0 | 7 |
| control center:Open Ring | 3 | 0 | 1 | 1 | 0 | 2 |
| control center:Separator Movement | 4 | 2 | 4 | 2 | 0 | 2 |
| control center:Seperator Movement | 2 | 0 | 2 | 2 | 0 | 0 |
| control center:Transformer Maintenance | 2 | 2 | 2 | 0 | 0 | 2 |
| control-and-freeze:control-and-freeze | 10 | 7 | 9 | 2 | 0 | 8 |
| drift-off:drift-off | 18 | 14 | 15 | 1 | 0 | 17 |
| industroyer:industroyer | 17 | 17 | 12 | 0 | 5 | 12 |

每一個改變與未改變事件均有診斷列，包括 ID、scenario、family、N/EN scores/predictions、正確性與 evidence hash，
見 existing_prediction_transitions.json。這是模型對照造成的判斷差異，不是操弄 E 的物理因果效果。
