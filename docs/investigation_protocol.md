# Investigation protocol v1 — 提案，尚未凍結

對應 RQ1/RQ2/RQ3；沿用 [-60,+60) 秒、主 PCAP、opaque event IDs、E/N/M/G 契約。
先以 N-FULL 的准許語意進行 investigation；不將先前 observability T45 等條件一起擴成主矩陣。
分類器輸出、feature importance、attack family、classifier probabilities 不放進 LLM 或 retrieval。
同一事件使用同一問題、同一總 evidence 預算；E-only、N-only、EN 只改可見證據。

## 固定問題 Q1–Q7

1. Q1：事件視窗中觀察到哪些網路活動、命令型 request 或 protocol response？
2. Q2：觀察到哪些電氣／製程回報值或可計算的回報變化？
3. Q3：哪些 observed assets、channels 或 network endpoints 涉及上述觀測？哪些對應未知？
4. Q4：依捕獲時間，可建立什麼事件時間線？
5. Q5：網路活動與電氣／製程觀測之間有哪些可支持的時間關聯？請分開時間關聯與因果。
6. Q6：哪些具體觀測值得安全調查？證據支持的解釋到哪一層為止？
7. Q7：在目前可見證據下，哪些結論仍不能成立，缺少什麼支援？

不含 gold narrative、family、attack label、playbook。E-only 問 Q1 等也不能偷換成另一套簡單問題。

## Retrieval 與公平性提案

先做可重現的 structured retrieval，不引進 embedding/vector DB。keys 僅 event scope、可見 asset/channel、
capture time、允許的 protocol activity、quality-valid reported differences；不能拿 G 或 classification score 排名。
所有引用都是原始 structured observations 或可回溯原始 records 的明列 derived query receipts，不只 ML vectors。

候選固定總上限 64 個 evidence entries：E-only 64E；N-only 64N；EN 32E+32N，不跨來源挪用剩餘額度。
M/scope manifest 一律必要且單獨列大小；證據序列化上限 48,000 UTF-8 bytes，需額外 tokenizer 檢查。
這不是 token 預算的替代，模型選定後將實際 token 上限寫入 retrieval config，再 freeze。
超過上限依穩定 priority 截斷並保存 omitted counts；不依任何模型輸出調整 retrieval。

N 優先保留每種 activity 的代表、request、各種 response、interval gaps 的邊界與 receipt，
再以固定 time bins/opaque ID 排序填入。E 優先每個 numeric family 的有資料 channel、有效前後 pair、
state observation 與 missing/quality 情形，避免只選最大變化；依 family quota、時間與 ID 穩定選取。
每個 delta 必須能回到精確原始 pair；aggregate 完整父集合可用私有索引+content hash 保存。
上述細部 quota 在 Basic pilot 完善並版本化；不能於 final eval 後換 ranking。這是正式 freeze 前待補的工程項目。

同一 event/view 的 retrieval bundle 在 B0–B4 完全相同。保存 eligible universe、retrieved IDs、
field mask、derived query、cutoff、排序、budget、truncation、input hash。absence/gap 一律基於完整可見 query，
不是從 top-k 缺席推論；query 只描述 capture，不能證明 sensor health 或不存在未捕獲流量。

EN 每個來源份額較少是固定總預算的代價；同時報 retrieval recall、各 source token/entries，
不把 retrieval 壓縮造成的差異全歸因 LLM 或 evidence modality。無預算控制的 EN union 不當主實驗。

## G. 精確 baseline matrix

| Baseline | E/N/EN（各一格） | LLM | Citation | Verifier | Sufficiency |
|---|---|---|---|---|---|
| B0 | ✓ / ✓ / ✓ | 無 | 每列原始或 derived evidence ID | 僅資料 schema/provenance，沒有 LLM claim filter | 無；不產生安全判斷 |
| B1 | ✓ / ✓ / ✓ | 一個固定模型／snapshot | 選填；輸出仍是相同 typed JSON | 無 | 不強制；可自行標不足 |
| B2 | ✓ / ✓ / ✓ | 與 B1 相同 | substantive claims 強制 citations，或明確不足 | 無 | 不強制；可自行標不足 |
| B3 | ✓ / ✓ / ✓ | 重放同一 B2 輸出 | 同 B2 | 八項 deterministic checks；只發佈支援或較弱 canonical 語句 | 無 question-level obligation |
| B4 | ✓ / ✓ / ✓ | 重放同一 B2/B3 輸出 | 同 B2 | 同 B3 | 每題最低支持組、qualify/withhold 與缺證理由 |

