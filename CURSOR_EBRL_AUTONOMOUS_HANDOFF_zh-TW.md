# Cursor Agent 自主開發任務：ICIT 2027／EBRL 端到端完成

> **請將本文件視為開發委託與驗收規格。目標不是再寫一份設計提案，而是親自在現有 repository 中完成實作、測試、實驗、文件和論文中有證據支持的更新。**
>
> 工作方式：先讀取、盤點與提出精簡可執行計畫，然後持續逐項實作、執行、測試、修正，直到所有在現有環境與證據下可完成的項目完成。不要在每完成一小步時等待我回覆；不要把未完成工作偽裝成完成。若遭遇真正的外部阻礙，先完成所有不受該阻礙影響的工作，再清楚記錄阻礙與所需的最小使用者協助。
>
> **新增且優先的使用者要求（2026-10-13）：凡研究實驗需要使用 LLM，一律以本地／自行管理的地端模型推論，不得以雲端商用模型 API 作為替代、備援或正式實驗條件。詳見第 4A 節。**

## 0. 專案識別與操作原則

- Repository：`https://github.com/CHPIYR2/ICIT2027`
- 目前已核對 `main` commit：`0c02db409da1c91bf0d01bf9b1dc71a8cedefa95`（2026-10-11；`Strengthen EBRL method and evaluation framework`）。**這是交接時的快照，不要假設永遠是最新版本。**
- 主論文：`icit2027_ot_investigation.tex`；編譯成品預定：`output/pdf/icit2027_ot_investigation.pdf`。
- 交接背景：使用者先前提供 `CODEX_HANDOFF.md`；若本地沒有該檔，則以 repository 的最新可檢查原始碼、配置、凍結 manifest 與本文為依據。
- Python 專案：`pyproject.toml` 目前要求 Python >=3.11；存在既有 `src/`、`tests/`、`experiments/`、`scripts/`、`configs/`、`schemas/`、`data/`、`results/`、`docs/`。
- 全程使用繁體中文回報進度與最後結論；論文本文及既有英文專有名詞維持學術英文。
- 優先在獨立工作分支開發；**先檢查 `git status`，保留所有既有未提交修改**，不得覆蓋使用者工作。可以在工作分支作小型、可追溯 commit；未經使用者明確授權不得 force-push、刪除既有歷史、重寫 protected artifacts、合併至 main，或啟動外部／雲端 LLM 服務（無論是否收費）。
- 讀取及修改本地 repository；不能直接操作的外部資源只記錄阻礙，不得假裝已執行。

## 1. 研究定位：不可偏離

論文暫定題名：**Beyond Co-Occurrence: Evidence-Bounded Cross-Modal Relation Ledgers for Post-Alert OT Investigation**。

這不是新的 anomaly detector。上游偵測器或分析人員已提供事件視窗 `W_e` 和時間錨點 `t0`；研究的任務是：針對 OT 網路命令與程序／電氣遙測變化，判斷在**模型實際可見證據**下有哪些可支持的關聯、有哪些明確不關聯、哪些必須保持未知；並避免將「同時出現」升格成執行、物理完成、因果、入侵、意圖或歸屬。

不得宣稱：端到端異常偵測、事件自動切割效能、完整因果推論、對真實生產環境的外部效度、已部署地端控管能力，除非有對應實驗。`W_e` 與 `t0` 是外部提供的 oracle-like inputs。

本研究關鍵問題：
- **RQ1 Relation quality**：固定相同事件、證據預算與候選集合後，EBRL 相對時間、資產與語意規則基準，是否更能找回有根據的關聯、減少不受支持的關聯？
- **RQ2 Semantic restraint**：語意上限、證據型別與顯式棄答，相對直接 LLM、引用 Evidence ID 的 LLM 是否有幫助？
- **RQ3 Components**：確定性的發布驗證器（verifier）對錯誤關聯、語意過度提升、證據路徑完整性、召回率有什麼影響？

