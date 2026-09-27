# Protocol v2 — 探索性網路可觀測性結果

**Exploratory / post-confirmatory：相同、先前已評估的 84 個 Sherlock 事件；不是新的盲測或獨立確認。**
作者已核准固定設計；模型／特徵／可見性程式先通過測試、凍結，再產生這些分數。原 v1 結果保留。

## 比較方式

- Basic 35 作原五折 OOF 及最終訓練；Semiurban/Rural 84 作探索性評估。
- LR/RF/GB 使用原超參數、seed=20270921、threshold=0.5；不依新成績調參或選擇 levels。
- N-FULL 原 8 欄；N-TRANSPORT 5 個 header-only 特徵，不讀取 ASDU/COT/U-format/process payload。
- N 的 pre 60 秒保留，post 只可見 60/45/30/15 秒；E 全窗固定。各 regime 在訓練時也施加相同可見性。
- rate/gap 使用實際可見時長；unknown 尾段不當成零流量。這是 N 分析出口尾段不可用，不是全域 raw-source loss。
- 33 個 model/view 條件：9 個原 E/FULL 參考、24 個新條件。原參考的 saved-model predictions 已重現核對。

## 主量：N 與 EN 的整體 Macro F1 與 ΔFusion

| 網路條件 | 模型 | N | EN | Δ(EN−N) | 95% paired CI | 改對／改錯 |
|---|---|---:|---:|---:|---|---:|
| N_FULL_T60 | Logistic Regression | 0.243 | 0.243 | +0.000 | [0.000, 0.000] | 0/0 |
| N_FULL_T60 | Random Forest | 1.000 | 1.000 | +0.000 | [0.000, 0.000] | 0/0 |
| N_FULL_T60 | Gradient Boosting | 1.000 | 1.000 | +0.000 | [0.000, 0.000] | 0/0 |
| N_TRANSPORT_T60 | Logistic Regression | 0.243 | 0.243 | +0.000 | [0.000, 0.000] | 0/0 |
| N_TRANSPORT_T60 | Random Forest | 0.527 | 0.628 | +0.101 | [-0.006, 0.207] | 16/12 |
| N_TRANSPORT_T60 | Gradient Boosting | 0.496 | 0.504 | +0.008 | [0.000, 0.027] | 1/0 |
| N_DEGRADED_TRANSPORT_T45 | Logistic Regression | 0.243 | 0.243 | +0.000 | [0.000, 0.000] | 0/0 |
| N_DEGRADED_TRANSPORT_T45 | Random Forest | 0.263 | 0.503 | +0.241 | [0.154, 0.326] | 15/0 |
| N_DEGRADED_TRANSPORT_T45 | Gradient Boosting | 0.263 | 0.510 | +0.247 | [0.140, 0.352] | 19/4 |
| N_DEGRADED_TRANSPORT_T30 | Logistic Regression | 0.243 | 0.243 | +0.000 | [0.000, 0.000] | 0/0 |
| N_DEGRADED_TRANSPORT_T30 | Random Forest | 0.491 | 0.635 | +0.145 | [0.044, 0.244] | 17/8 |
| N_DEGRADED_TRANSPORT_T30 | Gradient Boosting | 0.388 | 0.401 | +0.014 | [0.000, 0.034] | 2/0 |
| N_DEGRADED_TRANSPORT_T15 | Logistic Regression | 0.243 | 0.243 | +0.000 | [0.000, 0.000] | 0/0 |
| N_DEGRADED_TRANSPORT_T15 | Random Forest | 0.263 | 0.461 | +0.199 | [0.117, 0.287] | 12/0 |
| N_DEGRADED_TRANSPORT_T15 | Gradient Boosting | 0.274 | 0.417 | +0.143 | [0.062, 0.234] | 11/3 |

## E-only 必須一併比較

| 模型 | 固定 E-only Macro F1 | TRANSPORT/退化條件的 EN 範圍 |
|---|---:|---|
| Logistic Regression | 0.719 | 0.243–0.243 |
| Random Forest | 0.737 | 0.461–0.635 |
| Gradient Boosting | 0.621 | 0.401–0.510 |

