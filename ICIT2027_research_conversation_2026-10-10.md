# ICIT2027 OT 調查論文研究對話紀錄

- 匯出日期：2026-10-10
- 對話標題：調查論文資料集的異常偵測基線
- 專案目錄：`/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027`
- 對話 ID：`01a0f28b-d529-7043-85e1-d0a91d84f989`

> 本檔只收錄使用者可見的提問與助理最終回覆；不包含系統／開發者指令、內部推理、工具輸出或子代理紀錄。

## 對話

### Turn 1

#### User

[https://arxiv.org/pdf/2504.06102](https://arxiv.org/pdf/2504.06102)

可以幫我調查這篇論文的資料集在2025/2026 有哪些好的研究有用來做Baseline anomaly detection?

#### Assistant

可以。先講結論：截至 **2026-09-30**，Sherlock 還是很新的資料集。若把 anomaly detection 嚴格定義為：

- 只用正常資料訓練；
- 遵循官方時序 train/test；
- 以攻擊事件而非逐列分類評估；
- 回報 Detected Attacks、False Alarms、Time-to-Detection；

那麼目前唯一完整、可直接採用的 baseline，仍是 Sherlock 原始的 CODASPY 2025 論文。2026 有值得引用的後續研究，但尚無新的、成熟且可重現的 Sherlock anomaly baseline。

## 1. 最重要的 baseline：Sherlock 原論文，2025

原論文在 `01-Basic` 上測試五種 process-aware anomaly detector：[Sherlock / CODASPY 2025](https://arxiv.org/abs/2504.06102)。

- **PASAD**：0/18 attacks，1 false alarm，無 TTD。
- **Invariant**：0/18，1 false alarm，無 TTD。
- **Seq2SeqNN**：7/18，10 false alarms，平均 TTD 149.63 秒。
- **SIMPLE**：16/18，33 false alarms，平均 TTD 81.43 秒。
- **GeCo**：15/18，94 false alarms，平均 TTD 75.89 秒。

研究上建議：

- 主要可比 baseline：**SIMPLE、GeCo、Seq2SeqNN**。
- Historical/failure controls：**PASAD、Invariant**。
- SIMPLE 偵測率最高，但 33 個誤報全部由正常維護事件觸發。
- GeCo 最快，但誤報最多。

這些數字有一個很大的限制：作者先大幅移除了受到 switching／maintenance 影響的 signals，才得到上述結果，並明確承認這是現實部署中不可行的理想化設定。另外，Table 1 寫 `01-Basic` 有 17 次攻擊，Table 3 卻以 18 次為分母，屬論文內部不一致。

## 2. 2026 最值得引用的研究

### Loughmari et al., 2026

[*Towards reliable intrusion detection in smart grids: A multiclass, process-aware perspective*](https://journals.sagepub.com/doi/10.1177/18758967261484195) 是目前最有價值的 Sherlock 後續方法學研究。

它比較三種設定：

- unsupervised anomaly detection；
- supervised binary classification；
- supervised multiclass classification。

主要發現是：

- Unsupervised anomaly detection 無法穩定區分攻擊與正常操作異常，原因包括 maintenance/switching 造成的 benign anomalies，以及明顯的 train–test distribution drift。
- Binary classifier 在單一切分看似很好，但交叉驗證 accuracy 會在 35%–96% 間波動。
- Multiclass XGBoost 在 15 類監督式任務達到 `99.81% ± 0.04%`。

這篇很適合用來證明「隨機切分的高 accuracy 不代表可靠異常偵測」。但 `99.81%` 是使用標籤的 supervised upper bound，不是 anomaly-detection baseline；公開頁面也沒有逐一列出 anomaly algorithms、事件級結果或程式碼。

### 2026 ICT Express FDIA survey／實驗

[*A comprehensive survey of false data injection attacks modeling and ML/DL-based detection in smart grids*](https://www.sciencedirect.com/science/article/pii/S2405959526001414) 在 Sherlock 上比較 16 種設定，包括 HMM、GMM、Kalman Filter、RF、XGBoost、LSTM、GRU、LSTM-AE 等。

但它只保留三個量測訊號、時間窗只有 3，結果幾乎全部降到 `AUROC ≈ 0.5`。作者也將此實驗定位為 illustrative，而不是 benchmark-grade comparison。因此它比較適合當：

- feature-ablation failure case；
- intentionally weak negative control；

不適合用作主要 performance baseline。

## 3. 有使用 Sherlock，但不應當 anomaly baseline

- [DeepFM，Scientific Reports 2025](https://www.nature.com/articles/s41598-025-20625-2)：Sherlock accuracy 95.4%、F1 0.955，但採 80/20 supervised binary classification。作者甚至把 unsupervised anomaly detection 列為未來工作，所以只能當 supervised comparator。

- [CNN–GATv2，University of Thi-Qar Journal 2026](https://jutq.utq.edu.iq/index.php/main/article/view/498)：`01-Basic` accuracy 99.92%、F1 98.82%，但使用攻擊標籤與自行設計的 80/20 split，沒有官方事件級指標、03-Rural transfer 或公開程式碼，不能與 SIMPLE／GeCo 直接比較。

因此，看到 95%–99% 的 Sherlock 結果時，要先檢查它是否其實是 supervised row classification；這類數字通常遠高於真正 benign-only anomaly detection。

## 建議你實際採用的 baseline 組合

如果你準備用 Sherlock 做新研究，我建議：

1. **核心 published anomaly baselines**：SIMPLE、GeCo、Seq2SeqNN。
2. **Failure controls**：PASAD、Invariant。
3. **Supervised ceiling**：Loughmari 的 multiclass XGBoost，單獨呈現，不與 anomaly models 混排。
4. **自行補充的現代基線**：Isolation Forest、One-Class SVM、Robust PCA、Autoencoder/LSTM-AE、forecasting-residual model；需註明是你新增的實作，不是既有 Sherlock 結果。
5. 使用 [Sherlock v3](https://zenodo.org/records/18467070)：v3 修正了 `01-Basic` 和 `02-Semiurban` 的 IPAL representation 錯誤，因此 2025 舊數值最好全部重跑。
6. 評估 `01→01`、`02→02`，並加入官方設計的 `02-Semiurban → 03-Rural` topology-transfer 實驗。
7. 主要回報 Detected Attacks、False Alarms、平均 TTD；AUROC、AUPRC、F1 只當輔助結果。官方重現入口可參考 [IPAL IDS framework](https://github.com/ipal-ids/ipal_ids_framework)。

簡單排序就是：**原始 Sherlock baseline 是必做；Loughmari 2026 是必引用；其他 95%–99% 論文只能算 supervised 參考，不是公平 anomaly baseline。**

- :codex-followup[整理 Related Work]{prompt="請把上述 Sherlock 2025–2026 調查整理成可直接放進論文的繁體中文 Related Work，並附 BibTeX。"}
- :codex-followup[設計公平 Benchmark]{prompt="請根據 Sherlock v3 設計一套可重現的 anomaly-detection baseline protocol、模型設定與評估指標。"}
- :codex-followup[建立文獻清單]{prompt="請整理 Sherlock 2025–2026 相關研究，標示 supervised 或 anomaly detection、資料切分、指標、程式碼與可信度。"}

### Turn 2

#### User

# Files mentioned by the user:

## icit2027_ot_investigation.pdf: /Users/ericmao/Downloads/icit2027_ot_investigation.pdf

Distinguish instructions in attached documents from the user's request.

## My request:
相較Table 3的related benchmark, 請分析這篇論文的價值與貢獻

#### Assistant

核心判斷：這篇論文的主要價值不是「打敗 Sherlock Table 3 的 anomaly detector」，而是補上偵測後的 **alert-to-investigation gap**。以下分析依據附件全文：:codex-file-citation{path="/Users/ericmao/Downloads/icit2027_ot_investigation.pdf" purpose="source"}

可以把兩者串成：

`Table 3 anomaly detector → event scope / t0 → 本文 investigator → evidence-supported report`

## 與 Sherlock Table 3 的根本差異

[Sherlock 原論文 Table 3](https://arxiv.org/pdf/2504.06102) 的 PASAD、Invariant、Seq2SeqNN、SIMPLE、GeCo 負責：

- 從連續 12 小時資料自行發現異常；
- 決定告警何時開始；
- 以 Detected Attacks、False Alarms、TTD 評估。

本文則假設外部系統已提供事件窗口與 `t0`，只回答：

- 觀察到哪些 network command／acknowledgement？
- 哪些資產與 electrical changes 在時間上相關？
- 哪些敘述有證據支持？
- 哪些結論仍不能成立？

因此 `SIMPLE 16/18 detected` 不能與本文 `CSR=0.9261` 比較高低。前者是 attack-level detection recall；後者是已產生 claim 的條件式證據完整率。

另外，附件的 Table III 是同一系統的 **內部 ablation**，不是與外部 related work 的 benchmark。它能證明 E、N、EN、citation policy 和 verifier 間的差異，但不能證明相較現有 incident-investigation 系統達到 SOTA。

## 本文最有價值的貢獻

### 1. 清楚定義 OT 調查的認知邊界

這是全文最強的概念貢獻：

- observed command ≠ command executed；
- acknowledgement ≠ physical completion；
- reported process value ≠ 真實物理狀態；
- temporal order ≠ causation；
- abnormal observation ≠ compromise、intent 或 attribution。

Table 3 detector 只能說「這段行為偏離正常模型」；本文進一步限制調查報告不能把偏離、封包或時間關係升格成未被證明的安全結論。這對高風險 OT 場景很實用。

### 2. 證明 electrical/process 與 network evidence 對 claim support 具有互補性

在固定總 retrieval budget 下，EN 的 CSR：

- 相較 E 提高 `+0.1761`，95% CI `[0.1449, 0.2030]`；
- 相較 N 提高 `+0.1856`，95% CI `[0.1480, 0.2208]`。

這是 Table III 最強的實證結果。

但結論應限定為「EN 產生的 claims 有較完整證據」，不能說 EN 全面改善 investigation：

- EN coverage 只明顯高於 N，沒有顯著高於 E；
- Network-only Retrieval Recall 反而最高；
- 所有 view 的 exact gold-fact reconstruction 都是 `0.0000`。

### 3. 量化 deterministic verification 的 support–coverage trade-off

Verifier 將：

- Citation Precision：`0.9949 → 1.0000`
- CSR：`0.9261 → 1.0000`

但同時：

- Coverage：`0.7760 → 0.5278`
- Withholding Recall 只有 `0.3344`
- 完全不發布 security-sensitive substantive claims，因此 V1 的 USCR 是 **NA，不是 0**

所以真正有研究價值的發現不是「verification 達到完美可靠性」，而是：

> Fail-closed evidence verification 可以提高被發布內容的機械一致性，但會犧牲大量有用調查內容。

這個負面結果比單純宣稱 100% precision 更有可信度。

### 4. 實驗控制比一般 LLM security paper 嚴謹

值得肯定的設計包括：

- evaluator gold 不進入 retrieval、generation 或 verification；
- frozen model、prompt、schema 與 decoding；
- verifier 使用 raw G1-EN 的 exact replay，能隔離 verifier 效果；
- 先在 event 內平均 repetitions，再做 event-level paired contrast，避免把 claims 當成獨立樣本；
- 明確將 zero denominator 記為 NA，而不是用 0 美化結果。

## 目前限制論文價值的核心問題

### Exact reconstruction 全為零

這是最嚴重的結果。即使 EN 讓全部 14 個 gold facts「理論上可被證據支持」，平均只 retrieve 到 3.125 個完整支持，最後沒有任何 frozen gold fact 被精確重建。

因此目前能主張的是：

> 產生的部分 claims 有較完整證據。

不能主張：

> 系統成功重建事件或完成 incident investigation。

這也可能代表 exact matcher 太嚴格；論文需要將零分拆成 retrieval miss、generation omission、paraphrase mismatch 與 evidence insufficiency。

### Verifier 的 1.0000 部分是設計保證

Verifier 依 frozen support policy 刪除違規 claims，最後又用同一 policy 評分，因此 1.0000 主要證明 **policy self-consistency**，不是獨立的事實正確性或真實世界安全性。

極端而言，刪除所有 claims 也能獲得完美 precision。應補：

- risk–coverage curve；
- equal-coverage comparison；
- verifier false accept／false reject；
- 獨立或 blinded human adjudication。

### External event scope 可能是 oracle

論文沒有清楚說明 `t0` 與窗口如何產生。如果直接來自 Sherlock event labels，任務會比實際部署簡單很多。

這也代表本文目前不能證明能處理 Table 3 的實務問題，例如：

- SIMPLE 的 maintenance false alarms；
- GeCo 的大量 false alarms；
- 偵測器過早、過晚或過寬的 alarm window；
- missed detection。

### 外部效度不足

目前只有：

- 32 個 preselected events；
- 單一 power-grid dataset；
- 單一模型 snapshot；
- 單一 reviewer、無 inter-annotator agreement；
- 未公布 scenario、attack family、benign/maintenance 組成；
- 無 analyst study 或調查時間／工作量結果。

## 對三項 claimed contributions 的評價

- **Provenance-preserving representation**：工程價值高，但目前沒有 no-provenance ablation，科學證據中等。
- **Structured claims 與 semantic boundaries**：概念貢獻強，也是論文最具 OT 特色的部分；但缺少 free-form baseline 或 analyst usefulness 評估。
- **Deterministic verification with retained coverage**：目前實證最完整的貢獻；應成為全文主軸，但要稱為 evidence-policy verification，而非 truth verification。

## 總評

如果把論文定位為：

> **Sherlock v3 上的 post-alert、evidence-bounded OT investigation measurement study**

那它有清楚且可發表的核心貢獻，尤其是：

1. Table 3 detector 後端的 actionability；
2. E/N evidence 對 claim support 的互補性；
3. verification 所造成的 support–coverage frontier；
4. OT observation 與 execution／causation間的語意界線。

如果定位成「新的 anomaly detector」、「改善 Sherlock Table 3」或「已完成可驗證的自動事件調查」，目前證據不足。

整體評價是：**問題定義強、工程整合強、實驗誠實度高；方法新穎性中等，事件重建與實務驗證仍弱。以目前狀態屬 borderline／major revision，但有明確可補強的發表核心。**

最有影響力的下一步，是讓 SIMPLE 或 GeCo 實際產生 alarm windows，把 true-positive attacks 與 maintenance false alarms 都交給本文系統，再測量是否能避免把正常 switching 誤升格為攻擊結論。這會把目前的 oracle-scoped experiment 提升成真正的 detection-to-investigation pipeline。

- :codex-followup[重寫論文定位]{prompt="根據上述分析，重寫這篇論文的 title、abstract、contributions 與 conclusion，使主張精確落在 post-alert evidence verification。"}
- :codex-followup[設計補強實驗]{prompt="設計一套將 SIMPLE 或 GeCo alarm windows 接到本文 investigator 的端到端實驗，包括 true positives、maintenance false alarms、指標與 ablation。"}
- :codex-followup[模擬 ICIT 審稿]{prompt="以 IEEE ICIT reviewer 格式完整審查這篇論文，提供 strengths、weaknesses、questions、required revisions 與投稿評分。"}

### Turn 3

#### User

重新定位要怎麼鋪陳

#### Assistant

最關鍵的重新定位，是把論文主語從：

> 「我們提出一個可驗證的 OT incident investigation system」

改成：

> 「我們量測 post-alert OT investigation 中，證據完整性與調查涵蓋率之間的取捨。」

也就是不把重點放在「LLM + verifier 架構很新」，而是放在一個明確、尚未被 Table 3 解決的研究問題：

> 異常偵測器發出告警後，系統如何產生有證據支持、又不過度推論的調查結果？加入嚴格驗證後，會犧牲多少有用資訊？

## 建議的故事主線

### 第一幕：Table 3 解決了偵測，但沒有解決調查

Introduction 第一段先承認 anomaly detection 的角色：

- PASAD、SIMPLE、GeCo 等回答「何時偏離正常行為」。
- 但 alarm 不代表 command 已執行。
- acknowledgement 不代表設備完成操作。
- 電氣變化發生在網路事件之後，也不代表兩者具有因果關係。
- detector score 更不能證明 compromise、intent 或 attribution。

建議可直接使用：

> Existing process-aware intrusion detectors identify departures from expected operational behavior, but their alarms do not by themselves establish what occurred. A detected anomaly does not prove that a command was executed, that an acknowledged operation physically completed, or that a subsequent process change was caused by the observed network activity. Incident investigation therefore requires a separate evidence-reasoning stage after detection.

這樣自然把 Table 3 定位成本文的 upstream，而不是 competitor。

### 第二幕：定義新的、範圍有限的任務

接著明確限定本文不是做什麼：

> We study post-alert, event-conditioned investigation. An upstream detector or operator supplies an event scope and temporal anchor; our task is to determine which incident claims are supported by the electrical/process and network evidence visible within that scope.

這裡要反覆強調：

- 不做 continuous detection。
- 不做 unknown-onset discovery。
- 不判斷 attack/benign。
- 不證明真實物理狀態。
- 不做因果推論或 attribution。
- verifier 檢查的是 evidence consistency，不是 universal truth。

論文名稱中的 `Verifiable` 容易被解讀為「驗證事故真相」。較安全的用語是：

- `Evidence-bounded`
- `Evidence-consistency verification`
- `Policy-checked`
- `Post-alert investigation`

我最推薦的標題是：

> **Evidence-Bounded Post-Alert OT Investigation: Cross-View Support and Verification Trade-offs on Sherlock v3**

## 第三幕：把 research gap 寫成 support–coverage 問題

不要把 gap 寫成「LLM 可能 hallucinate，所以加 verifier」。這太一般化。

建議改成三個更具體的未知問題：

1. Electrical/process 與 network evidence 是否能互補，提高 claim support？
2. 強制 citation 是否真的改善完整證據支持，而不只是增加 citation 數量？
3. Deterministic filtering 能提高證據一致性，但會刪掉多少有用調查內容？

對應 RQ 可以改成：

> **RQ1:** Under a fixed retrieval budget, how do electrical/process, network, and combined evidence affect claim support, investigation coverage, and gold-fact reconstruction?

> **RQ2:** Does requiring citations improve complete evidential support without reducing retained investigation content?

> **RQ3:** What support–coverage trade-off results from deterministic publication filtering of generated claims?

第三個 RQ 不要問「verification 是否提高正確性」，因為目前 verifier 和評分共用同一 policy，能證明的是 policy-aligned consistency。

## 第四幕：重新寫 contributions

建議縮成三項，而且每項要與實驗直接對應。

> This work makes three contributions:
>
> 1. We formulate post-alert OT investigation as an evidence-bounded claim-generation task, with explicit semantic boundaries separating observations from execution, physical completion, causation, intent, and attribution.
> 2. We conduct a paired evaluation on 32 Sherlock v3 events to measure how electrical/process and network evidence views affect conditional claim support, retrieval, coverage, and exact reconstruction under a fixed evidence budget.
> 3. We quantify the support–coverage trade-off introduced by citation requirements and deterministic publication filtering, showing that stronger verifier-aligned support is obtained by withholding substantial investigation content.

不要把以下項目單獨宣稱成已驗證的 contribution：

- provenance-preserving representation；
- stable IDs；
- structured JSON；
- deterministic verifier architecture。

它們可以是 design components，但目前沒有 no-provenance、free-form 或 alternative-verifier ablation，無法證明各自的增量效果。

## 第五幕：Results 要先講負面結果

目前最危險的寫法，是先強調 CSR 0.9261 或 verifier 1.0000，之後才提 reconstruction 為零。Reviewer 很容易認為在挑好看的指標。

更可信的結果順序應該是：

1. **Exact reconstruction 全部為零。**
2. 說明 supportability、retrieval、generation、exact matching 是不同階段。
3. EN 提高 conditional CSR，但沒有改善 exact reconstruction。
4. Citation requirement 只建立 CSR 改善，沒有建立 citation precision、coverage 或 USCR 改善。
5. Verifier-aligned support 達到 1.0，但 coverage 明顯下降。
6. 因為 V1 不發布 security-sensitive claims，所以 USCR 是 NA。

核心結果句可以改為：

> Combined evidence did not improve exact gold-fact reconstruction, which remained zero in every view. However, among the substantive claims that were produced, EN yielded higher complete cited support than either single-view condition. Deterministic filtering further eliminated violations detectable by the frozen support policy, but reduced Q1–Q6 coverage from 0.7760 to 0.5278.

這比「combined evidence improves investigation」精確很多。

## 第六幕：把 1.0000 重新解釋為 selective publishing

不要寫：

> Verification produces fully reliable reports.

建議寫：

> Deterministic filtering produced a narrower set of claims that achieved perfect verifier-aligned citation precision and support under the frozen policy. This result reflects selective publication rather than independent truth verification: coverage decreased by 24.83 percentage points, and no security-sensitive substantive assertions remained in the published output.

這樣反而會讓論文更有學術價值，因為它揭露「沉默也能換取完美 precision」。

最好將 Figure 2 改成或補上一張 risk–coverage curve，把 verifier threshold／policy strictness當橫軸，support error 與 retained coverage 當縱軸。這會比單一 V1 operating point 更有說服力。

## 建議的新版 Abstract

> An anomaly alert in an operational technology system does not establish command execution, physical effects, causation, or malicious intent. We study post-alert, event-conditioned investigation, in which an upstream source supplies an event scope and a language model produces evidence-linked claims from electrical/process and network observations. A deterministic policy then checks references, values, units, assets, timing, lineage, and claim-specific evidence requirements.
>
> Using 32 preselected Sherlock v3 events, we compare electrical/process-only, network-only, and combined evidence under a fixed retrieval budget. Exact gold-fact reconstruction remains zero in every view. However, combined evidence increases the conditional Complete-Support Rate to 0.9261, compared with 0.7500 for electrical/process-only and 0.7406 for network-only. Requiring citations increases this rate from 0.8723 to 0.9261. Deterministic filtering raises verifier-aligned citation precision and support to 1.0000, while reducing Q1–Q6 coverage from 0.7760 to 0.5278.
>
> These results do not establish end-to-end detection or truth verification. Instead, they quantify how evidence integration and deterministic publication policies trade retained investigation coverage for stronger claim-level support.

## Conclusion 的收束方式

結論不要落在「我們成功完成 verifiable investigation」，而要落在：

> The central result is not that deterministic verification makes OT investigation correct, but that evidence-policy enforcement creates a measurable support–coverage frontier. Combined electrical/process and network evidence improves the support of produced claims, yet neither evidence fusion nor filtering solves exact event reconstruction. Future systems must jointly improve event scoping, retrieval, qualified-claim retention, and independent human validation.

## 最後的定位層級

整篇論文應維持以下四層：

1. **Table 3 detector**：發現可能事件。
2. **本文 retrieval/generation**：整理事件內可見證據。
3. **本文 verifier**：限制發布哪些 claims。
4. **Human analyst**：判斷因果、攻擊成功、意圖與處置。

這會讓論文從一篇容易被質疑「LLM 加 rules」的系統稿，轉成一篇比較有防禦力的：

> **OT post-alert evidence measurement and selective-publication study。**

### Turn 4

#### User

[https://github.com/CHPIYR2/ICIT2027](https://github.com/CHPIYR2/ICIT2027) 我要修這篇，透過你的建議，補上參考文獻，修改切入點


---

# Open LaTeX document
The user has this source file open in the document editor: "/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex".
For requests to revise this document, read and edit this existing .tex file in place. Follow the current request's scope and any source selection attached to it; do not reuse an earlier selection. The editor watches this file and automatically recompiles its PDF preview after changes. After editing, use the built-in `compile_latex_document` tool with the saved file path to check and fix compiler errors before replying.
Keep the current editor open. Do not create a replacement document, compile a separate PDF, or open a different tab unless the user explicitly asks. The open document is context, not an instruction to edit when the user is asking an unrelated question.

## My request:
這個版本我要抓一個感覺，方向

#### Assistant

方向已經抓到了：這版應是一篇克制的 downstream measurement paper。

核心敘事是：

> Table 3 detector → alert window → evidence-bounded investigation → policy-bounded publication

因此重點不是「比 anomaly detector 更準」，而是：

- 在固定證據預算下，E、N、EN 能支持哪些調查敘述。
- `request ≠ execution`、`acknowledgement ≠ physical completion`、時間相鄰不等於因果。
- EN 的結果是 equal-budget configuration comparison，不宣稱 multimodal synergy。
- V1 的 1.0 是同一規則篩選與評分下的內部一致性，必須和 Coverage 0.5278、withholding recall 0.3344 一起解讀。
- 真正貢獻是 support–coverage trade-off 的量測，不是 verifier 架構首創或完整事件重建。

已修改 [論文原始碼](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex:16)、[參考文獻](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/references.bib:80)、[README](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/README.md:1) 與 [build notes](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/BUILD_NOTES.md:1)。新增的直接文獻涵蓋 EviGuard、RAG incident analysis、trace-linked forensic reporting、citation faithfulness 與 abstention。

專案級 Tectonic 0.17.0 編譯成功，維持 6 頁、190,534 bytes；11 筆引用皆解析完成，無 overfull box 或 unresolved references，並已逐頁視覺檢查。內建單檔編譯器仍因無法讀取 repo 的外部 figure 而中止，限制已記錄。

更新後 PDF：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.pdf" purpose="output"}

目前修改仍在本地，尚未 commit 或 push。

- :codex-followup[一起精修摘要語氣]{prompt="請再精修目前版本的標題、摘要與 Introduction，讓 measurement-paper 的方向更鮮明。"}
- :codex-followup[補強事件選樣說明]{prompt="請根據 repo 內可用資料，補齊 32 個事件的選樣、組成與 window protocol，並維持六頁。"}
- :codex-followup[整理提交到 GitHub]{prompt="請檢查目前 diff，建立 commit 並推送到 GitHub；先不要開 PR。"}

### Turn 5

#### User

參考文獻沒提到benchmark的table 3，會不會讓出發點有點薄弱

#### Assistant

會有一點，但問題不是 bibliography 沒有一筆叫「Table 3」——參考文獻只列論文，不會列其中的表。現在 [Related Work 的 Table 3 敘述](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex:55) 引用 Sherlock，形式上是正確的。

真正偏薄的是：段落點名五個 detector，卻只引用 Sherlock 的彙整實驗，沒有交代五種方法代表的技術脈絡。建議形成三層證據鏈：

1. 用 primary papers 定義上游 detector landscape：

   - [PASAD](https://doi.org/10.1145/3243734.3243781)
   - [Invariant](https://doi.org/10.14722/ndss.2019.23265)
   - [Seq2SeqNN](https://doi.org/10.1007/978-3-030-42048-2_1)
   - [SIMPLE](https://doi.org/10.1007/978-3-031-17143-7_28)
   - [GeCo](https://www.usenix.org/conference/usenixsecurity25/presentation/wolsing)

2. 用 [Sherlock Table 3](https://arxiv.org/pdf/2504.06102) 支撐共同 benchmark setting、detected attacks、false alarms 與 TTD。

3. 緊接著指出 task gap：這些方法輸出的是 alarm；本文研究的是 alarm 之後，哪些 claim 能被證據支持。

建議改成這種語氣：

> Sherlock’s Table 3 provides a common upstream operating-point benchmark spanning departure-based detection, learned invariants, sequence prediction, simple interpretable rules, and comprehensible state-space models [primary references]. It evaluates alarm-level outcomes using detected attacks, false alarms, and time to detection [Sherlock]. These metrics do not determine which post-alert claims are evidentially supportable. We study that downstream gap.

關鍵是稱它為「upstream operating-point benchmark」，而不是本文要超越的 baseline。

如果篇幅只能補兩篇，優先放 SIMPLE 與 GeCo：兩者直接談 meaningful/comprehensible alarms，最容易自然銜接到本文的 actionability 與 evidence-supported claims。不過目前第六頁仍有一些 reference 空間，我傾向五篇都補，論證會完整很多。

### Turn 6

#### User

好，補上後請強化前面的論述，從偵測面的背景來說明此問題已經不少研究著墨，但在後分析的部分，尤其在語言模型上，必須兼顧地端資料

#### Assistant

已完成，論文的切入點現在更扎實：

- 先以 PASAD、Invariant、Seq2SeqNN、SIMPLE、GeCo 說明 OT anomaly detection 已有大量研究；Sherlock Table 3 被明確定位為「上游偵測 operating-point benchmark」，而不是本文下游 CSR/Coverage 的直接 baseline。[NDSS Invariants](https://www.ndss-symposium.org/ndss-paper/a-systematic-framework-to-generate-invariants-for-anomaly-detection-in-industrial-control-systems/)、[USENIX GeCo](https://www.usenix.org/conference/usenixsecurity25/presentation/wolsing)
- 接著把研究缺口收斂為：alarm 能回答「何時告警」，卻不能直接回答「發生了什麼、哪些證據支持、哪些解釋不可成立」。
- 再引入後分析的資料邊界：OT telemetry、封包、設定與資產對應可能揭露廠區架構，因此 LLM workflow 必須能兼容組織控制、地端或斷網環境。[2025 AI–OT 聯合指引](https://www.cyber.gov.au/sites/default/files/2025-12/principles-for-the-secure-integration-of-artificial-intelligence-in-operational-technology.pdf)
- 同時保留科學界線：本文使用公開 Sherlock 資料與固定 hosted model，沒有宣稱已驗證 local LLM；地端性被定位為 deployment constraint 與後續實驗方向。[Dehing et al.](https://research.rug.nl/en/publications/structured-report-generation-using-local-llms-for-chat-based-digi/)

主要修改位於 [Introduction](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex:38)、[Related Work](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex:55) 與 [references.bib](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/references.bib:138)。

最新版共 6 頁、14 筆實際引用，專案編譯成功且已逐頁檢查；沒有 overfull、缺圖或未解析引用。編輯器的單檔編譯器仍因無法載入 `figures/*.pdf` 而失敗，但完整專案 Tectonic build 正常。最新版 PDF：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.pdf" purpose="output"}

- :codex-followup[模擬審稿人攻防]{prompt="請以 ICIT 審稿人角度檢查目前 Introduction、Related Work 與 contribution positioning，列出最可能的拒稿理由並直接修正文稿。"}
- :codex-followup[規劃地端模型實驗]{prompt="請設計一個可加入論文或後續工作的 local-versus-hosted LLM 實驗，包含模型、硬體、資料外流、延遲與 evidence-support metrics。"}
- :codex-followup[整理提交 Git 變更]{prompt="請檢查目前 ICIT2027 的 git diff，整理一個清楚的 commit message，提交並推送到既有 GitHub repository。"}

### Turn 7

#### User

希望這篇與這位教授共作者，口頭有先告知，要先提供論文給他指導，請幫我擬、郵件

#### Assistant

主旨：敬請指導 ICIT 2027 論文初稿暨共同作者邀請

教授您好：

先前曾口頭向您提過，我們正在進行一項關於 OT 資安事件後分析的研究，也希望能邀請您共同參與。目前論文初稿已完成，隨信附上，想先請您撥冗審閱並給予指導。

本研究以 Sherlock 資料集為基礎，將既有異常偵測視為上游環節，進一步探討警報產生後，語言模型如何在電力／製程與網路證據的限制下，形成具證據支持且可稽核的調查結論。我們也特別考量 OT 資料的敏感性，將地端資料治理與受控證據存取納入研究定位。

目前特別希望請教您：

1. 研究切入點與貢獻定位是否清楚；
2. 實驗設計、評估指標與結論是否充分且合理；
3. 與既有 OT anomaly detection 及 LLM incident analysis 研究的區隔是否恰當。

若您認為研究方向合適，我們也誠摯希望邀請您擔任共同作者，並會依照您的建議持續修改，於投稿前再提供完整版本供您確認。

若您方便，我也很樂意另外安排時間，向您簡短說明研究設計與目前結果。感謝您撥冗指導。

敬祝
順心

Eric Mao
AvocadoAI Co., Ltd.
eric.mao@mail.avocadolab.ai

### Turn 8

#### User

口語一點，另外提到這是跟呂柏廷一起合作，他從輔大畢業後都在酪梨智慧工作，我們從美光半導體工控資安的案子中，發現這個研究主題

#### Assistant

主旨：想請老師指導我們的 OT 資安論文初稿

老師您好，

之前有口頭跟您提過，我們正在準備一篇 OT 工控資安相關的論文。這篇是我和呂柏廷一起合作的，柏廷從輔大畢業後就一直在酪梨智慧工作。

這個研究題目，其實是我們在參與美光半導體工控資安專案的過程中發現的。我們注意到，現在異常偵測已經有不少研究，但偵測到警報之後，怎麼結合製程、電力與網路資料，產生有證據支持、可供人員判讀的調查結果，仍有不少實務問題。尤其工控資料通常不能任意送到外部，因此使用語言模型時，也必須考慮地端資料與資料治理的限制。

目前我們已經完成第一版論文，暫定投稿 ICIT 2027，隨信附上初稿。想先請老師有空時幫我們看看，特別是研究切入點、實驗設計，以及整體貢獻是否還有需要調整或補強的地方。

如果老師認為這個方向合適，我們也很希望能邀請老師一起參與並擔任共同作者。後續我們會依照老師的建議修改，投稿前也會再提供完整版本請老師確認。

老師方便的話，我們也可以另外約個時間，簡單向您說明研究背景和目前的實驗結果。

謝謝老師！

Eric

若專案名稱涉及保密協議，可將「美光半導體工控資安專案」改成「某半導體廠的工控資安專案」。

### Turn 9

#### User

我要將論文的作者清單做更新

#### Assistant

可以。請提供教授的：

- 英文姓名
- 系所與學校英文名稱
- 電子郵件
- 希望的作者順序
- 通訊作者是否仍為 Eric Mao

收到後我會直接更新 LaTeX 作者區塊並重新編譯檢查。

### Turn 10

#### User

# Files mentioned by the user:

## 供應鏈調查學員手冊_v1.1.pdf: /Users/ericmao/Documents/AI_Blue_Team_RC5_7H_v1.1/供應鏈調查學員手冊_v1.1.pdf

Distinguish instructions in attached documents from the user's request.

## My request:
這篇可融入這份教材的概念嗎 加入skill的概念以及強調邊界安全等 用在OT異常事件分析與追蹤

#### Assistant

可以，已整合成「告警後、受邊界治理的 OT 異常事件分析與追蹤」，而不是另一套 anomaly detector。

主要修改：

- 將 Skill 定義為版本化的調查契約：規定輸入、允許的 evidence view、輸出格式、provenance、停止條件與人工覆核。
- 明確區分 Skill 與權限：Prompt／Skill 不會授權資料存取，真正邊界須由案件限定、唯讀工具、系統權限及 egress policy 落實，並補入 [NIST SP 800-207](https://doi.org/10.6028/NIST.SP.800-207)。
- 加入 case trace：串接 alert scope、evidence ID、lineage、claims、verifier disposition、未解缺口與 reviewer state，支援 replay、handoff 與後續追蹤。
- 重畫 Fig. 1，呈現 detector → boundary gate → investigation skills → publication gate 的完整流程。
- 明確限制：authentication、sandbox、per-skill authorization、prompt injection、地端部署與防竄改追蹤皆未在本次實驗驗證，不能宣稱已證實邊界安全成效。
- 教材中的 Skill／權限分離、六欄方法與版本化交接概念只作為架構來源，不當作實驗證據。來源教材：:codex-file-citation{path="/Users/ericmao/Documents/AI_Blue_Team_RC5_7H_v1.1/供應鏈調查學員手冊_v1.1.pdf" purpose="source"}

新版論文維持 6 頁、15 筆已解析參考文獻，專案編譯成功且逐頁檢查無裁切或重疊：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.pdf" purpose="output"}。更新後的向量架構圖：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/figures/figure1_system_architecture.pdf" purpose="output"}

內建單檔編譯器因無法載入 `figures/*.pdf` 而失敗；完整專案 Tectonic 編譯正常，僅剩兩個無害的 underfull-box 警告。

- :codex-followup[檢查論文措辭]{prompt="逐段審視 skill 與 boundary security 的措辭，找出 reviewer 可能質疑為未實驗主張的句子並提出修訂。"}
- :codex-followup[設計後續實驗]{prompt="把 per-skill authorization、local LLM、egress control 與 tamper-evident case trace 轉成可執行的第二階段實驗設計與指標。"}
- :codex-followup[準備教授說明稿]{prompt="根據新版論文整理一頁中文說明，解釋教材概念如何轉化成論文架構、哪些已驗證、哪些屬於 future work。"}

### Turn 11

#### User

請以審稿者的方式來評估哪裡不足


---

如何評估，有建議嗎感覺這部分很重要, 現在的baseline是不是仍需要oracle?

#### Assistant

是，**目前 D0、G0、G1、V1 都仍依賴 oracle-like 的 event scope 與 \(t_0\)**。但這不代表實驗無效；關鍵在於你要回答哪一個問題。

- 若研究問題是「固定事件窗口後，哪種證據視圖與生成方法較好」，oracle 可以保留，而且所有 baseline 應共用同一組 oracle 輸入，才能公平比較。
- 若要主張「實際 detector 告警後的分析效益」或 end-to-end value，目前設計就不夠，因為 detector 的延遲、錯誤窗口與 false positives 都被排除了。

也就是說，D0 仍可使用 oracle；baseline 不必是 oracle-free。但它應被稱為 **oracle-conditioned downstream baseline**，而不是 operational detector baseline。

### 最建議的評估設計

1. 保留現在的 O0 控制組

   所有方法共用完全相同的 \(W_e,t_0\)：

   - D0 deterministic/template baseline
   - raw LLM
   - citation-required LLM
   - verified LLM

   Gold facts 只能用於評分，不能參與 retrieval、prompt 或 verifier。

2. 新增低成本的 O1 window sensitivity

   不必先整合 detector，可以直接擾動現有 32 個事件：

   - \(t_0\) 前後平移，例如 \(\pm0.25L\)、\(\pm0.5L\)
   - window width 測試 \(0.5L, 1L, 2L\)
   - retrieval budget 仍固定 64 records

   這會直接回答：

   - 結論是否只在精準 oracle window 下成立？
   - window 太晚時會遺失多少關鍵事實？
   - window 太寬時是否因 evidence dilution 降低 support？

3. 再加入 O2/O3 detector-generated windows

   選一個可重現、threshold 已凍結的 detector：

   - 以 detector 真正的 alarm timestamp 建立 \(t_0\)
   - 事先固定 pre/post window 和 alarm merging 規則
   - 納入全部 true-positive windows
   - 同時納入 false-positive／benign windows
   - 不允許人工依 gold 修正窗口

   Sherlock Table 3 的彙總 detection rate、false alarm 與 detection time **不能直接變成 downstream baseline**；必須取得逐告警時間戳或重新執行 detector，才能把輸出真正傳入後分析流程。

### 建議新增的指標

除了 CSR 與 Coverage，至少補：

- `Window Evidence Recall`：完整事件中可支持的事實，有多少證據仍落在輸入窗口內。
- `Oracle Gap`：\(M_{\text{detector/perturbed}}-M_{\text{oracle}}\)。
- Semantic fact recall：因為目前 exact completeness 全為 0。
- False-alert unsafe escalation rate：benign／FP window 被錯誤升級為攻擊結論的比例。
- Correct insufficient/withholding rate：證據不足時是否正確拒絕下結論。
- 每 100 個 detector alerts 產生的報告與人工審查負擔。

### 對這一版最實際的決策

如果時間有限，我建議：

1. 保留 oracle 主實驗。
2. 把 D0 升格成正式 baseline。
3. 增加 window perturbation sensitivity。
4. 把論文主張限定為：

> conditional on a supplied event scope and time anchor.

5. 將 detector-generated TP/FP windows 列為下一階段；除非你仍想主張 operational/end-to-end effectiveness，那它就必須在本篇實作。

Oracle 不是目前最致命的缺陷；在你已經明確限定 post-alert conditional measurement 的情況下，它可以被防守。更致命的仍是 verifier–scorer circularity、單一 reviewer，以及 exact reconstruction 全為零。審查依據為目前 PDF：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.pdf" purpose="source"}

我已把「O0–O4 oracle 評估階梯」補進[完整審稿評估畫布](/Users/ericmao/.cursor/projects/empty-window/canvases/icit2027-review.canvas.tsx)。這類 baseline、oracle 與修訂優先級的關係較適合放在可反覆查看的視覺化分析中。

- :codex-followup[設計 oracle sensitivity 實驗]{prompt="依目前 32 個事件與 retrieval budget，設計可直接執行的 t0/window perturbation 實驗、條件矩陣、指標與統計分析。"}
- :codex-followup[重寫方法與限制段落]{prompt="把 oracle-conditioned estimand、baseline 定位與 detector-generated windows 的界線寫進論文 Methodology、Discussion 與 Limitations。"}
- :codex-followup[規劃 detector baseline]{prompt="依 Sherlock 可取得的 detector 實作與逐告警輸出，規劃 TP/FP window 傳入後分析流程的最低成本實驗。"}

### Turn 12

#### User

是否優先修改verifier–scorer circularity、單一 reviewer，以及 exact reconstruction 全為零

#### Assistant

是，這三項應優先於 oracle sensitivity、local model、boundary security 與擴充 detector baseline，因為它們直接影響目前結論是否成立。

建議合併成一個補強工作包，而不是分開處理：

1. 先處理 verifier–scorer circularity

立即修改論述：

- RQ3 改成「policy consistency and retention trade-off」。
- V1 的 CSR／Citation Precision = 1.0 不再寫成 verifier effectiveness。
- 強調它證明的是 construction consistency，不是 factual correctness。

再增加獨立驗證：

- 第二位 reviewer 在不知道 V1 disposition 的情況下，判斷 raw 與 retained claims 是否受支持。
- 報 verifier 的 false acceptance、false withholding、sensitivity、specificity。
- 可用正確 claim 做數值、單位、asset、timestamp、citation-ID 擾動，建立已知違規 challenge set；這不必重跑 LLM。

2. 同時解決 exact reconstruction 全為零

不要刪除或放寬 exact metric，而是把它保留為最嚴格指標，再新增語義層級：

- Exact match
- Semantic equivalent
- Partial but correct
- Unsupported／incorrect
- Absent

核心輸出改成：

> supportable → retrieved → mentioned → semantically matched → exactly matched

這樣才能判斷目前的零分究竟代表：

- 模型真的沒有重建事實；或
- 內容大致正確，但 exact schema／數值／措辭要求產生 floor effect。

若 semantic recall 仍很低，就應把論文定位成「supported claim generation」，不要再稱 reconstruction。

3. 用同一位第二 reviewer 解決 single-reviewer 問題

最低可接受方案：

- 分層抽取 20–30% 的完整事件，而不是零散 claims。
- 涵蓋 E／N／EN、raw／V1、不同 scenario、cyber／benign。
- 對 condition、prompt 類型及 verifier disposition 盲化。
- 同時評 semantic reconstruction 與 claim support。
- 報百分比一致率，以及適合不平衡標籤的 agreement 指標。
- 說明 disagreement adjudication，但保留 adjudication 前的原始一致率。

最理想則是讓 reviewer 2 評完全部 32 個事件的 gold-fact semantic matching；claim-level support 可以只做分層子集。

優先順序可簡化為：

1. 立即重寫 RQ3 與結論，停止把 1.0 當成有效性證據。
2. 設計盲化 semantic-matching rubric。
3. 第二 reviewer 執行 semantic matching 與獨立 support review。
4. 加 verifier challenge set／gate ablation。
5. 完成這些後，再做 D0 baseline、matched-budget 與 oracle sensitivity。

如果只能做一件新增評估，我會選擇：

> 第二位盲化 reviewer 對 gold facts 做 semantic reconstruction，並獨立重評 raw／retained claims。

它可以一次回應三個最致命的審稿問題，也是最有可能把 Weak Reject 推向 Borderline／Weak Accept 的補強。

### Turn 13

#### User

這篇論文核心邏輯有沒有缺失？

#### Assistant

有一個核心邏輯缺口，但不是整篇無法成立：

> 論文目前從「個別 claim 符合作者定義的 support policy」，跳到了「形成有價值且安全的 OT 事件調查」。

中間缺少獨立證據證明這些 claims 同時具備正確性、完整性與分析價值。

### 目前論證鏈的斷點

1. 研究問題與主要結果不一致

RQ1 接近「事件重建」，但 Exact／View-Conditional Completeness 全為 0。論文隨後以 CSR 作為主要正向結果。

但兩者不同：

- Completeness 問：「應該找到的事實有沒有找到？」
- CSR 問：「模型選擇說出的內容中，有多少符合 support policy？」

模型只說少量簡單事實，也可能得到很高 CSR。因此高 CSR 不能證明成功重建事件。

2. Verifier 證明的是規則一致，不是真實有效性

目前是：

> 同一 policy 過濾 claims → 同一 policy 再評分 retained claims → 得到 1.0

這最多證明 verifier 按規則執行，不能證明：

- policy 本身正確；
- retained claims 符合真實世界；
- 被刪除的 claims 都應該刪除；
- 報告對分析人員仍然有用。

3. Supported claims 不等於 useful investigation

論文缺少由分析人員或固定 gold opportunities 所定義的效用層：

- 是否找出關鍵事件？
- 是否保留決策所需資訊？
- 是否協助下一步查證？
- 是否正確區分 benign、uncertain 與 security-relevant event？

Coverage 嘗試補這個缺口，但 Q1–Q6 是作者內部定義，尚未證明等同 analyst utility。

4. Evidence-view 結果不能完全歸因於 evidence modality

E64、N64、EN32+32 同時改變 modality、quota 與資訊密度。因此目前只能說：

> 這三種固定配置產生不同結果。

不能直接說：

> 結合 cyber／physical evidence 造成較佳調查品質。

5. 問題動機比實驗範圍更大

前面談到：

- 地端資料不能外流；
- boundary security；
- investigation skills；
- detector-to-investigation handoff。

但實驗實際使用 public data、hosted model、oracle-like window，而且沒有存取控制與安全測試。這些適合當 deployment implications，不宜形成核心貢獻。

### 可以成立的核心邏輯

建議把中心命題縮成：

> 在外部提供的事件窗口中，不同 evidence-view allocation 會改變模型能提出並由可見證據支持的 claim portfolio；deterministic publication policy 可以提升 policy consistency，但會犧牲 retained investigative content。本研究測量這項 trade-off，而不是證明完整事件重建或 verifier factual correctness。

這條論證與目前數據是一致的，而且相對容易防守。

### 建議重建的證據鏈

1. 外部提供固定 scope 與 \(t_0\)。
2. 測量每個 view 中哪些 gold facts 原本可支持。
3. 測量 retrieval 實際取得多少。
4. 由盲化 reviewer 評估 exact、semantic、partial、absent。
5. 獨立評估 raw claims 是否受支持。
6. 執行 verifier。
7. 再由同一套獨立評估比較：
   - unsupported claims 減少多少；
   - supported facts 保留多少；
   - useful investigation questions 保留多少；
   - false withholding 增加多少。

目前最缺的是第 4、5、7 步。

因此，這篇不是「核心想法錯誤」，而是「證據鏈尚未連到較大的結論」。只要將主張縮到 controlled measurement，並補上獨立 semantic/support/utility evaluation，核心邏輯可以完整成立。

### Turn 14

#### User

請依照此針對全文進行修正

#### Assistant

已依照核心邏輯檢討完成全文修訂：[LaTeX 原始碼](/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/icit2027_ot_investigation.tex:16)。

主要調整包括：

- 重新定位為「偵測後、oracle-conditioned 的 OT 調查評估」，不再暗示是新偵測器或獨立 verifier。
- 將指標統一為 `Q1–Q6 Substantive Coverage`，並補齊 CSR、USCR、Citation Precision、Withholding 的分母與判定單位。
- 明確揭露 exact reconstruction 全為零、單一 R1 reviewer、same-policy circularity，以及沒有 relaxed semantic matching。
- 區分完整 eligible evidence view 與實際 64-record model-visible bundle。
- 補充事件選樣、資料分層、prompt variants、模型設定、缺失 repetition、finite-set estimand 與 bootstrap 的解釋邊界。
- 將 Sherlock Table 3 定位為上游偵測參考，不冒充本文方法 baseline。
- 強化 EviGuard、Cadet、Cognitive SOC、Dehing、Wallat 等相關研究的差異化論述。
- 修正 Figure 1 的 `ground truth/gold` 用語，改為 evaluator references，並保留外部 anomaly detectors：:codex-file-citation{path="/Users/ericmao/Documents/ChatGPT/Courses/ICIT2027/figures/figure1_system_architecture.pdf" purpose="output"}

驗證結果：

- Codex LaTeX editor 編譯成功。
- 完整圖檔與 bibliography 建置為 8 頁、19 篇參考文獻，沒有未解析引用或 overfull box。
- Tectonic 仍有 Times 字型替代警告；投稿前應使用正式 IEEE pdfLaTeX/BibTeX workflow 與 PDF eXpress 檢查。
- 若會議限制為 6 頁，還需要獨立做一次篇幅壓縮，目前沒有為了頁數刪減關鍵限制與方法定義。

- :codex-followup[壓縮成六頁版本]{prompt="請在不犧牲核心方法定義與限制的前提下，將目前論文壓縮成 IEEE 六頁版本，並改善 Table III 與 Figure 1 的可讀性。"}
- :codex-followup[設計第二 reviewer 評估]{prompt="請依目前論文設計第二位 blinded reviewer 與 relaxed semantic matching 的最小追加實驗及標註表。"}
- :codex-followup[模擬正式審稿]{prompt="請針對目前修訂版進行一次正式 IEEE reviewer-style 審查，給出 accept、weak accept、weak reject 或 reject 與必要修改。"}

### Turn 15

#### User

會不會太複雜概念，請幫我評估

#### Assistant

會。以第一次閱讀的審稿者來看，目前不是方法本身太複雜，而是同時出現太多「看起來都像核心貢獻」的概念：

- OT anomaly detection 與 Table 3 benchmarks
- oracle-conditioned alert scope
- E/N/EN evidence views
- retrieval budget
- investigation skill
- boundary security、case trace、zero trust
- LLM citation requirement
- deterministic publication filter
- exact reconstruction、CSR、Coverage、USCR、Withholding 等多組指標
- local deployment 與資料治理

審稿者可能讀完後仍不確定：這篇究竟是在做 evidence-view benchmark、LLM investigation framework，還是安全 publication gate？

真正核心其實可以濃縮成一句：

> Given a fixed alert window, does combining process and network evidence help an LLM produce better-supported OT investigation claims, and how much substantive content is lost when unsupported claims are filtered?

中文就是：

> 在固定的異常事件範圍內，結合製程與網路證據是否能產生更有依據的 OT 調查結論？而為了移除證據不足的結論，需要犧牲多少調查內容？

建議只保留三層主線：

1. 上游偵測器提供事件範圍，但不在本文評估。
2. 比較 E、N、EN 三種固定預算 evidence views。
3. 對生成結果套用 publication filter，觀察 support 提升與 coverage 下降。

指標也應分層，不要全部等量呈現：

- 主要結果：Protocol-Exact Fact Recall、CSR、Substantive Coverage。
- 過程診斷：Retrieval Recall、Citation Precision。
- 安全性補充：USCR、Required Withholding Recall/Precision。

其中 exact recall 全為零反而要成為清楚的論述：

> 系統能產生較受證據支持的局部結論，但尚不能重建預先定義的完整事件事實。

這句比同時解釋九種 metric 更容易讓審稿者記住。

最應該降級的內容是：

- investigation skill
- case trace
- boundary gate
- zero-trust/local deployment
- authorization、egress、sandboxing

這些概念可以保留，但應集中成 Discussion 裡一段「Deployment Implications」。因為目前沒有實驗驗證它們，放在主架構中央會讓審稿者以為本文還宣稱一套 production security architecture。

RQ 也可以收斂：

- RQ1：固定預算下，E/N/EN 對 recall、support、coverage 有何差異？
- RQ2：要求 citation 是否改變 claim support？——定位成 ablation，不必當主要貢獻。
- RQ3：publication filtering 移除了哪些 policy violations，又犧牲多少 coverage？

我的整體判斷是：

- 科學問題：清楚，而且有價值。
- 實驗設計：不算過度複雜。
- 名詞與評估概念：目前偏多。
- 最大風險：審稿者把它看成「多個未完整驗證的概念拼在一起」。
- 最佳定位：不是完整 OT investigation architecture，而是「固定警報範圍下的 evidence-view 與 selective-publication measurement study」。

如果以投稿優先順序來看，我會先做三件事：

1. 簡化 Figure 1，只留下 supplied alert → evidence view → generation → filtering → evaluation。
2. 把 skill、boundary security、case trace 移到 Discussion。
3. 將結果表收斂到三個主要指標，其餘標成 diagnostic metrics。

這樣不只概念更集中，也有機會把目前八頁壓回六至七頁。

### Turn 16

#### User

將此對話會出md

#### Assistant

已將本對話匯出為 Markdown，保留使用者提問與助理最終回覆，並排除系統指令、內部推理與工具紀錄。

## 目前研究產出

- 論文原始碼：[`icit2027_ot_investigation.tex`](./icit2027_ot_investigation.tex)
- 參考文獻：[`references.bib`](./references.bib)
- Figure 1：[`figures/figure1_system_architecture.pdf`](./figures/figure1_system_architecture.pdf)
- Figure 1 產生程式：[`scripts/generate_figure1_system_architecture.py`](./scripts/generate_figure1_system_architecture.py)
