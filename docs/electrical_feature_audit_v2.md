# Electrical feature audit — Protocol v2 探索性稽核

本文件是已觀察 Sherlock 119 個事件的描述性 audit，含 Basic 35 與先前評估 84；不是新模型結果。
所有數字來自既有 pipeline-v2 episodes/features，不使用 physical.zip、initial_value 或未來資料。
逐事件來源、quality-valid channel coverage 見 results/exploratory-v2/audit/episode_coverage.json。

## 1. 哪些欄位實際有值

每個場景的四個 numeric relative change、五個 post missing fraction 均為全事件非缺失。
但 state changed fraction 在 Basic 35/35、Semiurban 48/48、Rural 36/36 都缺失。
沒有可配對的 state pre/post channel，不能視為 zero transitions；missing fraction 有值也不代表 process value 已觀測。

## 2. 可用的前後 channel coverage

表格為每事件同時有有效 pre/post 的 channel 數：min / median / max（靜態 mapped 數）。
事件是統計單位，沒有把多個 channels 擴增為事件。

| 場景 | Family | paired channel min/median/max | mapped channels |
|---|---|---|---:|
| 01-Basic | voltage | 46/49/49 | 49 |
| 01-Basic | current | 32/34/34 | 34 |
| 01-Basic | active_power | 78/83/83 | 83 |
| 01-Basic | reactive_power | 78/83/83 | 83 |
| 01-Basic | reported_state | 0/0/0 | 65 |
| 02-Semiurban | voltage | 377/397/397 | 397 |
| 02-Semiurban | current | 255/269/269 | 269 |
| 02-Semiurban | active_power | 586/616/616 | 616 |
| 02-Semiurban | reactive_power | 586/616/616 | 616 |
| 02-Semiurban | reported_state | 0/0/0 | 482 |
| 03-Rural | voltage | 178/189/189 | 189 |
| 03-Rural | current | 121/129/129 | 129 |
| 03-Rural | active_power | 342/362/362 | 362 |
| 03-Rural | reactive_power | 342/362/362 | 362 |
| 03-Rural | reported_state | 0/0/0 | 300 |

四個 numeric family 的每事件 pre/post 覆蓋普遍完整或接近完整；reported_state 的 paired coverage 一律零。
此結果支持保留現有 numeric E 作控制條件，不支持憑空恢復初始 state。

## 3. CYBER/BENIGN 的既有 E 分布

以下為 min–max；median；IQR。這些是所有場景合併的描述，會混入場景與事件家族構成差異，
不能據此挑閾值或宣稱特徵有因果效果。按場景×類別的全部統計見 feature_distributions.json。

| E 欄位 | CYBER (75) | BENIGN (44) |
|---|---|---|
| e_voltage_relative_change | 0.00027251–1; 0.0018077; 0.0025603 | 0.00047565–1; 0.0059106; 0.01827 |
| e_current_relative_change | 0.11837–124.15; 0.27122; 0.15141 | 0.1194–26.239; 1.9221; 9.1284 |
| e_active_power_relative_change | 0.0021488–4669.6; 1; 0.98713 | 0.24991–1500; 14.445; 282.63 |
| e_reactive_power_relative_change | 0.00011368–354.13; 3.1818; 11.321 | 0.00084761–857.98; 14.526; 53.508 |
| e_voltage_post_missing | 0–0.061224; 0; 0 | 0–0; 0; 0 |
| e_current_post_missing | 0–0.062016; 0; 0 | 0–0; 0; 0 |
| e_active_power_post_missing | 0–0.060241; 0; 0 | 0–0; 0; 0 |
| e_reactive_power_post_missing | 0–0.060241; 0; 0 | 0–0; 0; 0 |
| e_reported_state_post_missing | 0.95385–1; 1; 0.0033333 | 0.95385–1; 0.9973; 0.0075 |
| e_state_changed_fraction | 全缺失 | 全缺失 |

四個 numeric change 都在兩類內變動；BENIGN 的典型變化也可能很大，不能把大幅電氣變動直接等同攻擊。
連續量的 missing fractions 在 44 個 BENIGN 均為零，部分 CYBER 大於零；missingness 的確可能帶有通訊／程序線索。
但目前沒有比較 values-only/missingness-only 模型，**不能回答缺失是否比數值更有預測力**。
如需這項比較，須另核准固定分組消融，不從本表挑最佳欄位。

## 4. 電氣變化是否依事件家族不同

原始 family_description 保留，不合併拼字相近名稱。下表只示既有變化特徵的 family median；
全部欄位、range/IQR 與 counts 已保存於 JSON，少數家族只有一件，不作顯著性推論。

| 原始家族 | n | voltage relative change median | active-power relative change median |
|---|---:|---:|---:|
| arp-spoof:arp-spoof-dos | 14 | 0.0014328 | 1.1057 |
| control center:Cable Maintenance | 4 | 0.83367 | 242.32 |
| control center:Close Ring | 3 | 0.0065847 | 340.92 |
| control center:Generator Bootstrap | 3 | 0.0029365 | 645.05 |
| control center:Generator Control | 11 | 0.0024371 | 1.9691 |
| control center:Manual Commands | 2 | 0.008413 | 1.471 |
| control center:Open Ring | 3 | 0.010137 | 3.8408 |
| control center:Separator Movement | 6 | 0.0062 | 203.55 |
| control center:Seperator Movement | 2 | 0.0061815 | 153.53 |
| control center:Transformer Maintenance | 4 | 0.50107 | 1.5027 |
| control center:maintenance1 | 1 | 0.013468 | 293.33 |
| control center:maintenance2 | 1 | 0.0034072 | 350.9 |
| control center:maintenance3 | 1 | 0.66619 | 352.1 |
| control center:sgencontrol | 1 | 0.00047565 | 0.24991 |
| control center:trafostep | 1 | 0.019455 | 0.88383 |
| control center:trafostep2 | 1 | 0.015595 | 1.6949 |
| control-and-freeze:control-and-freeze | 15 | 0.0019107 | 0.32864 |
| drift-off:drift-off | 22 | 0.0013148 | 0.74843 |
| industroyer:industroyer | 24 | 0.012594 | 1 |

家族摘要差異明顯，但同時混有場景規模、資產類型、動作方式與數值 baseline。
目前 max aggregation 會隨 channel 數及極端值改變，尤其 near-zero baseline 由固定 floor 穩定後仍可產生很大比值。

## 5. 足夠性與候選改進（未實作）

建議第一輪 observability matrix 保持原 10 欄 E，讓網路條件成为唯一主要變動因素。
這套 E 足夠作保守參考，但不能表示全部製程行為或獨立物理真值。

後續獨立提案可考慮：

- 最大 post deviation：每 channel 的 max(abs(post−mean(pre)))/max(abs(mean(pre)),既有 family floor)，再以固定 family 90th percentile 聚合；需 pre>=1、post>=1。
- 變異變化：每 channel 的 log1p(var(post)/floor²)−log1p(var(pre)/floor²)，population variance，需兩邊各>=2；family 取中位數。
- freshness：每 channel 到可見截止時間的最後有效觀測 age，無觀測為 None；不得補窗外舊值。
- 狀態轉移數：只有同一 channel 至少兩筆有效已觀測 state 才能計算，不能用 initial state 補起點；先核對實際可用性。
- 超過偏差門檻的 channel fraction 如需使用，門檻只能由 Basic training fold 定義，不能依已見 84 labels 設計。

上述候選沒有計算新 feature matrix、沒有 fit/predict，也沒有選出「最能讓融合勝出」的一组。
是否新增 E 是獨立作者 gate；本提案建議暫不新增。
