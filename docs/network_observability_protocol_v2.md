# Network Observability Protocol v2 — 探索性提案，待作者核准

狀態：**exploratory / post-confirmatory / Protocol v2；尚未實作新 regimes，尚未訓練或評分新模型。**
本提案依附件第 25–26 節先完成稽核與可審閱規格。既有 v1 實驗不改寫。
先前的 `pipeline-v2` 是 v1 評估前的解析修正，與本次研究假設的 **Protocol v2** 不同。

## A. 已核對的既有狀態

原評估 84 事件（57 CYBER／27 BENIGN）；LR E/N/EN Macro F1 為 0.719/0.243/0.243，
RF 為 0.737/1.000/1.000，GB 為 0.621/1.000/1.000。三模型的 N/EN 二元判斷均未改變。
這是原凍結設計下有效的無增益結果。RF 的兩欄命令消融為 N 0.609、EN 0.801、
差約 0.192、條件式 paired CI 約 [0.091,0.297]；它保持診斷地位，不改列主結果。

已讀七份指定文件、原 configs、來源 manifests、feature rows、predictions、metrics、
bootstrap、模型 metadata 與 locks，並核對原評估鎖定的 68 個檔案與 scoring artifacts。
歷史文件中「尚未評估」段落是較早里程碑，以 heldout_results.md 與 run manifest 為最新狀態。
舊 configs/locks/models/results/episodes 不覆寫；新 audit 另存 exploratory-v2。

## B–C. 逐項 N 欄位與資訊路徑

FULL 全部保留。TRANSPORT 的判準是運算只依賴 IP/TCP header、長度、capture time，
而不是「與命令完全無關」。觀測到的 transport 行為可以間接反映命令，但不解碼其語意。

| 現有 N 欄位 | 原始來源／層級／parent | 語意 | FULL | TRANSPORT | 間接線索與決策理由 |
|---|---|---|---|---|---|
| post log rate | PCAP→IEC message APDU→count，application framing；全部 post m IDs→p IDs | 每秒不同 APDU 數的 log1p | 保留 | **原欄排除，另建 TCP packet rate** | 雖未讀 ASDU/COT，仍需 IEC framing、APDU 去重，且命令/回應增加消息量。不是 payload-blind packet rate。 |
| log rate change | pre/post APDU m IDs→p IDs | APDU rate 差 | 保留 | **原欄排除，另建 packet rate change** | 繼承 application framing，可能反映程序排程及錄製流量規模。 |
| command log count | ASDU type 45..51 + COT=6；m IDs→p IDs | activation command | 保留 | 排除 | 直接 IEC 命令語意；不可換成其他命名繼續輸入。 |
| activation response log count | ASDU type 45..51 + COT=7；m IDs→p IDs | activation response，非執行真值 | 保留 | 排除 | 直接 IEC cause 語意；不等同 TCP ACK。 |
| RST log count | TCP flags RST，port 2404；p IDs | 連線重設封包數 | 保留 | 保留 | 普通 transport 行為，也可能與攻擊脚本或重連排程相關。 |
| post max gap fraction | post APDU timestamps + scope 邊界；m IDs→p IDs | IEC message 間隔 | 保留 | **原欄排除，另建 TCP packet gap** | application-message 時序與普通 packet 時序不同；不可直接留舊欄。 |
| U-format log count | IEC APCI format；m IDs→p IDs | IEC U-frame 活動 | 保留 | **排除，請作者核准此明確選擇** | 不是 TCP flag，須辨識 IEC 控制格式。其測試／啟停／重連活動也可能成為程序線索。 |
| endpoint log count | IPv4 endpoints + TCP port；p IDs | post 可見 IP 端點數 | 保留 | 保留 | 是 transport 可見量，但 Basic 固定約 33 endpoints、其他場景較多，可能反映 topology/recording。只用數量，不用識別字串。 |

Packet size 可以合法屬 transport，但常反映消息格式。本輪最小集**不納入**，理由是
維持小樣本與可解釋的 5 欄集合，不是已證明它洩漏標籤；亦未按分類成績挑選。
Timing/rates/endpoint counts 的間接關聯不稱 forbidden-data leakage。
沒有證據顯示上述可見欄位讀取了 G；命令規則的高分稱 dataset/procedural shortcut。

## D. 精確 N-TRANSPORT 提案：5 欄

輸入為同一 primary vantage、TCP、src 或 dst port=2404 的 **packet header projection**。
Port 是固定 service scope，不是解碼出的 ASDU。包括 ACK、重傳與握手封包；不做 APDU
去重、不按 IEC message type 篩選、不讀 payload。禁止讀取 source_type=message/process。
既有 episode 保留了所需 p records；新的 extractor 應能只用 p records 執行，不依賴
ASDU/COT/APCI parser 的成功與否。必要時從 capture_v2 的 Ethernet/IP/TCP reader 建立
projection；不透過 process/mapping 選封包或端點。現有 packet roots 已先於 IEC decode
建立，本次資料均成功解碼，但未來 transport parser 不應被 IEC parse failure 阻擋。

