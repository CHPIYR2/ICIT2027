# Cursor 交接：MIRAGE-OT 全新專案 v0.1

## 已完成的工作（本包）

- **從零開始的獨立程式**；沒有任何 EBRL 源碼、攻擊分類規則或舊測試結果。
- Python 套件 `mirage_ot`，支援 PCAP（標準 Ethernet/IPv4/TCP/ARP 限定）、
  Sherlock/IPAL `.state.gz` 串流讀取，以及 ZIP 成員讀取，無需解開巨型 ZIP。
- 多模態事件時間網格：Network Flow、IEC104 網路回報電氣量測；可追溯 Source ID。
- PyTorch GRU Encoder + 可學習動態 adjacency + 次時槽預測。可用 `--no-graph` 消融。
- Graph JSON／GraphML／無 CDN 離線 HTML 三種輸出。
- Ollama Qwen/Gemma 可選圖解釋工具，不更動圖，不提供假信心百分比。
- Synthetic smoke data + pytest 單元／端到端測試。

**注意：原始 Sherlock v3 的 ZIP 不在本包中；尚未在 Mac 真實資料上驗證。
本包僅供原型起步，不能直接宣稱完成正式論文實驗。**

## 第一步：新 Git 工作樹（不要在舊分支清空檔案）

1. 在 Mac 終端或 Cursor 中檢查 `git --version` 與舊 Repo `git status`。
2. 從舊 Repo 建新 orphan branch `mirage-ot` 與獨立 worktree：
   `git worktree add --orphan -b mirage-ot ../ICIT2027-mirage`。
   也可使用本包 `scripts/mac_new_project.sh`（會先檢查版本／路徑）。
3. 將本 ZIP **解壓到新 worktree**（包含 `src/`、`tests/`、`README.md` 等），
   不要解到舊 Repo；不要複製舊 EBRL 的程式或論文。
4. Sherlock v3 共用舊 Repo 的原始資料：
   `mkdir -p data/raw/sherlock && ln -s /Users/potinglu/Documents/ICIT2027/data/raw/sherlock/v3 data/raw/sherlock/v3`。
5. 連結不加入 Git、不將原始 ZIP 推到 GitHub。請先查 ZIP MD5：
   `01-Basic.zip=c482e0dc7e56b063b357d8b03be5cce6`
   `02-Semiurban.zip=0f7d3eb61e478d05f4b431ae99d45564`
   `03-Rural.zip=0cc7807bd5a76ea5bc85a1da6fd6c061`

## 第二步：執行測試及 smoke test

`python3 -m venv .venv && source .venv/bin/activate && pip install -e '.[test]' && pytest -q`

`mirage-ot synthetic-fixture --out runs/toy/fixture.jsonl`

`mirage-ot prepare --jsonl runs/toy/fixture.jsonl --out runs/toy/train.npz`

`mirage-ot fit --train runs/toy/train.npz --epochs 2 --max-steps 16 --out runs/toy/model.pt`

`mirage-ot graph --checkpoint runs/toy/model.pt --data runs/toy/train.npz --out runs/toy/graph`

請檢查 `graph.json`、`graph.graphml`、`graph.html`；這是**合成流程檢查**，不是研究實驗結果。

## 第三步：正式實驗前的阻塞事項

**P0：真實資料格式**。執行 `mirage-ot inspect-archive --archive data/raw/sherlock/v3/01-Basic.zip`。
列出真正的 state / pcap 內部路徑、紀錄時間、schema，和來源數量。使用真實
Sherlock 小窗口 smoke test；比較數筆原始記錄與 Feature Matrix。

**P0：PCAP／IEC104 解碼可靠性**。目前純 Python PCAP 解碼僅有限協定欄位，
不做 TCP 重組、CA/IOA/ASDU 解碼，且不同鏡像來源可能重複封包。請用經驗證的
IPAL transcriber 或經驗證完整解析器取代；維持來源 ID，記錄解碼失敗率。

**P0：ZIP 使用安全**。不得把 6GB+ ZIP 全部展開到 Mac SSD，維持串流讀取，
並避免無邊界把所有事件載入記憶體；按警報區間／訓練片段選定時間窗口。

**P0：時間序列特徵檢查**。IP​​AL 回報的電氣數值是 `network-reported`，
不是 `physical.zip` 模擬器真值；驗證測量與 setpoint 是否分開。全模態時間同步與
同源資訊的重複計分需明確寫入資料品質稽核報告。

**P1：正式自監督模型**。先訓練 no-graph vs learned-graph，
分開訓練、使用相同超參數及不同亂數種子，回報跨場景 Forecast MAE、
Graph Ablation、N/P/N+P Ablation，並檢查 learned edges 是否只是密集 softmax。
目前 prototype 的 query/key adjacency 不是解釋性邊機率；請研究可識別性、
稀疏圖假設、bootstrap 的不確定性與獨立驗證。

**P1：事件調查與 LLM**。先依真實已知事件區間挑選少量案例，產生
Network–Network／Physical–Physical／Cross-Modal 關聯圖。
把圖與證據供 Qwen/Gemma 解釋，但攻擊答案只能在 evaluator 使用。
模型輸出應說明統計相關不等於因果。加入 Evidence ID 存在性驗證。

**P2：論文評估**。Graph Prediction Utility、事件級下游調查
（官方標籤 evaluator-only）、圖穩定性、模型不確定性。
沒有獨立 relation Gold，不能報 Edge Precision／Edge Recall／正確關聯機率；
可以先不找專家，但論文應如實界定自動評估可以支持什麼研究主張。

## 結束交接的必要交付

請回報：Git branch/worktree 狀態、Sherlock 原始資料驗證、`pytest` 結果、
真實 Basic 事件最小可執行範例、Graph artifacts 路徑、目前 decode coverage、
train/eval 隔離、正式 Baseline 設定及每項限制。

## 不可做

不要改舊 Git 分支、不要複製舊 EBRL 任何源碼、不准加入人工攻擊類別規則、
不可隨意 `git clean`/`git reset --hard`、不得覆寫既有研究檔、不得捏造 metrics。
