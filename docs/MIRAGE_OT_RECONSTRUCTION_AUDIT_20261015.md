# MIRAGE-OT Incident Reconstruction Engine — 原始程式與實驗稽核

審查基礎：使用者提供的 `MIRAGE_OT_RECONSTRUCTION_REVIEW.zip`，不修改原 ZIP；於隔離目錄解壓、執行 Python/pytest、交叉檢查三個 Sherlock Basic 事件之 JSON、report、evidence bundle。

## 0. 可重現性與已成立的成果

- 使用這份 ZIP 執行 `PYTHONPATH=src pytest -q tests/test_reconstruction.py tests/test_postalert.py tests/test_etgi.py`：**66 passed, 2 failed**；兩項失敗均出在 `src/mirage_ot/etgi/evidence/index.py:14` 對 ZIP 未附的 `mirage_ot.ipal` 匯入，屬打包依賴不足。單獨測 `tests/test_reconstruction.py` 為 **4 passed**。不能由此宣稱原 Mac 專案的 68 項測試失敗，也不能把本次打包視為全部程式的整體測試。
- 19 個 postalert/reconstruction 模組 SHA256 全部與 manifest 一致。從檔案內容重算 `code_sha256=c884c2d4705e3458e5fb62378135eceb61c21067bc43cd3007f9f5e1054775ad`，三個事件一致；三者 manifest 記錄 commit `b0bbe660…` 和 clean diff hash。這個摘要只涵蓋上述兩個模組目錄，不是整個 repo 的內容 digest。
- 三個事件的 evidence audit bundles：`ev0961 312/312`、`ev12 149/149`、`ev3e4d 228/228`；皆 `missing_ids=[]`、`row_check_failures=[]`（這證明引用範圍內稽核包完整，不等於所有事件事實語意均正確）。
- 真實 `sgen.6` 的命令值 20000.0、命令前 40004.5312、命令後 20000.6875；`sgen.10` 的命令值 270000.0、命令前 309980.938、命令後 269971.625。兩者都是值得保留的實際觀測順序，但不等於物理因果已被獨立證實。

## 1. P0：狀態訊息「存在」即被標成「狀態已改變」，導致真實事件過度宣稱

**程式**：`src/mirage_ot/etgi/reconstruction/transactions.py:397–410,481–495`；`event_graph.py:323–355`；`report.py:187–198`。

`_finalize_transaction` 接受任何同 RTU/CA/device stem 監測訊息，且條件 `m["cot"] == 3 or m["type_id"] == 1` 甚至可能接受並非 spontaneous 的 type 1 回報。只要找到任一回報，`has_spontaneous=True`，即直接設 `device_state_change_status=state_change_observed`，沒有核對點位狀態值或命令前基準，也沒有檢查回報是否與命令目標一致。

**已在真實稽核包驗證：五筆開關回報皆沒有成功解出狀態值**：

- `ev0961`: `switch.23:is_closed` 的 EV-3109cd2175859fbc、`switch.24:is_closed` 的 EV-1d4bff598cd2de10、`switch.25:is_closed` 的 EV-520a8e57a72caf4a；
- `ev3e4d`: `switch.31:is_closed` 的 EV-3a78b2dbe4a1f370、`switch.27:is_closed` 的 EV-917419e06fdb9b27；

這五筆在 `transactions.json` 是 `value=null, value_present=false`，稽核列 payload 的 `alignment=unparsed_value`，但全部被標成 `state_change_observed`。`IPAL new` 是來自網路的狀態更新，不是設備物理真值；在沒有先前值與可靠解碼之前，也不能單憑它斷言發生轉換。

**修法**：將 `state_report_observed` 與 `verified_state_transition` 設為不同狀態；只有可解析的狀態值 + 命令前比較（或可信相對狀態證據）才升級 `state_change_observed`。解析 type 1 `siq.spi` 布林／品質欄位和 type 45 `sco.on` 布林／select/execute 欄位；缺值時應是 `state_report_value_unknown`，而非默認完成。根據 COT=3 報告與某命令相鄰，最多先建立「後續相關觀測」而非直接協定確認階段。對三個舊案例重跑并註明研究結果修正。

## 2. P0：`supported_inference` 邊無條件建立，且未進入主張驗證

**程式**：`transactions.py:412–453`，`event_graph.py:375–391,670–742`，`engine.py:46–50`，`report.py:136–185`。

在交易階段先計算 `shifted_from_pre_baseline`、`matches_commanded_setpoint`；但在 Graph 階段 `if post_fid:` 即建立 `command_to_device_state_transition`、`claim_level=supported_inference`、`verification_status=supported`，不檢查前述布林值，甚至直接以文句聲稱 `matching target setpoint`。