完整觀測時 pre=[t0−60,t0)、post=[t0,t0+60)，p 時間仍為原 capture time。
令 Ppre/Ppost 為各半窗的可見 TCP/2404 packet 數，T 為已知 post 可見秒數：

| 新欄位 | 精確公式 |
|---|---|
| nt_post_log_packet_rate | log1p(Ppost / T) |
| nt_log_packet_rate_change | log1p(Ppost / T) − log1p(Ppre / 60) |
| nt_rst_log_count | log1p(post 中 RST bit set 的 p record 數) |
| nt_post_max_packet_gap_fraction | 可見 post packet timestamps 加 t0、t0+T 邊界的最大相鄰差／T |
| nt_endpoint_log_count | log1p(post 中不同 opaque IP endpoint 數) |

完整可見但零 packet 是真實零量／gap=1；不可見區間是 unknown，不填成零流量。
本輪 T>0，若後續加入全 outage，須另定全缺失政策，不從 None 推論通訊正常。
不使用 raw IP、絕對時間、scenario/recording、事件標籤、電氣 payload、ASDU/COT/U-format。
「encrypted/unsupported protocol」只作分析能力受限的近似：不是重新產生加密流量，
也不宣稱加密前後封包大小／時間必定不變。E 是另一個獲授權的解碼表示，故 E+TRANSPORT
不能稱單一無解密能力感測器卻能憑空取得 E；是同源、不同分析出口可見性的實驗。

## E. N-DEGRADED：建議主設計與共享來源界線

**建議主設計：N-TRANSPORT 分析出口在 post 視窗中途停止提供資料；E 分析出口仍可用。**
這是 network-view/export outage，不是 primary PCAP capture outage，也不是網路真的停止通訊。

提出固定 T={60,45,30,15} 秒，保留完整 pre 60 秒；post N 只可見 [t0,t0+T)。
60 是完整基準；45/30/15 是等距的 15 秒故障起點，覆蓋中度至嚴重的尾段不可用，
且 15 秒在每個現有事件均有可見封包（Basic/Semiurban/Rural 最少 164/781/442 個）。
這只驗證技術可行性，沒有計算這些條件的分類成績。選擇尾段 outage 表示 exporter
在觀測期間故障；不移動故障位置去找到最能抹掉命令或提升 EN 的區間。
本輪不做随机 packet loss、全 outage 或多個時間位置搜尋。

這是 post 時長 100/75/50/25% 可用，不是整個 120 秒視窗或 packet 數遺失相同比例；
整窗時間可用比例分別 100/87.5/75/62.5%。實際 packet retention 另行記錄。
rate 用實際可見 T 當分母，gap 只在可見區間計算，避免把 exporter 故障製造成
「網路異常沉默」訊號。比較固定在 t0+60 決策；E 仍可見完整 −60/+60 秒。

**Lineage 實作要求（尚未實作）：**

1. canonical 原始證據庫不改寫；網路出口遮蔽集合是區間內 p record 的 **N access**。
2. 在 network projection 內封鎖這些 p 及全部可達 N descendants；所有 N aggregates
   從剩下的可見 p 重算，不能保留原 full-rate/full-gap/endpoint caches。
3. canonical E 的 private parents 還存在；E+N 視圖只展示 E 量測與可見 N。這不叫
   全域 raw-source removal。不能直接把現有 remove_sources 用於 canonical episode
   後再偷偷保留 E。需新的明確 view-specific visibility API／proof receipt。
4. 若**真的移除原始 p source**，必須用全域 lineage-closed removal，連 E 也刪除並重算。
   這是另一個 shared-source-loss 實驗：E-only 也會隨 level 變，不併入本輪 E 固定的曲線。
   建議本輪暫不執行這個第二機制；作者可選它，但需另核准矩陣。
5. degraded N 與 EN 對同一 event 使用完全相同 mask。Mask 只由 t0、T 決定，與 y、
   family、attack_point、end/recovery 無關。記錄 parent IDs、可見區間與重算 recipe。

跨層規則：LLM 未實作。將來只能收到同一 regime 的 projection；不能順著 E 的
parent_ids 取回被禁止的 IEC headers。private verifier 可核對來源，回傳有範圍的驗證
receipt，不能在解釋或工具回覆中洩回隱藏內容。metadata/lineage IDs 不當 classifier X。

## F. E 保持原契約；先稽核再考慮新增

10 個 E 欄位保持不變。四類 numeric change 與五個 missing fraction 在 119 事件皆有值；
state changed fraction 在全部 119 事件缺失，因沒有任何 state channel 同時有效觀察於
pre/post。不能把缺失寫成「沒有狀態變化」，也不能用初始值補前值。

現有四類 numeric coverage 足以先研究網路可觀測性改變；不足以代表完整物理行為。
缺失比例可能反映通訊而非獨立物理證據，最大值聚合可能偏向大型場景／少數極端值。
詳細 class/family/coverage 稽核與待議候選見 electrical_feature_audit_v2.md。
建議本輪 **不新增 E**，避免同時改動兩個因素。候選只列提案，不實作。

