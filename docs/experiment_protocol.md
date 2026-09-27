# 第一版研究協議 — 三項設定已於 2026-09-21 核准凍結

## 凍結是什麼

凍結就是在看保留測試成績之前，把「資料怎麼用、事件怎麼分、怎麼評分」定案，
保存版本與雜湊。不是永遠不能改；改動要有新版與理由，不能看到測試結果後調整
規則，再把相同資料的成績當成完全未見測試。

證據契約決定哪些欄位屬 E/N/M/G、可見性、單位、缺失與來源要求。
實驗切分決定哪些事件用於開發，哪些留給最終評估。模型種類／特徵公式／閾值
也要在第一次 held-out evaluation 前固定。

## 已由本地資料支持的事實

- Basic 有 35 個標註事件：18 cyber、17 benign；其中官方 train 只有 7 個 benign。
- Semiurban 有 48 個事件：29 cyber、19 benign；Rural 有 36 個：28 cyber、8 benign。
- 所有事件已逐一核對原始 procedure 標註，沒有未解決類別。
- 5 份 recording、119 個事件不是 216,028 個獨立 state samples。
- 現成 state 混入初始化、網路 test 欄與設定／量測別名，不直接作為 E-only。

## 已凍結的 split

| 用途 | Recording | 事件數 | 可以做什麼 |
|---|---|---:|---|
| Development | Basic train + Basic test | 35（18 cyber／17 benign） | feature design、training-only preprocessing、模型／閾值選擇；後續 prompt／verification 開發 |
| Held-out | Semiurban train | 9（全 benign） | 最後報告良性操作 false cyber attribution；不得用於調參 |
| Held-out | Semiurban test | 39（29 cyber／10 benign） | 最後跨場景評估 |
| Held-out | Rural test | 36（28 cyber／8 benign） | 最後跨場景評估 |

因此開發 35、保留 84，合計 119。`configs/split.v1.json` 已列出每個
opaque event ID 的歸屬、固定 seed=20270921 與固定五折分配。Truth／原始檔案
對照僅在 `data/evaluator/event_catalog.json`。ID 不得作為模型欄位。

保留的 Semiurban train 是原資料集的檔名，不代表本研究可用它訓練。
整個 Basic 作為 development 符合 scenario-level 開發設計；必須在論文明說它
包含官方 test，不能稱為沿用官方監督式 train/test split。

### 開發集內部驗證

採按事件類別分層的五折，E/N/EN 共用相同 folds；同事件的視窗、資產資料、
問答及其衍生資料全部同組。若後續增加有共同 parent 的 episode，須先合併 group。
每個 fold 的 imputer、scaler、feature selection 與模型僅在 fold train 擬合。
初始 classifier 建議 regularized Logistic Regression，避免小樣本大量搜尋。

五折只估計 Basic 內事件變動，不證明跨獨立 simulation run 泛化。Basic 的 cyber
只在一個 recording，不能做每個驗證 fold 都有兩類的 leave-one-recording-out。

## 已凍結的事件範圍與觀測點

- 起點 t0 使用 evaluator 已核對的 event start；因此明示為 event-conditioned triage。
- 固定 `[t0−60s, t0+60s)`，前 60 秒供 baseline，於 t0+60s 輸出判斷。
- 60 秒是已核准的固定決策延遲，不是根據測試成績最佳化的參數。所有事件使用同一設定。
- 不使用 gold end/recovery 裁窗，不使用 attack_point 選資產，不增加大量背景視窗充作 benign 事件。
- 使用全部可見、已映射的資產，主觀測點固定 Basic n302／Semiurban n406／Rural n402。
- 所有時間用 PCAP capture time／Unix 秒；不使用 14 倍模擬時間換算。
- 已檢查這個固定窗在五個 recording 都沒有彼此重疊；不根據 held-out 調整視窗。

這個觀測窗可能包含事件中的恢復動作；它們仍屬原事件的觀測，不另行分成獨立
benign 事件。若研究者要研究 recovery triage，應另定標籤政策及實驗。

## 保留資料的接觸紀錄

本輪僅作資料可用性／schema／標籤一致性／品質稽核，沒有計算分類成績、搜尋
閾值或比較 label-conditioned feature performance。報告公開已檢查的場景與內容，
不宣稱保留檔案從未被開啟。之後不以保留資料擬合任何模型或前處理。

## 評估與研究界線

RQ1：同一 classifier，matched E-only／N-only／E+N。按 scenario、recording、
event family 分列；整體分數不能代替分列結果。至少保存 confusion matrix、
class counts、precision／recall／F1／macro F1／balanced accuracy，並報告
BENIGN→CYBER 與 CYBER→BENIGN 的分子／分母。AUROC／AUPRC 只在有兩類且
有適用 score 的分組計算；對全 benign 的 Semiurban train 標記不適用。

依 brief 做固定 seed 的 paired event-cluster bootstrap 2,000 次，保留 pairing；
不能把同事件多個問題或 LLM 重跑當成新單位。少數固定模擬場景的相依性會限制
CI 與泛化解讀。沒有假設 fusion 一定勝出，也不宣稱真實半導體場域或因果驗證。

Layer 1 仍為 CYBER_RELATED／BENIGN_OPERATIONAL 二分類。
INSUFFICIENT_EVIDENCE 是後續 Layer 3 的證據充分性結果；sufficiency gold 必須
另有明確 annotation policy，不能用分類錯誤或 verifier 自己輸出反過來定義真值。

## 核准與執行紀錄

使用者已明確同意三項設定：Basic 35／其他 84、共用 primary PCAP 的 E/N、
固定 −60/+60 秒。正式契約為 `configs/evidence_contract.v1.json`，切分為
`configs/split.v1.json`，`configs/protocol.v1.lock.json` 保存 SHA256 與核准紀錄。
原 proposed 檔與 Phase 1 audit manifest 保留作歷史，不改寫既有稽核雜湊。

第一版特徵／模型實作詳見 `docs/feature_spec.md`、`configs/features.v1.json`、
`configs/models.v1.json`。模型採規格列出的 LR、RF、Gradient Boosting，同組 folds
與 threshold=0.5，不做參數搜尋；不依 held-out 成績選最佳模型。
這些是 implementation choices，不冒稱使用者另行核准了每個模型參數。

本階段只跑 35 個 Basic 事件的 OOF 開發比較及全 Basic 模型擬合；84 個 held-out
仍由 runner gate 阻擋。下一個里程碑是完成研究實驗的 pre-evaluation lock，接上
分場景／分 recording／分家族評分與 paired bootstrap，再作一次正式保留評估。
開發 OOF 分數不當成跨場景結論。之後才開始 explanation/verifier。

## 正式評估完成

後續階段已完成 pipeline-v2 品質修正、開發消融、37 項測試與 pre-evaluation lock，
並對全部 84 held-out 完成一次評估。三項核准設定未更動。結果、CI、限制與
接觸紀錄見 `docs/heldout_results.md`、`docs/pre_evaluation_notes.md`；
原本僅開發的段落為歷史里程碑，後續不得再聲稱尚未接觸 held-out 成績。