### 已知資料集與切分（尚待重驗）
- 使用 Sherlock v3、IEC 60870-5-104 網路流量及電氣／程序觀測。
- 新版 EBRL **論文目前規劃**：development 16 個 `01-Basic` 事件；evaluation 32 個事件（`02-Semiurban` 18、`03-Rural` 14；文中稱 cyber 16、benign 16）。必須實際核對 manifest，不可只相信文字。
- **舊研究**稽核與 E/N/EN 實驗可能使用 35／84 等不同的切分、不同任務。絕不能混用事件數、模型分數與評估結果。
- Repo 舊 README 對 claim-support／protocol-exact 的 0.0000、1.0000 等結果不是 EBRL 配對層級的實驗成績；不得搬入新表格。

## 2. 先做 Repo／資料稽核，再定方法

立即執行：
1. `git status`, `git log -5 --oneline`, 列出目錄與 Python/測試入口；記錄當前 commit、工作樹、環境可用性。
2. **完整閱讀** `icit2027_ot_investigation.tex`，特別是 Episodes and Frozen Candidates、Relation Semantics、EBRL、Reference Construction、Baseline Ladder、Metrics、Limitations、`\TBD{...}`。
3. 閱讀 `README.md`、`BUILD_NOTES.md`、`docs/sherlock_audit.md`、`docs/evidence_contract.md`、`data/README.md`、`configs/evidence_contract.v1.json`、`configs/protocol.v1.lock.json`、相關資料 manifest。舊文件有過時內容時，標記衝突與哪個版本具權威，不直接沿用。
4. 調查現有 `src/sherlock/`、`src/evidence/`、`src/retrieval/`、`src/investigation*`、`schemas/`、`tests/`、評分工具的**可重用元件**，不要因名稱相似便誤以為已經實作 EBRL。
5. 確認資料在本機是否可用、SHA256/manifest 是否匹配、磁碟空間及可能的大檔案。資料集既有稽核稱三份封存檔約 8.95 GB；不得任意重複下載或展開、不得更動 immutable manifests。
6. **最重要的科學性稽核**：逐一查明是否真的存在獨立的 `command → execution / operational response → physical effect` 來源追溯（操作日誌、動作 ID、情境模擬器 trace、直接狀態轉換的可連結記錄）；判斷完整性、時間一致性、可否正確連接到 command/telemetry episodes、是否適合建構正負標籤。把實際可用欄位、無法確認欄位、例子與測試記錄在新稽核文件。

**不可跳過第 6 點。** 若沒有獨立 Ground Truth，不可以把時間＋資產＋語意規則的輸出當成獨立真實標籤；R3/R4 的事實正確率應標記 `NA` 或縮小研究結論。缺少獨立來源證據不一定表示系統不能執行 R0–R2，但必須如實報告研究界線。

## 3. EBRL 正式管線：必須實作，不只是畫圖

**輸入**：事件視窗與錨點、可見網路紀錄、可見遙測紀錄、經審查的資產映射、證據預算、版本化契約。

**輸出**：每個候選配對恰好一筆 ledger row，包含 raw proposal、發布後判定、必要證據 ID、驗證理由、可追溯事件／來源；加上一份只能根據核准 ledger rows 生成的調查報告。

### A. Episode Normalizer
- Network：將 IEC-104 的 request／response／retransmission／select-before-operate 等整理成 command transaction episodes。保留 flow、APCI/ASDU、CA/IOA、COT、方向、命令語意、時間、原始證據 parent IDs、品質與版本等。
- Process：將可見 telemetry 轉為 change episodes（狀態轉換、持續數值變化），包含 before/after、變化方向、單位、asset、observed_at、最新鮮度、lineage。
- 自動處理去重、單位、時鐘偏差、量測 deadband/change-point、缺失、stale、quality flags；所有重要參數需由開發集確定，版本化寫入 config。
- 不可以把 network protocol ACK 解讀成 command executed；不可以把 reported telemetry 當實體真值。
- 重用現有經測試的封包解碼／證據管線；若存在映射別名碰撞、相同封包在多觀測點出現、PCAP 衍生的 E/N 共享來源，必須維持 lineage 防止假獨立證據。