## G. 提議的完整矩陣與評分

| 網路條件 | N 欄位數 | E-only | N-only vs EN |
|---|---:|---|---|
| N-FULL，T=60 | 8 | 同一個固定 E(10) 參考 | 既有 v1 結果重現／引用，不稱新盲測 |
| N-TRANSPORT，T=60 | 5 | 同上，不另造資料集 | 5 vs 15 欄 |
| N-DEGRADED-TRANSPORT，T=45 | 5 | 同上 | 5 vs 15 欄 |
| N-DEGRADED-TRANSPORT，T=30 | 5 | 同上 | 5 vs 15 欄 |
| N-DEGRADED-TRANSPORT，T=15 | 5 | 同上 | 5 vs 15 欄 |

每列 LR/RF/GB 同一 classifier 成對比較；沿用 models.v1 的參數、seed=20270921、
threshold=0.5、Basic 35 開發與原五折，之後 fit Basic 35，對已觀察過的其他 84 事件做
探索性比較。每 regime 在 Basic 也施加相同可見性，imputer/scaler 只 fit 該 training fold。
這測量「已知 regime 下的可達效能」，不是 full-trained 模型遭遇突發 outage 的 robustness。
後者若研究，須另立 train-full/test-degraded 矩陣，不混淆。

3×(1 個 E + 5 組 N/EN)=33 個 model/view 條件，其中 9 個為原 E/FULL 參考，24 個新條件。
不挑最佳 regime／model。主量為 ΔFusion=MacroF1(EN)−MacroF1(N)，同時列 N/EN 分數、
balanced accuracy、FP/benign、FN/cyber。沿用 scenario×truth 分層的 2,000 次 paired
事件 bootstrap，固定 seed，所有 views/levels 同一重抽索引；CI 只作這些已觀察場景的
條件式描述，不當 family 少數事件的精確推論或因果效果。

按原始 family_description、recording、scenario 列 N/EN 正確數、corrected_N、hurt_N、
unchanged（再分 both-correct/both-wrong）。每個預測改變都存 episode ID、scores、
visibility、可見／被遮蔽 evidence IDs 與來源雜湊。保留原 Seperator/Separator 拼字差異，
不按結果合併家族。Curve 只在同一 TRANSPORT 語意下以 T 為 x 軸，N/EN 分線；
FULL 對 TRANSPORT 是類別比較，不畫成等距物理退化比例。非單調結果照實報告。

## H. 研究風險

- 新假設受既有結果啟發，84 事件重用；全部新結論標 exploratory/post-confirmatory。
- 命令規則可見且合法，但過度吻合 dataset procedure；不可外推「沒命令就是攻擊」。
- E/N 共用 packet lineage，互補表示不等於獨立感測佐證；表示缺失不等於原始來源缺失。
- 全部僅 5 recordings；Basic cyber 僅一份，event bootstrap 不估計新模擬 run 的不確定性。
- 家族不均且部分 benign family 只有一件；保留 counts，避免只報整體平均。
- traffic rate、endpoint count、缺失分母與 max aggregation 受場景規模影響，LR 已顯示偏移風險。
- 電氣回報可被操弄，不是 simulator truth；缺失、零值與未改變有不同語意。
- 時間尾段遮蔽相對已知 event start 定義，是 controlled event-conditioned study，非真實故障率模型。
- E 固定的出口故障實驗需要分開分析出口的操作假設；資料並未證明部署現場有獨立 E 來源。
- 候選 E 閾值不能從已見 84 事件的 labels 設計；若後續調整僅 Basic 開發並保持探索性標記。

## I. 新檔案與 gate

本輪建立（審閱／描述性 audit，非新實驗）：

- docs/network_observability_protocol_v2.md
- docs/electrical_feature_audit_v2.md
- docs/network_shortcut_analysis_v2.md
- docs/network_distribution_shift_v2.md
- docs/paper_positioning_v2.md
- configs/network_observability.v2.json、configs/features.v2.json、configs/evaluation.v2.json（全為 proposed，execution_enabled=false）
- scripts/audit_observability_v2.py
- results/exploratory-v2/audit/（舊資料的新描述性統計、來源雜湊、不可變檢查）

作者核准後才建立／執行：

- configs/protocol.v2.lock.json（現在不建立，以免冒稱凍結）
- src/features/network_transport_v2.py
- src/evidence/observability_v2.py
- experiments/run_observability_v2.py
- tests/test_observability_v2.py
- results/exploratory-v2/development/、evaluation/、transitions/、figures/

待核准六項：FULL=原 8 欄；TRANSPORT=上述 5 欄且排除 U；DEGRADED=僅 N 出口尾段
不可用 T=60/45/30/15、E 固定；本輪不新增 E；上述三模型矩陣；上述新命名／版本。
附件第 26 節明訂：**“Do not run Protocol-v2 models yet. Wait for author approval.”**
因此本輪在可審閱提案完成後停止，等待作者對具體設定的核准；沒有跑新模型。
