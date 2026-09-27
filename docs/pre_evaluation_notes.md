# 跨場景評估前紀錄

本階段延續作者「繼續下個階段」的指示。三項已核准研究設定完全維持：Basic 35
開發、其他 84 保留；E/N 共用 primary PCAP；固定 −60/+60 秒。

## 評分前完成的修正

- 第一版 segment 去重在 Basic test 的事件窗漏掉 4 個 APDU，涉及 packet 482004、
  482212。v2 依連線／TCP stream offset／APDU bytes 去重，保留不同內容的衝突回報。
- 全捕獲時間順序探查發現微秒級顛倒，Basic train 的一例在最後事件之後；Semiurban
  與 Rural 也有少量顛倒。v2 用固定 1 ms bounded reorder，原 timestamp/index 不改。
  超過上限仍報錯；不能因此宣稱部署時已達成相同 wall-clock 決策延遲。
- 保留原 src/sherlock/parser.py、build.py、第一輪 models/results/episodes；v2 使用
  capture_v2.py、parser_v2.py、build_v2.py 與 data/processed/v2。
- 特徵公式、模型參數、folds 和 threshold 不變；所有模型重新 fit 修正後 Basic。
- 用獨立的 APDU identity 檢查流程比較 primary captures，截到最後事件決策截止；
  報告保存於 data/manifests/segmentation_audit.v2.json。

v1 主模型 OOF 分數在修正後沒有改變。v2 消融只移除 command count 和 activation
response count，其他網路特徵仍可能含命令流量的間接影響，因此不是「所有命令證據
消失」的來源遮蔽實驗，也不能把所得差異解讀為命令的因果效果。

| 開發 OOF Macro F1，移除兩欄 | N | EN |
|---|---:|---:|
| Logistic Regression | 0.797 | 0.825 |
| Random Forest | 0.886 | 0.828 |
| Gradient Boosting | 0.857 | 0.857 |

這是根據 Basic 線索設計的診斷，未根據其成績挑選參數。正式評估將同時保留主模型
與診斷結果，不挑最好的組合作為唯一結論。

## 固定評估

configs/evaluation.v1.json 定義三模型、三視圖主比較、移除命令群組診斷、命令存在
簡單規則、分 scenario/recording/原始 family_description 結果，以及 2,000 次 paired
bootstrap。先保存 configs/evaluation.v1.lock.json 的程式、設定與已擬合模型 SHA256，
再 build held-out features、驗證 episode→feature 重算，最後載入模型直接 predict。
held-out runner 不呼叫 fit，也不挑模型／閾值。

Bootstrap 在 scenario×truth 內重抽 event，保留每一 event 的跨視圖 pairing；同一
重抽索引計算 EN−E、EN−N 的 macro F1 與 balanced accuracy 差。95% percentile CI
是條件於既有場景／類別構成的描述，不估計新模擬 run 或新場景母體的不確定性。
不作多重比較校正後的顯著性宣稱。只有兩個 held-out scenarios，不能誇大泛化。

37 項測試通過，涵蓋新的 APDU 重分段、序號 wrap、SYN reset、capture jitter、
paired resampling 與計分對照。其餘既有來源／時限／洩漏／補值測試保留。