### B. Candidate Generator（候選產生，不是暴力列舉全部原始紀錄）
- 基本數學契約：`C_e ⊆ Q_e × P'_e`。論文目前的初步候選條件為 `abs(delta_t) <= tau_max OR asset_neighborhood_map(q,p)`，但**`tau_max` 與資產映射的正式規則目前沒有定稿**，先在開發集決定並凍結。
- 操作 episode，不做 raw-packet × raw-sample 的無限笛卡兒積；優先使用 time-index／interval query／asset partition 產生候選。若要限量，依事前凍結的 strata quota + deterministic hash；不能只留下「容易判定」的候選。
- 必須保留不同挑戰類型：資產語意相容、資產相同但語意不相容、時間近但資產不相容、反向時間、競爭控制命令、間接或缺映射情境；不可為了高分排除負樣本或未知樣本。
- **固定（freeze）是每次事件調查的候選快照**，不是所有新事件永久使用相同配對；應保存版本、hash、builder config、來源 IDs。未來增量資料可產生 V2 而非竄改 V1，舊快照能重播。
- 所有 baselines、P0、P1 使用完全同一份候選集合；測量候選可取得性／列舉召回率、per-event 候選數、wall time、記憶體與規模增長。若 ground truth 不足以測 candidate recall，就誠實標示無法測。

### C. 關聯語意：Disposition + Semantic Ceiling 為兩個軸
- `L`: supported link；`N`: supported non-link（必須有**可見的反證**）；`U`: insufficient evidence。未列入已知 link 不等於 `N`；missing 不可轉成 negative。
- `R0`: 沒有受支持的跨模態關聯。
- `R1`: 僅能支持共同出現／時間先後。
- `R2`: 時間、資產映射、命令－變數語意共同支持**有限關聯**；不能宣稱執行或因果。
- `R3`: 有獨立執行或操作回應證據支持更強的操作關係。
- `R4`: 有獨立介入／動作－效果來源追溯，才可支持實體完成或因果主張。
- 層級是**可宣稱的上限**，不是 `0~4` 的機率或信心分數。執行、完成、因果、資安（入侵／意圖／歸屬）是**彼此獨立、各有證據要求的 promotion flags**。`R2` 不得設定因果或已入侵為 true；protocol acknowledgement 不得直接設定 completion=true。
- 定義對每個 disposition / level / flag 的必要條件、反證與優先順序。R1 時間關聯是否刊為 `L` 必須明訂「時間性 link」與「操作性 link」的語意邊界，避免評估混淆。

### D. Relation Proposer（真正負責提出關聯）
- 先完成**完全可離線重現的 rule-based proposer**，檢查：時間先後與 skew、資產映射、命令－變數相容性、方向／目標、競爭命令、跨設備影響、可見執行／效果證據。
- 使用版本化 semantic ontology / compatibility table：例如 `Open breaker` 與回報開關狀態／電流下降「語意相容」不等於確定造成；變壓器、tap、電壓、功率等也應有真實資料欄位支持才加入規則。
- 產生 `L/N/U`、`R0~R4`、typed evidence IDs、promotion flags、reason code、optional confidence。confidence 若使用，必須在開發集定義及校準；缺乏校準不得虛構數字。
- 後續加 LLM proposer 或 rule+LLM hybrid（如果環境已提供可授權模型），輸入只包含同一 visible evidence budget 和 candidates；要求 structured output；不要默認 LLM 判定為真相。
- 不應依賴使用者先指定某家付費 API 才能完成最小實作：無憑證時先以 deterministic baselines、test fixtures、可用本地模型完成全部可離線部分；將需要付費／連線的矩陣明確標為 `BLOCKED_NOT_RUN`，不可偽造 LLM 結果。

### E. Evidence Ledger 與 Publication Verifier（核心）
- Ledger schema 應至少涵蓋：event/candidate/episode IDs、row validity、raw disposition、raw proposed level、typed network/process/mapping evidence IDs、promotion flags、reason code、optional confidence、verifier findings、published disposition & level、provenance/version。每個候選恰好一筆；缺失／無效 row 是 failure，不可自動計為正確棄答。
- Verifier 是**獨立的確定性政策檢查器**，不負責捏造證據，也不得存取 evaluator-only ground truth。至少檢查：schema、候選集合成員、evidence ID 存在且可見、角色型別、timestamp/skew、units/quality/stale、asset mapping、semantic compatibility、competing commands、ACK-to-execution/physical-completion 過度推論、各層級與 promotion flags 必要證據。
- 行動僅限：`retain`、`downgrade`、`suppress / rewrite published disposition to U`；不刪候選行、不擅自把未知變成 supported non-link；必須保存 raw proposal 與 verifier reason。
- 明定多重失敗時優先順序、降級條件、無效 row 處理、R2/R3/R4 門檻及 challenge tests；逐條實作可機械檢查的規則表。
- **Verifier 不是獨立 Ground Truth 評分器**。它「符合自己規則」不等於「事實一定正確」。

