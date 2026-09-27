# 第一輪跨場景保留評估

84 個保留事件已依評分前雜湊鎖完成評估：Semiurban 48、Rural 36，共 57 CYBER、27 BENIGN。
主模型、兩欄命令消融及命令存在規則全部保留。所有模型只在修正後 Basic 35 擬合；
保留評估僅載入模型 predict，沒有調參／補值擬合／模型選擇。

## 主比較：整體 Macro F1

| 模型 | E-only | N-only | E+N | EN−N 的 95% paired bootstrap CI |
|---|---:|---:|---:|---|
| logistic_regression | 0.719 | 0.243 | 0.243 | [0.000, 0.000] |
| random_forest | 0.737 | 1.000 | 1.000 | [0.000, 0.000] |
| gradient_boosting | 0.621 | 1.000 | 1.000 | [0.000, 0.000] |

CI 為 2,000 次 scenario×truth 分層、event 配對重抽的 percentile 區間。
它條件於本資料的場景／類別構成，不代表跨獨立 simulation run、場景母體或真實工廠的不確定性；
不作多重比較校正後的顯著性宣稱。

## 分場景 Macro F1

| 場景 | 模型 | E | N | EN |
|---|---|---:|---:|---:|
| 02-Semiurban | logistic_regression | 0.700 | 0.284 | 0.284 |
| 02-Semiurban | random_forest | 0.728 | 1.000 | 1.000 |
| 02-Semiurban | gradient_boosting | 0.600 | 1.000 | 1.000 |
| 03-Rural | logistic_regression | 0.734 | 0.182 | 0.182 |
| 03-Rural | random_forest | 0.723 | 1.000 | 1.000 |
| 03-Rural | gradient_boosting | 0.630 | 1.000 | 1.000 |

## Recording 層級錯誤

FP 為 BENIGN→CYBER；FN 為 CYBER→BENIGN。下表使用事件數的分子／分母。

| Recording | 模型 | N FP | EN FP | N FN | EN FN |
|---|---|---:|---:|---:|---:|
| 02-Semiurban/train | logistic_regression | 0/9 | 0/9 | 0/0 | 0/0 |
| 02-Semiurban/train | random_forest | 0/9 | 0/9 | 0/0 | 0/0 |
| 02-Semiurban/train | gradient_boosting | 0/9 | 0/9 | 0/0 | 0/0 |
| 02-Semiurban/test | logistic_regression | 0/10 | 0/10 | 29/29 | 29/29 |
| 02-Semiurban/test | random_forest | 0/10 | 0/10 | 0/29 | 0/29 |
| 02-Semiurban/test | gradient_boosting | 0/10 | 0/10 | 0/29 | 0/29 |
| 03-Rural/test | logistic_regression | 0/8 | 0/8 | 28/28 | 28/28 |
| 03-Rural/test | random_forest | 0/8 | 0/8 | 0/28 | 0/28 |
| 03-Rural/test | gradient_boosting | 0/8 | 0/8 | 0/28 | 0/28 |

Semiurban/train 只有 9 個良性事件；其雙類 Macro F1、balanced accuracy、AUROC/AUPRC 不適用，
JSON 明確記錄 null。完整 E-only、所有 recording 及原始 event-family 分組見 metrics.json。

## 診斷：移除 command／activation-response 兩欄

| 模型 | N | EN | EN−N 的 95% CI |
|---|---:|---:|---|
| logistic_regression | 0.243 | 0.243 | [0.000, 0.000] |
| random_forest | 0.609 | 0.801 | [0.091, 0.297] |
| gradient_boosting | 0.649 | 0.649 | [0.000, 0.000] |

簡單命令存在規則的 Macro F1=1.000，FP=0/27，FN=0/57。
此規則在 Basic 診斷後、保留評估前明訂。兩欄消融仍保留 rates/gaps 等間接命令流量訊號，
不能視為原始命令來源完全遮蔽，也不能當因果效果。消融／規則不是主比較的替代結果。

## 證據、版本與執行

- 保留集重建 84 episodes、2,917,282 筆 evidence records；每筆 episode 均驗證雜湊及 feature 重算。
- 原始三項協議雜湊保持不變。pipeline-v2 修正 TCP regrouping duplicate 與微秒級捕獲排序；v1 舊產物未覆寫。
- 37 項測試通過；5 份 primary captures 的 APDU 去重參照覆核通過。
- 評分前鎖：configs/evaluation.v1.lock.json；模型：results/development-v2/models 與 results/ablation-development-v2/models。
- 評分開始與完成紀錄：results/heldout-v1/started.json、run_manifest.json。
- 預測：results/heldout-v1/predictions.json；計分：metrics.json；CI：paired_bootstrap.json。
- 原始 family_description 僅供 evaluator 分組；不進 classifier X。數值分數未校準。
- 本次評估已接觸保留成績；後續依此調整的特徵／規則必須標記探索性，不能再稱同批資料完全未見。

## 研究解讀與後續

本輪主比較沒有出現 EN 相對 N 的整體 Macro F1 增益，不能宣稱已證明 evidence fusion 優於網路單模態。
三個主模型的 N 與 EN 在 84 個事件上的二元判斷完全相同（score 可以不同），所以 EN−N 的配對 F1 CI 在本樣本退化為 [0,0]；這不保證未來資料也無差異。
LR 的 N/EN 漏掉全部 57 個 CYBER。事後描述性診斷顯示，post log-rate 在 Basic 為 1.972–2.182，保留集為 2.908–4.302；
LR N 在保留集的該欄平均 log-odds 貢獻為 −17.347，顯著壓低 CYBER 分數。這支持流量規模分布偏移的解釋，
並非根據此結果重訓或重新正規化。完整加性貢獻與欄位範圍見 posthoc_diagnostics.json；不是物理因果結論。
移除命令兩欄後，只有 RF 的融合有明顯描述性改善（0.609→0.801），LR/GB 沒有改善；不以此診斷取代未改善的主比較。
事件起點來自已核對標註，所以這是 event-conditioned triage，並非連續流量中的端到端事件偵測。
開發 cyber 只來自一份 Basic recording；同樣的程序和命令生成模式可能跨場景延續。
觀測回報不是獨立物理真值；capture ordering 的離線整理不證明線上延遲。

下一階段先整理主模型的錯誤與融合是否改變判斷，確認 Layer 1 的可支持研究主張；
再建立 deterministic verifier 的可測規則與 evidence sufficiency annotation policy，最後接 LLM 解釋。
LLM/verifier 尚未實作，不把分類成功當作證據充分性或解釋忠實度的證明。