B0 時間線可按 claim schema 表達其機械可建立的觀測與變化；不補 security narrative。
B1/B2 固定相同系統角色、問題、輸入排序、claim/token caps，僅引用要求不同。
B3/B4 不重新生成或 silent repair。保留 raw、parsed、verifier output、final presentation 四層。
由於 B3 包含規則檢查與 canonical rendering，B2→B3 的效果屬於這個完整驗證／發佈步驟，
不能全部歸因某一條 verifier rule，也不能宣稱已驗證任意自然語言的真偽。逐 claim 紀錄
rule failure、保留的 typed content 與文字改寫，讓讀者看出減少 overclaim 是透過拒絕、降格或重寫。

B3 claim-level withholding 與 B4 question-level sufficiency 不混同：B3 可以留下孤立 supported fragments；
B4 必須告知整題是否有足夠 support。Q1 需至少一項 network fact，Q2 需有效 E fact（要說變化則需 pair），
Q3 需 observed record+mapping 或 endpoint pair，Q4 需至少兩個不同 capture time 的 observation，
Q5 需 N/E 各一個 supported observation 且可定先後／同時，Q6 需具體 supported indicator 且無更強 overclaim；
未達要求則明列不足，不能自動補成 benign。Q7 統一列出尚未支持的結論與 reason。
問題的人工 gold answerability 決定上述政策是否正確，不由 B4 自己宣告成功。

評估提案 32 events × 3 views × 5 baselines = 480 event-condition cells。
B1/B2 各做預定 3 次生成以量測穩定性：192 distinct generation settings，共 576 model calls（不含開發與 API transport retry）。
B3/B4 同步重放三次 B2；B0 每個 event/view 一次；共有 1,248 份 report artifacts，統計樣本仍是 32 events。
API 暫時失敗只准以相同 payload retry 並記錄；schema invalid、拒答、截斷均保留為失敗，不能反覆生成直到好看。

未定而必須補齊才能 freeze：模型/provider/snapshot、sampling params/seed 支援、actual context/output token caps、
retrieval 具體 type quotas、reviewer 名單、gold adjudication。不得在這些空白時宣稱 protocol 已凍結。
不在未核准前送任何資料給 LLM provider。

## H. Metrics 與精確分母

記 event 為 e、view 為 v、run 為 r。人審的有限 gold fact 集為 G_e（完整 EN 可見條件下的主 benchmark）；
G_ev 為其中在 view v 可被支持的子集。這是明列的 salient fact benchmark，不聲稱窮盡 raw capture 全部事實。
每個 gold 有 alternatives of minimal support sets。取得其中一組完整支援且語意／數值／scope 正確才 recovered；
每 gold 最多記 1 次，重複 claim／alias 不加分。單個 claim 有多個原子主張先拆開，禁止靠長句稀釋錯誤。