### F. 報告生成
- 僅由 validated/admitted ledger rows 透過受控模板產生文字；可以描述 supported links、supported non-links 與 unresolved/missing evidence。
- 嚴禁報告額外創造 Ledger 沒有的因果／攻擊／設備動作主張；可用可逆連結追溯到 evidence IDs。至少包含端到端案例與可重播輸出。

## 4. 評估器必須與驗證器隔離

- 分開實作並版本化：`reference_builder`、`publication_verifier`、`scorer`。獨立 evaluator-only provenance 只可用在 reference builder 和 scorer，絕對不能進 proposer、prompt、retrieval、模型特徵、verifier 或報告。
- 來源不足或正負標籤不完整：標註 unresolved；受影響分層的 operational precision/recall 設 `NA`；不能把 `U` 擅自當作 `N`。
- 如果 Gold 是用與 B2/B3 或 Verifier 同一套規則算出，必須標記 **policy consistency / silver-label**，不能當獨立 operational ground truth；實驗表拆開。
- 如果可能建立反事實 hard negatives，需說明生成方式、有效性檢查、分佈界線及與真實事件的差異；若人工審查不可避免，定義雙人獨立盲審／抽樣與一致性統計；無法取得人員時留下完整可執行審查協議，不可虛構審查結果。
- 所有方法在相同 `W_e`、`t0`、visible evidence budget、mapping、candidates、output schema 下比較。

### 基準方法與消融實驗

依序實作並可執行：
- `B0`: Abstain-all，全部 `U`，負向對照；
- `B1`: Nearest-after，純時間，誠實限制在 R1；
- `B2`: Asset+Time；
- `B3`: Asset+Time+Semantic，最強的非 LLM 確定性基準；
- `B4`: Shallow pair classifier，**只有**獨立標註的開發資料足夠才實作／執行，否則有理由地標記不適用；
- `B5`: Direct LLM，無強制 evidence path；
- `B6`: Evidence-ID-grounded LLM，須引用 ID 但沒有完整 EBRL verifier；
- `P0`: EBRL without verifier；
- `P1`: Full EBRL（對 P0 使用 deterministic verifier）。

LLM 實驗僅能使用第 4A 節允許的本地模型。若無可用地端模型，先完成程式、mock/test、介面、replay 機制並嘗試合理的本地環境修復；不能把 mock 當實驗數據，亦不可自動切換成雲端模型。

### 指標（不可僅看 precision）

優先具備：
- 有獨立真值時的 Operational Link Precision / Recall、Unsupported Operational Link Rate。
- Event-level false-relation incidence（事件為主要統計單位）。
- Visible policy consistency、semantic overpromotion、evidence-path completeness/accuracy、invalid/hallucinated evidence IDs。
- Supported non-link recovery、appropriate abstention、substantive coverage。
- Evidence availability / candidate enumeration recall，與關聯決策指標分開。
- Scenario / event-family 分層統計，event-stratified paired bootstrap 可信區間；同一事件多 pair、重複生成不可當獨立樣本。
- 在基準與 gold 共用規則時，明確標成政策重播診斷而非獨立事實精度。

## 4A. 新增硬性要求：LLM 實驗一律使用本地模型（Local-Only LLM Experiments）

**本節優先於文件中任何較早的 API／provider／額度敘述。這項限制針對「論文實驗的 LLM 推論」，而不是宣稱 Cursor 編輯器自身的 Agent 一定採用地端推論。**

### 模型來源及連線範圍

