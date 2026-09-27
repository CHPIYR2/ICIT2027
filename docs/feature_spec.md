# 第一版特徵與開發基線

更新：特徵公式保留。正式評估使用 pipeline-v2 的 APDU byte-range 去重與固定 1 ms
捕獲排序，取代本文原 segment-only 政策；見 `configs/pipeline.v2.json`。
84 個保留事件現已完成一次評估，見 `docs/heldout_results.md`。下文保留開發時紀錄。

三項研究協議已由作者核准並凍結。以下是第一版實作選擇，保存於
`configs/features.v1.json`、`configs/models.v1.json`；第一次模型擬合之前另保存
程式與測試的 SHA256 snapshot。沒有使用 held-out 成績設計特徵或參數。

## 輸入與來源

- E/N 共用 primary control-center PCAP，每事件固定 `[t0−60,t0+60)`。
- E 只收 mapping 的 MEASUREMENT、allowlist attribute、正確 unit，且來自
  IEC104 monitoring type 1/13；type 45/47/50 命令不提供 E payload。
- M 只保留 opaque asset/channel、family、attribute、context、unit、scale。
  BASE/NONE 保持原值，沒有未驗證的倍率換算或初始值填入。
- 只解析完整存在於捕獲 segment 的 APDU；partial APDU 或 IP fragment 明確報錯。
- 原始 packet header → message header → process observation 都保存 parent IDs。
  原始路徑 resolver 在 `data/manifests/development_source_resolver.json`，不进入 X。
  episode gzip SHA256 加上提取程式／recipe hash 支援每筆 feature row 重算。
- 原始封包 ID 可按 source resolver 指定 archive/member 重新掃描 packet_index，
  依 `source_id|packet_index` 的 SHA256 重建；APDU/object offset 再決定子 ID。

## TCP 回報歧義

Basic 開發重建期間發現同方向連線、相同 TCP 起始序號存在不同內容，甚至不同長度。
因此第一版定位為 **捕獲回報的觀測摘要**，不是 TCP 接收端狀態重建。
同 sequence/end/bytes 的精確重傳只建立一次 message/process observation；不同
內容保留，原始 packet headers 都保留。私有 build audit 另計數衝突。

不假設 first-seen 或 later-seen bytes 比較可信；不根據事件標籤選擇哪份數值。
也不因存在衝突就刪掉所有回報，避免預先替模型判定真偽。特徵只按協定 quality
flags 排除不合格量測。不同 segmentation 的語意級 duplicate detection 尚未實作，
不能將此 decoder 泛稱完整 TCP reassembler；正式跨場景評估前須再核對這项限制。

## 10 個 E 特徵

前半窗為 pre，後半窗為 post。每 channel 的 numeric 摘要只使用 quality flags
為空且 value 有限的實際觀測；沒有觀測即為缺失，不從窗外或未來回填。

| 特徵群 | 個數 | 公式與缺失 |
|---|---:|---|
| relative change | 4 | voltage/current/active_power/reactive_power 各一個。每 channel 算 `abs(mean(post)−mean(pre))/max(abs(mean(pre)),floor)`，再取該 family 最大值；無 channel 同時有 pre/post 則 None。 |
| post missing fraction | 5 | 以上四類加 reported_state。沒有任何有效 post 觀測的 channel 數／該 family 靜態 eligible mapping channel 數；分母零則 None。 |
| state changed fraction | 1 | reported_state 中同時有有效 pre/post 的 channel，比較最後一次 pre/post 回報是否不同；分母零則 None。 |

數值 floor：voltage 0.01 pu、current 1 A、active_power 1000 W、reactive_power
1000 Var。這是避免 baseline 接近零的固定數值尺度，不是安全操作門檻。
不同單位不直接加總。保留缺失比例可能包含通訊排程／場景結構訊號，須在論文揭露。

## 8 個 N 特徵

以下皆排除 process/setpoint payload values；N 的消息數表示捕獲到的不同回報，
不保證接收端接受或執行。

| 特徵 | 定義 |
|---|---|
| post log rate | log1p(post IEC APDU 數／60) |
| log rate change | log1p(post 數／60)−log1p(pre 數／60) |
| command log count | log1p(post ASDU 45..51 且 COT=6 數) |
| activation response log count | log1p(post ASDU 45..51 且 COT=7 數)；不等於 positive confirmation 或已執行 |
| RST log count | log1p(post TCP port 2404 的 RST packet 數) |
| post max gap fraction | post APDU timestamps 加 t0/t0+60 邊界，最大相鄰差／60；無消息則 1 |
| U log count | log1p(post U-format APDU 數) |
| endpoint log count | log1p(post TCP port 2404 中不同 IP endpoint 數)；不使用 endpoint 身分作 predictor |

## 模型與驗證

LR、RF、Gradient Boosting 共用 E(10)、N(8)、EN(18) 與 frozen 五折。
全部參數見 `configs/models.v1.json`；固定 threshold=0.5、seed=20270921，無搜尋。
每個 fold 獨立擬合 median imputer（keep_empty_features）、全欄 missing indicators、
StandardScaler，再 fit classifier。全 training fold 缺失欄位的數值零只存在 estimator
內部，不回写 evidence；validation 不影響 median/scaler。增加全欄 missing indicator
使測試時首次缺失仍可表示，但模型未必曾學到它的影響。

每個 episode 只以對應 validation fold 的模型產生一次 OOF prediction。
輸出保存 confusion matrix、macro F1、balanced accuracy、AUROC/AUPRC、兩種錯誤率，
以及 recording／原始 event description 分組（description 僅 evaluator 使用）。
單類分組的 macro F1、balanced accuracy、AUROC/AUPRC 標 None，不當雙類成績。
LR 額外保存各轉換欄位的 coefficient×scaled-value 與 intercept；總和等於 log odds，
這是模型加性貢獻，不是因果效果。score 未校準。

## 範圍與下一個關卡

本輪僅是 Basic 35 的開發基線；final models 也只 fit Basic 35。
開發內 cyber 都來自一份 recording，OOF 仍可能學到該 recording 的特性。
不以高分宣稱跨場景泛化，不以不同視圖最佳分數挑選論文結論。

84 held-out 未重建特徵／未預測。正式實驗仍須完成 frozen evaluation runner、
同事件配對 bootstrap、分場景報告及 decoder segmentation 覆核，保存 pre-evaluation
lock 後才執行。LLM explanation/verifier、證據充分性 gold 尚未實作。