**全部 12 個 TRANSPORT/退化 model-condition 中，E-only 的 Macro F1 都高於 EN。**
因此，EN 相對弱化 N 的正增益不等於超過最佳單模態。原 FULL RF/GB 仍由 N 已可完全區分事件。
RF 的 TRANSPORT T60 增益 +0.101，CI 跨零；RF 的 T45/T30/T15 與 GB 的 T45/T15 有較大的描述性增益，
但沒有單調增加规律；LR 在全部條件仍無改善。CI 的條件式限制不變，不能只挑最大的一格。

## 事件家族的改對與改錯

N-FULL 各模型均無 N→EN 判斷改變。TRANSPORT T60 的 RF 共改對 16 件、改錯 12 件；
其中 Industroyer 改錯 7 件、Drift-off 改對 1／改錯 4，許多良性操作則被改對。
T45 的 RF 改對 15／改錯 0，其中 ARP-spoof DoS 7、Drift-off 4、Control-and-freeze 3、Industroyer 1。
但 T30 的 RF 又改錯 7 件 Industroyer；GB 在 T45/T15 也會改錯部分良性操作。
因此 aggregate F1 增益不能取代逐家族安全錯誤分析；完整所有家族與分母見 family report。

![Observability curve](/Users/potinglu/Documents/ICIT2027/results/exploratory-v2/figures/network_observability_curve.png)

圖：Protocol-v2 探索性結果；x 軸只比較同一 TRANSPORT 語意下的可見秒數，FULL 不混作連續退化刻度。
![Delta fusion](/Users/potinglu/Documents/ICIT2027/results/exploratory-v2/figures/delta_fusion_curve.png)

區間為 scenario×truth 分層、同 event 配對、2,000 次重抽樣的 percentile CI；全 regime 共用相同抽樣索引。
不代表獨立 simulation runs 或未見場景的不確定性，未作多重比較顯著性宣稱。

## Balanced accuracy 與錯誤方向

| 條件 | 模型 | N BA | EN BA | N FP/benign | EN FP/benign | N FN/cyber | EN FN/cyber |
|---|---|---:|---:|---:|---:|---:|---:|
| N_FULL_T60 | Logistic Regression | 0.500 | 0.500 | 0/27 | 0/27 | 57/57 | 57/57 |
| N_FULL_T60 | Random Forest | 1.000 | 1.000 | 0/27 | 0/27 | 0/57 | 0/57 |
| N_FULL_T60 | Gradient Boosting | 1.000 | 1.000 | 0/27 | 0/27 | 0/57 | 0/57 |
| N_TRANSPORT_T60 | Logistic Regression | 0.500 | 0.500 | 0/27 | 0/27 | 57/57 | 57/57 |
| N_TRANSPORT_T60 | Random Forest | 0.527 | 0.689 | 17/27 | 4/27 | 18/57 | 27/57 |
| N_TRANSPORT_T60 | Gradient Boosting | 0.498 | 0.507 | 20/27 | 20/27 | 15/57 | 14/57 |
| N_DEGRADED_TRANSPORT_T45 | Logistic Regression | 0.500 | 0.500 | 0/27 | 0/27 | 57/57 | 57/57 |
| N_DEGRADED_TRANSPORT_T45 | Random Forest | 0.509 | 0.640 | 0/27 | 0/27 | 56/57 | 41/57 |
| N_DEGRADED_TRANSPORT_T45 | Gradient Boosting | 0.509 | 0.611 | 0/27 | 3/27 | 56/57 | 38/57 |
| N_DEGRADED_TRANSPORT_T30 | Logistic Regression | 0.500 | 0.500 | 0/27 | 0/27 | 57/57 | 57/57 |
| N_DEGRADED_TRANSPORT_T30 | Random Forest | 0.492 | 0.678 | 17/27 | 6/27 | 22/57 | 24/57 |
| N_DEGRADED_TRANSPORT_T30 | Gradient Boosting | 0.398 | 0.415 | 24/27 | 24/27 | 18/57 | 16/57 |
| N_DEGRADED_TRANSPORT_T15 | Logistic Regression | 0.500 | 0.500 | 0/27 | 0/27 | 57/57 | 57/57 |
| N_DEGRADED_TRANSPORT_T15 | Random Forest | 0.509 | 0.614 | 0/27 | 0/27 | 56/57 | 44/57 |
| N_DEGRADED_TRANSPORT_T15 | Gradient Boosting | 0.499 | 0.550 | 1/27 | 3/27 | 55/57 | 45/57 |