1. **禁止**以 OpenAI、Anthropic、Google Gemini、雲端託管推論端點、未經明確核准的第三方推論代理，作為 B5/B6/P0/P1 的模型實驗來源；**不允許因地端模型不可用就自動退回雲端 API**。不得上傳 Sherlock 原始封包、模型可見證據、提示詞、生成輸出或 evaluator-only 資料到雲端推論服務。
2. **首選 Ollama**，因其具備簡單的本地模型管理與 HTTP 介面。優先偵測 Cursor 執行機器上的 Ollama（例如 `http://127.0.0.1:11434`）；若使用者已在自己管理的其他電腦部署 Ollama，亦可透過**經確認為自主管理的 LAN／私有網段**連線。自行管理的內網伺服器仍屬地端推論，但需記錄推論執行主機、實際連線方式與資料是否離開研究電腦；不得假設任何 IP、連線或權限已存在。
3. 啟動前實際執行環境檢查，例如 `ollama --version`、`ollama list`、`curl http://127.0.0.1:11434/api/tags`（依當前 OS 調整），測試最小結構化推論；檢查可用 RAM／VRAM、磁碟與實際速度。若服務未啟動，按現有授權與合理權限嘗試啟動；若機器資源不足，記錄原因並改用實際可運作的較小地端模型。
4. 模型候選可從**現場確實已安裝的模型**中選擇，例如 Ollama 的 Qwen Instruct、Gemma、Llama 等；`qwen2.5:7b` 可作為優先檢查的候選，但**不得預設它在此 Cursor 主機存在**，也不得杜撰精確模型版本、量化格式或容量。若需下載新模型，先評估磁碟、頻寬、模型授權與下載量；下載開源模型權重不等於使用雲端推論，但不得執行未授權的大型下載或系統層級破壞性安裝。
5. 將執行端抽象成可替換的 `LocalLLMAdapter`，第一版實作 Ollama adapter；必要時可兼容 `llama.cpp`、`vLLM` 等**確實在本地／自主管理環境提供推論**的介面。不要將特定的私有伺服器 IP、帳密或使用者個人路徑寫死到研究程式或公開設定檔。

### 實驗公平性與可重現性

6. **B5 Direct LLM、B6 Evidence-ID-grounded LLM、EBRL 的 LLM／hybrid Proposer 都必須使用同一個經凍結的本地模型快照**，除非另立並清楚標示模型比較實驗。三者固定相同的可見候選集合、證據預算、token 上限、輸入來源與執行協議；差異應限於方法要求（例如證據型別限制、關聯規則、驗證器），避免把模型差異誤當 EBRL 改善。
7. 在 `configs/ebrl/local_llm.json`（或既有更合適的位置）記錄模型名稱、完整 digest／hash（若介面可取得）、量化格式、參數規模（若可驗證）、context length、temperature、seed（如後端支援）、top_p、num_predict／max tokens、prompt 版本、JSON schema、Ollama 與 adapter 版本、hardware/runtime 設定及執行日期。無法取得的欄位標 `unknown`，不可猜測。
8. 優先使用結構化 JSON 輸出與 schema validator；對超時、模型載入失敗、OOM、輸出截斷、無效 JSON、缺漏 ledger row、證據 ID 幻覺、長上下文截斷建立明確 error/failure policy。重試次數與超時界線要明定；不可將失敗默默變成正確棄答。
9. 不要將 `temperature=0` 視為絕對確定性保證。先以 development／小型 smoke test 驗證輸出格式與資源可行性，再凍結設定、記錄每輪原始輸出／hash，依實驗協議執行重複次數，產生可重播結果。
10. Verifier、candidate builder、schema validator、獨立 scorer 必須可**不依賴 LLM 或網路**單獨執行與測試。LLM 可以提出關聯，但**不能成為證據真實性的最終裁決者**；正式報告只能從經 deterministic verifier 採納的 ledger 輸出。
11. **嚴守資料邊界**：`evaluator-only`、情境真值、攻擊標籤、完整 simulator provenance 禁止進入模型 prompt、embedding、retrieval、context 或 verifier。地端推論本身不會消除 reference leakage，必須在資料管線做明確驗證。
12. 正式研究報告需記錄每種方法的可用模型、實際推論次數、成功／失敗／中斷數、wall-clock 時間、token 使用量（有量測才報告）、峰值資源（可量測時）、每個事件耗時與實驗日期。若資源不足導致部分實驗無法執行，請如實標示 `BLOCKED`／`NA`，不可用 mock、預錄他人輸出或任何雲端回應冒充本地實驗成果。

### 本地模型專用驗收項目

