# 開發基線完成紀錄 — 2026-09-21

三項設定已依使用者同意保存為 v1；Basic 35 事件已完成證據重建與三模型 × 三視圖五折 OOF。
**84 個 held-out 尚未重建／預測／評分。以下是開發結果，不是正式跨場景實驗。**

## 產物與驗證

- 原始 Basic ZIP SHA256 已再次核對。重建 35 episodes、189,358 筆 packet/message/process 證據。
- 第一版為 10 個 E、8 個 N 特徵；所有 event 的 state changed fraction 皆因未同時觀察到前後狀態而缺失，未冒充零變化。
- 31 項測試通過，涵蓋 parser quality、命令 payload 隔離、mapping 去敏、opaque IDs、時限／來源／schema、來源移除後重算、train-only preprocessing 與 LR log-odds 加總。
- 在第一次擬合之前保存 `results/development-v1/implementation.lock.json`，記錄 src、tests、experiment、feature/model config 及 requirements SHA256。執行結束再次核對程式未改動。
- 保存 315 筆 OOF 預測（35×3×3）、9 份僅 fit Basic 的模型、詳細分 recording／原始 description 結果與 run manifest。
- 無參數搜尋；score 未校準。開發 runner 明確阻擋 held-out。

## OOF Macro F1

| 模型 | E-only | N-only | E+N |
|---|---:|---:|---:|
| logistic_regression | 0.658 | 1.000 | 1.000 |
| random_forest | 0.770 | 1.000 | 1.000 |
| gradient_boosting | 0.627 | 1.000 | 1.000 |

這些分數是完整 35 個 OOF predictions 合併計算，並非 training accuracy。

## 解讀與下一步

開發集 17 個 BENIGN 事件都在 post 視窗觀察到 1–4 個 activation commands 與相同數目的 activation responses；
18 個 CYBER 事件兩者均為零。這是由 PCAP headers 取得的可見訊號，但可能反映資料集程序設計，
不是所有資安事件在真實場域都會沒有命令。N-only 已飽和，因此本輪沒有呈現 E+N 相對 N 的增益。
不能挑 E-only 較低的結果來宣稱已證明 evidence fusion；也不能把同 recording 事件當獨立 simulation runs。

下一個里程碑依序為：

1. 在 Basic 開發集做命令／activation-response 群組移除的診斷與人工事件核對，保存為額外 ablation，不覆寫此次主基線或依 held-out 調整。
2. 覆核不同 TCP segmentation 是否重複計算相同 APDU；目前是 captured-observation decoder，保留衝突數值且不重建接收端採用值。
3. 完成正式評估 runner、分場景／分 recording／分家族報告、2,000 次 paired event bootstrap，保存 pre-evaluation lock。
4. 對 84 held-out 執行一次跨場景比較。若仍無融合增益，忠實呈現並在開發集檢討研究假設。
5. 在 Layer 1 與 evidence contract 穩定後進入 LLM explanation、deterministic verifier 和 sufficiency gold。

本輪尚未實作 held-out scorer、bootstrap、LLM 或完整 verifier；也沒有真實場域驗證。

## 可重現入口

```sh
UV_CACHE_DIR=.cache/uv uv pip sync --python .venv/bin/python requirements.lock
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/bin/python -m sherlock.build --partition development
.venv/bin/python experiments/run_development.py
```

最後一行若已存在完成的 results/development-v1/metrics.json 會拒絕覆寫；若在獨立乾淨副本重現，
需保留 frozen configs、相同原始資料與 requirements。此目錄未初始化 Git，以程式雜湊代替 commit ID。