**已進行不改原檔的反例測試**：複製 `ev0961 TX004`，把上述兩個旗標都設定 `False`，並把 `post_command_value` 改成 39999.0（命令值仍為 20000.0）。呼叫 `build_temporal_event_graph([], {}, tx_copy)` 仍生成 `R0015`，標成 `supported_inference/supported` 且文字仍稱吻合目標。這是程式邏輯缺陷，雖然原始 sgen.6/sgen.10 的數值確有接近目標。

此外 `run_llm_explanation()` 的 `verify_claims()` 僅驗證 **LLM 自選的 claims**。Graph 內的系統推論邊先被標成 supported，直接進入 Storyline/Report，沒有再經一個獨立判準檢查。實際三個 run 的 verified LLM claims 分別為 1、2、1 個**觀測事實**，不是其 graph 的 4、1、2 條推論邊全部已通過 Verifier。切勿混用兩者。

**修法**：只有已確認的正向 ACK（或明確標示 ACK 未知）、可靠 pre/post 比較、目標方向相符且容差合理，才產生 **candidate** inference；由獨立、可審計的 consistency gate 升級。沒有前置基準／值缺失／目標不符則保持 `unresolved`，不應硬標 `supported`；同時將圖邊與 LLM 主張的驗證狀態分開列印。補 `post unchanged`、`post shifted wrong direction`、`no pre baseline`、`different CA/IOA` 等反例。

## 3. P0：COT=7 缺少負確認（P/N bit）解析；`accepted_by_rtu` 可能過度確定

**程式**：`src/mirage_ot/etgi/evidence/iec104.py:79–85,113–179`、`evidence/index.py:325–330`、`reconstruction/transactions.py:333–379`。

解碼字段沒有提取 COT P/N（negative confirmation）、Test bit、控制命令 select/execute、品質位；`_attach_control_reply` 對所有 COT=7 都設定 `accepted_by_rtu`。故現有索引無法分辨真正的正向接受和負向確認；也無法根據命令值確認 `C_SC_NA_1` 開關操作的控制狀態。

**修法**：在 tshark 解碼器加入並實際核對 IEC-104 P/N、SQ、S/E 等對應欄位（先確認環境版本的正確 Wireshark 欄位名稱）；將值與品質存入原子 evidence payload，加入 negative ACK 測試。當原始資料缺失正負確認位時只可輸出 `activation_confirmation_observed_acceptance_unknown`，不要宣稱已接受。

## 4. P0/P1：SL004（及 ev12 SL001）並非連續路徑，卻被報告成逐步事件鏈

**程式**：`storyline.py:66–74,224–237,272–379`。

Beam Search 先找到 `command -> ACK -> post_measurement -> IPAL`，再將 `pre_to_post_measurement_transition` 作為一條比較邊 **prepend** 到 path：

- `ev0961 SL004`: node 序列 `[EF015(pre), EF013(cmd), EF014(ack), EF016(post), EF018(IPAL)]`，edge 序列 `[R0014(pre->post), R0013(cmd->ack), R0015(ack->post), R0017(post->IPAL)]`。第一條邊的終點 EF016 不是第二個節點 EF013。
- `ev12 SL001`: 同樣模式 `[EF003(pre), EF001(cmd), EF002(ack), EF004(post), EF006(IPAL)]`，第一條邊直接指向 EF004。

**已實際程式化比對三個事件全部 Storyline：恰好以上兩條不符合「任一 edge 的 source/target 等於 node[i]/node[i+1]」的 path invariant。** 時間列表仍遞增；缺陷在圖路徑拓樸，不是數字時間逆序。

**修法**：不把 pre/post 比較邊塞進線性 spine；把命令前量測掛在 `context_observations`，比較關係掛在 `supporting_evidence_edges`，把主幹維持連續的有向路徑。或直接將 Storyline 明確定義為 DAG，提供 topological order 與 adjacency，不可同時聲稱連續 path。加入 `edge-source/target == neighboring-nodes` 單測。

## 5. P1：跨 vantage 的 `tcp_seq` 去重可能合併不同值；過度概括 TCP retransmission

**程式**：`transactions.py:160–276,315–329`。

分組條件 `same_tcp_seq_diff_vantage` 比對同一 5-tuple / `tcp_seq` / type / COT / entity / CA-IOA，**沒有比較 ASDU 數值**、TCP payload bytes hash、TCP epoch；一旦使用相同 seq 但不同內容（特別是注入、路由中途改寫、連線重用），後面值被吞掉。

**已執行 synthetic counterexample**：同一 5-tuple、seq=55、CA/IOA、type=50、COT=6；n302 value=100，n318 value=999，timestamp 相差 10ms，函式仍合併成一筆，只顯示 100，包含兩個 evidence ID。另一方面 `_find_retransmit_target` 對確認前 0.5 秒內同鍵的第二個命令視為 retransmission，未核對 TCP 重傳序號或 APCI 序號，可能吞掉合法的重複操作。