- 能以 Ollama 或等價的**實際地端服務**完成單一候選與完整事件的最小 end-to-end 推論，並確認無雲端模型 fallback。
- B5、B6 與 EBRL 的 LLM/hybrid 條件可使用**同一個本地模型與凍結 evidence manifest**執行；輸出附來源 ID、耗時、schema 驗證結果及必要版本資訊。
- 提供明確離線重播指令：重播既有本地生成 artifact／驗證／評分時不需要連到任何外部 LLM API。
- 若無法連接可用的自主管理推論端，先完成非 LLM 部分，再把地端模型的**精確缺口**列入 `docs/EBRL_IMPLEMENTATION_STATUS.md`；不得聲稱 LLM 實驗已完成，也不可用雲端替代。

## 5. 必須涵蓋的失敗與回歸測試

- Same-event/time-near 但錯資產；同資產但命令語意不相容；反向時間；clock skew。
- IEC-104 request、activation confirmation、TCP ACK、實際操作回應、實體完成不可混為一談。
- 多個競爭命令、控制命令重傳、select-before-operate、別名碰撞、間接跨設備傳播。
- 電流／電壓／功率單位、per-unit、量測死區、stale state、缺少 quality、missing 不可補 0。
- 同一 PCAP 衍生 E/N 的來源 lineage；重複觀測點不能被當成兩份獨立佐證。
- evidence ID 未知、錯角色、指向未可見資料、跨事件、超出截止時間、被移除 parent 後仍引用。
- malformed / duplicate / missing ledger row 應被記為錯誤，不能當正確 `U`。
- Verifier 的 retain、downgrade、rewrite-to-U；多重失敗優先序；不能將 U 變 N；不能用 evaluator truth 幫模型作弊。
- Candidate freeze hash、同 seed 重播一致性、所有 baseline 相同分母、有限規模／極端候選數的效率測試。
- Report 文字不超出 ledger、不可把 R2 升為因果或資安攻擊證實。
- 架構可移植性：用人工合成的小型第二種設備命名／mapping fixture 測試，不得把對合成資料成功說成跨真實資料集泛化已驗證。

## 6. 執行順序與自主管理

請建立並持續更新 `docs/EBRL_IMPLEMENTATION_STATUS.md`，每個任務標為 `TODO / IN_PROGRESS / DONE / BLOCKED / NOT_APPLICABLE`，附具體檔案、測試、決策及證據來源。**不要只產計畫後就停止。**

- **Phase 0 — Inventory & risks**：盤點 repository、環境、git 狀態、凍結與防洩漏邊界；清楚寫出目前未知數與解決方案。
- **Phase 1 — Provenance feasibility**：稽核 Sherlock 獨立操作 Ground Truth；明定 R3/R4 是否能被事實驗證，無法時調整可宣稱範圍；發現分歧時保留原始證據、記錄理由。
- **Phase 2 — Contract-first**：凍結 episode schema、candidate generation config、semantic levels、disposition policy、evidence roles、mapping ontology、Ledger JSON schema、Verifier 規則表、版本與 hash；提供端到端人工 fixture。
- **Phase 3 — Core implementation**：實作 normalizer → efficient candidate builder → rule-based proposer → ledger → verifier → report；建立 CLI，可重播單一事件與批次事件。
- **Phase 4 — Scorer & baselines**：先建立獨立 scorer / gold contract，再做 B0–B3、P0/P1、可行的 B4；確認反證與 unknown 判定正確。
- **Phase 5 — Local LLM comparisons**：依第 4A 節先檢查本機／自主管理私網上的 Ollama 等地端推論服務、模型與資源，然後完成 B5、B6、EBRL hybrid 的同輸入本地實驗；無雲端替代或 fallback。凍結相同模型 digest、prompt/budget、重複次數、錯誤處理、輸出與 hashes；若地端服務不可用，保持此部分 `BLOCKED` 並完成其餘開發。
- **Phase 6 — Evaluation**：確認 development/evaluation split，開發集定閾值，凍結後執行評估；跑所有可行基準、消融、bootstrap、錯誤分析、runtime/candidate-cost 分析，產生 table-ready 結果與 manifest。
- **Phase 7 — Manuscript & docs**：只填入真實測得的內容；未能完成的結果保持清楚 `TBD/NA/Blocked`，更新 Methods / Metrics / Results / Limitations / README；依現有 IEEEtran 編譯來源、檢查 BibTeX、圖表與 PDF 每頁；不得為了表面完整虛構論文結論。
- **Phase 8 — Final acceptance**：執行全套測試、獨立重播、hash/leakage 驗證，整理驗收報告與可重現指令、尚存限制；儘可能完成所有 `DONE`。

