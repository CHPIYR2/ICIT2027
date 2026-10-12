# EBRL 實作狀態

更新日期：2026-10-13（Asia/Taipei）  
分支：`ebrl-implementation`（自 `main` `0c02db4` 分出）  
本文件是恢復工作的入口。數值只引用已執行的測試與 `results/ebrl-synthetic-v1/summary.json`。

## 環境

- 工作樹在開始時乾淨，只有未追蹤的交接文件。
- Python 3.12.10 安裝於使用者目錄。既有測試依賴的 scikit-learn 未預先安裝；EBRL 路徑不使用它。
- `data/raw/` 不存在。Sherlock v3 三份封存未掛載，未重新下載。
- `http://127.0.0.1:11434` 無 Ollama 回應。未呼叫雲端模型。
- 本機沒有 `pdflatex` / `tectonic`。論文原始碼已改，PDF 未重編。

## 階段

| 階段 | 狀態 | 證據 |
|---|---|---|
| 0 盤點 | DONE | Git `0c02db4`；既有 `src/investigation*` 是 claim-support 管線，不是 EBRL |
| 1 來源稽核 | DONE | `docs/ebrl_provenance_audit.md`；R3/R4 事實指標 NA |
| 2 契約 | DONE | `configs/ebrl/contract.v1.json` 與 ontology、verifier rules |
| 3 核心管線 | DONE | `src/ebrl/`；`scripts/run_ebrl.py` |
| 4 評分與 B0–B3、P0/P1 | DONE | 合成挑戰已跑；Sherlock 事件未跑 |
| 5 本地 LLM | BLOCKED | B5/B6/hybrid 未執行。介面在 `src/ebrl/llm.py`，拒絕雲端 URL |
| 6 Sherlock 評估 | BLOCKED | 無原始封存，也無獨立 command–effect join |
| 6 合成挑戰 | DONE | `results/ebrl-synthetic-v1/`。不是 Sherlock 成績 |
| 7 論文 | DONE（原始碼） | `icit2027_ot_investigation.tex` 已按稽核改寫；PDF BLOCKED |
| 8 EBRL 測試 | DONE | `tests/test_ebrl.py`，33 項通過 |

## 方法狀態

| 方法 | 狀態 | 說明 |
|---|---|---|
| B0–B3 | DONE | 同一凍結候選。合成套件上已評分 |
| B4 | NOT_APPLICABLE | 沒有獨立標註的開發配對。用政策規則訓練會循環 |
| B5、B6 | BLOCKED_NOT_RUN | 無本地模型。沒有雲端替代 |
| P0、P1 | DONE | 規則 proposer。乾淨提案上 P0 與 P1 處置相同 |
| A_NO_CEILING、A_ACK、A_UNTYPED、A_BINARY | DONE | 合成消融，不是 Sherlock 表 |

## 已完成的科學結論

- 自然 Sherlock 配對的 operational precision / recall / UOLR / EFRI 為 **NA**。
- P0 與政策參考的處置一致率是 **1.0**，這是規則重播，不是事實精度。
- 合成套件上，verifier 能把 acknowledgement 升格打回可見上限，但不能把「看起來相關、獨立標籤卻是否定」的配對改成正確的非關聯。
- 論文主表不填入合成數字。

## 下一步（需要原始資料或本地模型之後）

1. 掛載既有 Sherlock v3 封存，不要改 immutable manifest。
2. 只讀稽核 `events.jsonl`、control-center notifications、physical snapshots，確認有沒有 command id → response → effect 的連接鍵。
3. 若仍沒有連接鍵，維持 R3/R4 事實指標 NA，只在可見證據上做政策一致性，並標成 silver。
4. 凍結  development / evaluation manifest 後才調閾值。目前閾值是預先指定，沒有在開發集上調過。
5. 啟動本機 Ollama 後，用同一個模型跑 B5、B6 與 hybrid proposer。失敗列為失敗，不得改記成棄答。

## 重現

```text
%LOCALAPPDATA%\Programs\Python\Python312\python.exe -m unittest discover -s tests -p test_ebrl_*.py -v
%LOCALAPPDATA%\Programs\Python\Python312\python.exe scripts\evaluate_ebrl.py
%LOCALAPPDATA%\Programs\Python\Python312\python.exe scripts\audit_ebrl_provenance.py
%LOCALAPPDATA%\Programs\Python\Python312\python.exe scripts\reproduce_ebrl.py
```

`reproduce_ebrl.py` 會依序跑測試、合成評估與來源稽核。它不連外網，也不呼叫 LLM。