**修法**：衝突 value/payload 絕不能靜默合併，輸出 `cross_vantage_payload_conflict` 並保留雙觀測；增加 TCP connection epoch、APCI send sequence（若可用）、payload digest；區分 mirror duplicate、TCP retransmission 與 new application command。補 `same_seq_different_payload` / `before_ack_different_apci_seq` 測試。

## 6. P1：來源容器數量不等於獨立支持數；N-P 同源連結部分只依時間／點位

**程式**：`event_graph.py:755–761`、`storyline.py:194–203,382–390`、`event_graph.py:433–455`。

`_containers_of_msg` 同時保存跨 vantage fingerprint（兩個 hash）、`tcp_seq:<tuple>#<seq>` 與 point-key；`_informative_containers` 又可能從 IPAL evidence 自身退回，故 `independent_source_container_count` 不是「獨立物理來源數」。真實 `ev0961 SL001` 是 10 個 containers，但主幹只有 3 個不同的 IEC-104 邏輯通訊階段與 1 個衍生 IPAL 轉錄，不能說有 10 份獨立證據。

另在 `event_graph.py:437–455`，即使沒有具體訊息層 parent/依賴鏈相同，只因同 entity+CA/IOA、時間接近就稱作 `shared_source_ipal_transcription`。整個 IPAL 狀態雖源自網路，並不保證這兩個事件節點是同一個封包／同一個樣本。應嚴格分 `same_original_packet` / `same_network_data_stream` / `temporally_aligned_same_point`，不要以後者宣稱逐包轉錄。

**修法**：為邏輯消息產生跨 vantage canonical source id；同 source 計一次；把 `capture_count`、`logical_message_count`、`independent_support_count` 分開。N-P 邊需要明確 source mapping 或較弱的關係型別。

## 7. P1：報告會自動刊登系統推論，驗證邊界與「無證據」語氣需要加強

**程式**：`report.py:140–207,269–350`，`event_graph.py:323–391`。

Graph 的 `verification_status=supported` 是建圖時的標記，不等於 LLM verifier 獨立批准。`build_investigation_report` 無條件渲染全部 transactions 和 storylines，且只要 `tx.device_state_change_status` 為 observed 就列入 confirmed impacts。這在已知 switch value-null 的案例尤其嚴重。

Graph/Report 部分 Evidence ID 為了簡短只顯示前 2 個，跨設備共同出現可能只顯示 trigger 一側 ID（例如 ev0961 report `R0033`），雖然 JSON 有兩端資料。應至少清楚列出 `source_evidence_ids`、`target_evidence_ids`，避免「說的是線路變化，卻只引用控制命令封包」的稽核誤解。

## 8. 建議只進行一輪「修正重建引擎」——不是更換題目

**下一個 milestone：Reconstruction Reliability Fix**。先 P0，再 P1，不擴大 Agent/LLM 比較、不改 Sherlock、不重寫 graph/search。

### P0 完成標準
1. Switch 狀態值未解出或找不到 before/after 證據：`state_report_observed` 而非 `state_change_observed`；依原三事件重跑，不改舊輸出。
2. COT=7 P/N 位未明：`confirmation_observed_acceptance_unknown`；Negative Ack 明確不能接受。
3. `supported_inference` 只在實際判準成立且通過獨立 consistency gate 才生成或升級；改變 `shift` 與 `matches_setpoint` 為 false 不能生成 supported edge。
4. 所有 `spine` node/edge 必須形成真正連續路徑，或變為有正式 DAG schema 的事件圖；前置量測不得偽作第一段線性路徑。

### P1 完成標準
5. 跨 vantage 同 TCP seq 但內容不同不合併；相同資料多 vantage 不重複計來源支持。
6. `independent_source_container_count` 不再隨鏡像埠數量假性增加；N-P 的對應說明區分同封包與同資料流。
7. 報告可追溯兩端 Evidence IDs，並區分 `protocol observation`、`candidate association`、`verified state change`、`supported noncausal inference`。

### 核驗回歸樣本
- `ev0961`: 3 筆 switch COT=3 但 `value_present=false` 不可聲稱已確認狀態轉換；`sgen.6` 數值前後確有接近目標的觀測，保留但不聲稱獨立物理因果。
- `ev3e4d`: switch.30 無後續確認狀態變化仍保留不完整 TX；另 2 個開關未解值不應宣稱狀態轉換。
- `ev12`: sgen.10 的 5-node 改成合法 transaction spine + pre/post supporting comparison。
- 實驗 code sha、Git commit、單測、audit coverage 全記錄，新目錄不可覆寫舊資料。

## 9. 核心結論

MIRAGE-OT 已有真正的 IEC-104 操作重建、事件圖和可查證數值案例；`sgen.6` / `sgen.10` 可作方法研發的正向觀測案例。現在最關鍵的是把「看到狀態報告」「設備狀態有改變」「設定點符合」「此命令導致改變」拆成互不混淆的判準與輸出。否則系統的自動事件重建會因過度升格而產生看似完整、實則無法被原始資料支持的事件鏈。