### 推薦新增產物（若既有結構更合適，可調整但需說明）

- `docs/EBRL_IMPLEMENTATION_STATUS.md`、`docs/ebrl_relation_decision_spec.md`、`docs/ebrl_provenance_audit.md`、`docs/ebrl_evaluation_report.md`
- `configs/ebrl/`：參數、semantic ontology、verifier rules、freeze manifest、**local_llm.json**、model/budget config
- `schemas/ebrl/`：episode、candidate、ledger、report、reference 等 schema
- `src/ebrl/`：normalization、candidates、proposer、verifier、report、scorer、reference_builder、adapters
- `scripts/` 或 `experiments/`：`run_ebrl.py`、`evaluate_ebrl.py`、`reproduce_ebrl.py`
- `tests/test_ebrl_*.py`：含 fixture、單元、端到端、洩漏與重播測試
- `results/ebrl-*`：新的、可追溯的結果；**絕不覆寫舊實驗**

## 7. 自主工作模式與需要使用者介入的邊界

1. 現有環境允許且不涉及重大風險的讀檔、寫程式、建立設定、測試、編譯、分析資料、更新文件，都直接執行；不要反覆詢問「要不要繼續」。
2. 每完成一個階段，自行跑測試，發現失敗先診斷修復再繼續；保留簡短進度紀錄。避免無限重試：同一外部阻礙或環境限制連續發生時，記錄並轉做其他可完成工作。
3. 不得偽造 Ground Truth、指標、模型呼叫、專家審查、執行時間、泛化表現、實際部署成果。
4. 不得執行破壞性清理、刪除歷史結果、竄改封存／凍結 artifacts、外傳資料、未授權付費 API 呼叫、公開敏感資料、直接合併 main 或 force push。
5. **真的無法自主解決時才需要問我**：缺少必要檔案／磁碟／運算資源、需要帳號憑證、付費模型授權、涉及新的研究假設而需要我明確取捨、需要人工專家裁決等。提問時一次列出阻礙、已嘗試事項、可選方案、推薦方案；在等待回覆前完成不受影響的項目。
6. 若環境／Cursor session 無法維持無限長工作，保留可恢復的 `STATUS`、版本與下一條執行命令；**不得宣稱可以在 session 結束後自行背景持續工作**。
7. 本研究的最低完成條件：至少能由新事件的模型可見輸入離線產生候選、逐 pair 提出結構化判斷、經 deterministic verifier 驗證、輸出具 evidence ID 的 ledger 與報告；具備通過的單元/端到端測試、B0–B3 對照、獨立 scorer 的可執行框架與真實可用的評估（無 Gold 則如實 `NA`）。若可用的本地 LLM 或 R3/R4 Truth 不可取得，不能假裝論文所有實驗均完成，而應完成可行部分並交出精確 blocker。

## 8. 最後交付報告格式

完成所有可行工作後，以繁體中文提供：

1. **目前完成狀態**：哪些 `DONE`、哪些 `BLOCKED/NA`，不要以「設計完成」代替「實作完成」。
2. **具體檔案與 commit**：新增／修改的相對路徑與 git diff 摘要。
3. **實際執行紀錄**：完整的重現指令、測試通過／失敗數、執行日期、產物 hash。
4. **實驗結果**：只呈現實測數字；獨立操作 Ground Truth、policy consistency、synthetic/challenge tests 分別報告；LLM 結果明確列出本地模型 digest、推論主機類型、參數、實際執行次數、失敗率與耗時。
5. **關聯判定說明**：關聯如何由可見證據判斷、為何能到 R2/R3/R4、矛盾時如何降級/棄答，附最少三個可重播案例。
6. **論文狀態**：PDF 是否編譯成功、剩餘 `TBD`、哪些結論尚不能成立。
7. **阻礙與最小必要決策**：需要使用者提供的資料、權限或實驗授權，以及如果不提供會對論文造成什麼限制。

**請現在開始：先確認當前工作樹與真實 repo 狀態，閱讀上述來源，建立 status 文件，立即進入 Phase 1；按順序完成實作與驗證，不要只回覆研究建議或待辦清單。**