## 分場景的 Macro F1

| 條件 | 模型 | Semiurban N / EN | Rural N / EN |
|---|---|---|---|
| N_FULL_T60 | Logistic Regression | 0.284 / 0.284 | 0.182 / 0.182 |
| N_FULL_T60 | Random Forest | 1.000 / 1.000 | 1.000 / 1.000 |
| N_FULL_T60 | Gradient Boosting | 1.000 / 1.000 | 1.000 / 1.000 |
| N_TRANSPORT_T60 | Logistic Regression | 0.284 / 0.284 | 0.182 / 0.182 |
| N_TRANSPORT_T60 | Random Forest | 0.438 / 0.642 | 0.654 / 0.562 |
| N_TRANSPORT_T60 | Gradient Boosting | 0.370 / 0.370 | 0.678 / 0.704 |
| N_DEGRADED_TRANSPORT_T45 | Logistic Regression | 0.284 / 0.284 | 0.182 / 0.182 |
| N_DEGRADED_TRANSPORT_T45 | Random Forest | 0.284 / 0.483 | 0.221 / 0.498 |
| N_DEGRADED_TRANSPORT_T45 | Gradient Boosting | 0.284 / 0.510 | 0.221 / 0.498 |
| N_DEGRADED_TRANSPORT_T30 | Logistic Regression | 0.284 / 0.284 | 0.182 / 0.182 |
| N_DEGRADED_TRANSPORT_T30 | Random Forest | 0.438 / 0.667 | 0.562 / 0.562 |
| N_DEGRADED_TRANSPORT_T30 | Gradient Boosting | 0.333 / 0.333 | 0.464 / 0.499 |
| N_DEGRADED_TRANSPORT_T15 | Logistic Regression | 0.284 / 0.284 | 0.182 / 0.182 |
| N_DEGRADED_TRANSPORT_T15 | Random Forest | 0.284 / 0.423 | 0.221 / 0.472 |
| N_DEGRADED_TRANSPORT_T15 | Gradient Boosting | 0.284 / 0.317 | 0.235 / 0.498 |

## 保留比例

| post 可見秒數 | 時間保留占完整 120 秒 | post packet retention min/median/max |
|---:|---:|---|
| 60 | 100.0% | 100.0%/100.0%/100.0% |
| 45 | 87.5% | 70.8%/74.9%/79.0% |
| 30 | 75.0% | 49.6%/50.1%/50.7% |
| 15 | 62.5% | 20.7%/24.8%/28.9% |

原始 E-only 只作一套參考；不是每個 level 重新宣稱另一份 E dataset。
被隱藏的 p IDs、全部禁止的 IEC m IDs、完整 E canonical hash 均保存在 visibility receipts；所有網路特徵從可見 p 重算。

## 判斷界線

請同時解讀每個模型、各場景、錯誤方向与非單調曲線；不以最大正 Δ 取代全部矩陣。
觀測到的電氣數值仍可能被操弄，缺失比例也可能攜帶通訊線索；E/N 共用 packet lineage，不是独立感測佐證。
本研究條件是已知起點的 event-conditioned triage，加上已知 regime 的 matched training；不是未知 onset 偵測，
也不是 full-trained 模型在突發 outage 下的部署 robustness。僅五份 recording 且家族不均，限制外推。
任何額外調整需另立版本、維持探索性標記。若要形成確認性主張，需預先註冊後用真正新的資料或獨立模擬驗證。

## 可追溯產物

- configs/protocol.v2.lock.json：新成績前的程式／設定／输入雜湊。
- results/exploratory-v2/development/：1155 個 OOF/reference predictions、24 個 Basic-only 模型與每折 training IDs。
- results/exploratory-v2/evaluation/：2772 個 predictions、全部 scenario/recording/family metrics、配對 bootstrap 與 run manifest。
- results/exploratory-v2/transitions/evaluation.json：1260 個 paired event-condition records，含 N/EN scores、改對/改錯/未變、可見性 receipt 路徑和 SHA256。
- results/exploratory-v2/features/visibility/：119 個 private receipts，保存每 level 的 visible/hidden p IDs；不是 runtime/LLM 輸入。
- docs/observability_family_results_v2.md：完整逐家族 paired transition 表。
- results/exploratory-v2/figures/：PNG 與向量 PDF。LLM 尚未實作。
