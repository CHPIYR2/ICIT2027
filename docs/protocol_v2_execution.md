# Protocol v2 執行紀錄

使用者已明確核准上一輪六項提案：「同意，開始吧」。核准原文、時間與提案雜湊
保存於 results/exploratory-v2/approval/authorization.json；三份未核准 draft 的原始
副本存同目錄 *.proposed。原 review_manifest.json 與審阅文件保留為歷史，不改写。

network_observability.v2.json、features.v2.json、evaluation.v2.json 已依這次核准轉成
frozen_exploratory，執行前產生 configs/protocol.v2.lock.json。這不是修改原 v1 的 locks。

執行順序：48 項測試 → v2 freeze → 119-event projection build → Basic-only CV/final fit →
84-event exploratory score → 報告與圖表。沒有新 E、沒有模型／閾值搜尋，也沒有按新結果
移動 outage 起點。原 v1 FULL/E 模型的 9 個 reference 條件以 saved predictions 重現核對。

觀測性介面區分全域 source removal 與 N-export restriction。傳輸 projection 本身只含
核准 packet header fields，不持有 canonical episode 或 resolver；public E 介面不輸出
hidden parent headers。單元測試涵蓋 IEC/COT/process mutation、隱藏尾段 mutation、
半開區間截止、不可恢復隱藏來源、E 不變、真正 source removal 的 E 連帶移除、空可見窗、
feature allowlist 與所有 levels 的巢狀遮蔽。LLM 未實作。

模型使用原 .venv 與 requirements.lock，繪圖另用 .venv-figures；其套件快照為
results/exploratory-v2/figures-requirements.lock，不變更原模型環境。

完成結果見 docs/network_observability_results_v2.md；逐家族結果見
 docs/observability_family_results_v2.md。所有新分析為探索性／post-confirmatory，
既有 84 個事件並非新的未見測試。後續不得將此結果回寫原主比較。

最終唯讀查核已通過，結果保存於 results/exploratory-v2/verification.json。
查核涵蓋原始與 v2 凍結雜湊、119 份 canonical/visibility 產物、E/FULL 特徵不變、
各層遮罩巢狀與可見／隱藏集合完整性、24 個模型雜湊、120 次 Basic-only fold fit、
全部 33 條件的預測覆蓋率、所有分組指標重算、原 reference 逐筆比對、四組 bootstrap
重算及全部 1,785 筆 development/evaluation transition records。查核沒有重新訓練模型。
可用 `.venv/bin/python scripts/verify_observability_results_v2.py` 重做唯讀驗證；
只會更新 verification.json，不會覆寫模型、分數或 frozen lock。