| Metric | 分子 / 分母 | 特殊處理 |
|---|---|---|
| Citation precision | 實際支援其 claim 中指定角色、可見且存在的 (atomic claim, evidence ID) 對 / 所有聲稱的 citation 對 | 錯 ID、hidden、無關皆入分母；同 claim 重複 ID 去重；單 ID 不必單獨證明整條多證據 claim |
| Complete-support rate（伴隨 citation 指標） | citation set 足以共同支持整個 atomic claim 的 asserted claims / 所有 asserted substantive claims | 防止每個 ID 各有關係但合起來仍缺關鍵前提；B1 缺 citation 不能靠 evaluator 補引用得分 |
| Evidence completeness，主 RQ1 | 正確 recovered 的 G_e facts / \|G_e\| | 三 views 使用相同 EN-gold 分母，量測跨域重建總量；有缺 view 的合理上限 |
| View-conditional completeness | 正確 recovered 的 G_ev facts / \|G_ev\| | 控制該 view 的 answerability，與主分母並列；不能只報此值而掩蓋單來源缺領域 |
| Unsupported security-claim rate | 未被可見證據支持的 asserted security-indicator/interpretation 與任何位置的安全／因果／意圖主張 / 所有 asserted substantive security claims | 人審整個 raw/final 文本，防止改 claim_type 逃避；合理 unknown 不進分母；qualified 只評其實際保留的 assertion |
| Numerical accuracy | 值／差／比例與單位、pair、scope 均正確的 numeric assertions / 所有 numeric assertions | 沒數字則 NA；物理未量測值或不合法百分比為錯誤 |
| Asset consistency | 映射／endpoint role 正確的 asset relationship assertions / 全部這類 assertions | null asset 不是可任意匹配；M 的全場 asset 清單不算 involved |
| Temporal consistency | 支持其聲稱 order/equality/delta 的 temporal assertions / 全部 temporal assertions | 同 capture time 不代表真實同時；無測量時間不得聲稱 actuation chronology |
| Required withholding recall | gold 判應 qualify/withhold 且系統作出正確 action+reason 的固定機會 / 全部 gold insufficient/qualification opportunities | Q1–Q7+預定 guardrail opportunities；不是只評模型主動提到的項目 |
| Withholding precision | 人審認為確實需要其 action 的 explicit qualify/withhold 決定 / 全部此類決定 | 有足夠證據卻全拒答會降低此值；reason 錯也不算對 |
| Action accuracy | 在固定機會集合上正確 supported/qualified/withheld action / 全部固定機會 | 同時分層報 answerable、partial、unanswerable，不只總 accuracy |
| Substantive question coverage | Q1–Q6 中至少一項正確、非空、滿足問題最低支持的 supported/qualified answer 數 / 6 | 一題最多一次；Q7 的 unknown 不當實質調查覆蓋；全拒答為 0 |
| Retrieval recall | 至少有一組完整支援被 retrieval 的 G_ev facts / \|G_ev\| | 與 final completeness 分開，定位 retrieval failure |
| Schema compliance | 可解析且符合 schema+跨欄位 constraints 的 reports / 全部嘗試 reports | 截斷/invalid 不丟棄；調查 coverage=0，失敗率另列；raw security statements 仍做人審風險評分 |

所有比率分母=0 記 NA 並報 numerator/denominator、eligible events/runs。unsupported security claim
完全沒生成時不是 error-rate=0 的勝利；其該率 NA，連同 security coverage、claim count、整體 coverage 呈現。
正確但沒 citation 的 B1 fact 可由盲化 reviewer 對 bundle 確认內容而計入「內容 completeness」，
但不能计入 cited complete-support；兩者要分欄，避免把 B1 無引用直接定義為所有內容錯誤。

B3/B4 security risk 分別評原始 B2 和最終發布層，並報哪些不支持的主張被保留／刪除、哪些原本支持的被誤拒。
gold/人工評估獨立於 verifier status；不得以被 verifier 標 SUPPORTED 的數目當引用精確率。

## Coverage–reliability 與統計

主表每格同時給 completeness、Q1–Q6 coverage、unsupported rate 和各分母。
畫 coverage vs unsupported-rate 點圖，B0–B4 各點；不掃未註冊 threshold 產生最佳曲線。
額外 all-withhold sanity control：實質 coverage=0、security-rate=NA；不是優勝 baseline。

每 event/view/baseline 先平均三個 run 的 metric（只對有定義的 run，另報有定義 run 數），再對事件做 macro。
同時提供 pooled micro 計數，不能以 claim-rich 事件取代 event-level 主分析。
配對差使用同 event、view、run index；對 citation 等不同 eligible 集合只比較共同有定義事件，報 n。
固定 2,000 次、seed=20270922、scenario 分層 event bootstrap；三個 run、claims、packets 不是獨立樣本。
CI 僅條件於本已觀察場景；不以三份 evaluation recording 宣稱跨 simulation 的推論或 robust cluster CI。
報 family/scenario 分層與全部矩陣，不以多重比較中的最佳格作主要結果。

## 工程 tests 與後續小型 failure suite

最低測試：未知／跨 episode citation、view-hidden citation、未 retrieval citation、asset mismatch、
unit mismatch、zero-baseline percent、future record、同 timestamp ordering、壞 parent、刪 p 後 E 後代、
COT=7 不能當 physical execution、command→process order 不能當 causality、top-k 缺席不能當 gap、
自由文本 overclaim 不能隨 typed payload 被整句放行。

核心穩定後才定義缺 E、缺 N、retrieval failure、stale observation、錯 ID、synthetic conflict；
固定 paired perturbations 與受影響 IDs，和真實 Sherlock event results 分表。不冒稱合成衝突為真攻擊。
