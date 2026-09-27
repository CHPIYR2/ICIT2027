# Investigation event selection — 待核准候選集

只做 evaluator-side selection；**PROPOSED_NOT_FROZEN**。未執行 LLM、未產生人工 gold、未根據模型表現挑選。
完整 candidate IDs、observable descriptors、理由與輸入雜湊見 investigation_event_candidates.proposed.json。
生成規則保存在 docs/propose_investigation_events.py；這是文件審閱用分析工具，不是 runtime retriever。

## 現有母體與可見性

母體 119 件：Basic 35、Semiurban 48、Rural 36；五份 recording（Basic train/test、Semiurban train/test、Rural test）。
四個 cyber 家族是 Industroyer、Drift-off、Control-and-freeze、ARP-spoof DoS。
benign 保留原 catalog exact names；Separator Movement 與 Seperator Movement 不默默合併，
Basic 的 maintenance1/2/3、sgencontrol、trafostep/trafostep2 也保留，不推測它們等於其他操作。

所有事件四個 numeric E family 都有至少部分有效 pre/post pair，但 14 件有 numeric post channel 缺測
（Basic 2、Semiurban 6、Rural 6）；119 件都沒有 state pre/post pair。
有 post state channel 的事件為 20/35、24/48、14/36；此數字不是 state change 次數。

## 提案配額與規則

- 開發：Basic 每個 exact family 選 1 件，共 16（4 cyber、12 benign）。
- 評估：Semiurban、Rural 的每個 cyber family 各 2 件，共 16 cyber。
- 評估 benign：每個場景的每個 exact benign family 至少 1 件，再加 Semiurban 2、Rural 1 個 diversity slots，合計 16 benign。
- 最終提案共 48 件：16 development + 32 evaluation，不一次標註 119 件。
- 每場景各 descriptor 先轉 midrank；按 family 字串排序建立配額，第一筆以固定 salt+opaque ID 的 SHA256 排序；
  後續逐筆選距已選集最遠者（最小平方距離最大化），tie 用同一 hash。不是從成績挑容易事件。
- descriptor 僅原始既有 summary：四種 E relative change、N rate、command/response counts、gap、RST、
  numeric missing fraction、post state channels。這些只用來建立 evaluator 候選集，不進 LLM prompt。
- N count/rate/missingness 多樣性無法保證 investigation 難度多樣性；需人工 pilot 記錄 difficulty，不能之後依 LLM 成績換掉難事件。

| Partition | Scenario | n | CYBER/BENIGN | Recording 分布 | 有 numeric 缺測 | 無 post state |
|---|---|---:|---|---|---:|---:|
| development | 01-Basic | 16 | 4/12 | {'test': 11, 'train': 5} | 1 | 7 |
| evaluation | 02-Semiurban | 18 | 8/10 | {'test': 13, 'train': 5} | 2 | 8 |
| evaluation | 03-Rural | 14 | 8/6 | {'test': 14} | 2 | 7 |

候選含 5 件 numeric 缺測與 22 件無 post state 的事件；缺少 evidence 不是排除理由。
開發與評估按 scenario 分開，沒有同一 recording 跨兩組；但五份 recording 和原 84 件早已被稽核，
不能稱新的 unseen dataset 或獨立 confirmatory evidence。16/16 cyber/benign 是審查配額，不代表真實流行率。

## 候選 ID（不是 frozen ID list）

| Partition | Scenario/recording | Episode ID | Evaluator family |
|---|---|---|---|
| development | 01-Basic/test | `ev_812f8057d7c974d9cf36` | arp-spoof:arp-spoof-dos |
| development | 01-Basic/test | `ev_363ad64e92cfa74fd5f6` | control center:Cable Maintenance |
| development | 01-Basic/train | `ev_d0f69721cdddb2ca7528` | control center:Generator Bootstrap |
| development | 01-Basic/train | `ev_ab03f537915a04bff66c` | control center:Generator Control |
| development | 01-Basic/train | `ev_d0bba4b2d86620ece6e2` | control center:Manual Commands |
| development | 01-Basic/train | `ev_8e123e1c9101b39b2c8f` | control center:Separator Movement |
| development | 01-Basic/train | `ev_625f98cd139b5bea0587` | control center:Transformer Maintenance |
| development | 01-Basic/test | `ev_3e4d36008b29595ef246` | control center:maintenance1 |
| development | 01-Basic/test | `ev_410757c59c7e2db8363d` | control center:maintenance2 |
| development | 01-Basic/test | `ev_0961f1c2da8a257e3ebc` | control center:maintenance3 |
| development | 01-Basic/test | `ev_e76705884b8fec84592a` | control center:sgencontrol |
| development | 01-Basic/test | `ev_c7ce825223f3857cb235` | control center:trafostep |
| development | 01-Basic/test | `ev_47f867601cdff155820e` | control center:trafostep2 |
| development | 01-Basic/test | `ev_d04a24cd3fe039e0f7c1` | control-and-freeze:control-and-freeze |
| development | 01-Basic/test | `ev_21f18503563e6a677ae5` | drift-off:drift-off |
| development | 01-Basic/test | `ev_9c2ee5271d86628b1149` | industroyer:industroyer |
| evaluation | 02-Semiurban/test | `ev_eda32c84a9cf2952b292` | arp-spoof:arp-spoof-dos |
| evaluation | 02-Semiurban/test | `ev_54ead6013ea77949d028` | arp-spoof:arp-spoof-dos |
| evaluation | 02-Semiurban/test | `ev_d2eff99482b1195f73f5` | control center:Cable Maintenance |
| evaluation | 02-Semiurban/train | `ev_9804ee8ea26d2b778499` | control center:Close Ring |
| evaluation | 02-Semiurban/train | `ev_7a7f38593e6d9db5c366` | control center:Generator Bootstrap |
| evaluation | 02-Semiurban/train | `ev_82cae08a30e24662dec9` | control center:Generator Control |
| evaluation | 02-Semiurban/test | `ev_f2346d953482ad8cc899` | control center:Open Ring |
| evaluation | 02-Semiurban/test | `ev_48d9fc078aff4e136a46` | control center:Separator Movement |
| evaluation | 02-Semiurban/train | `ev_caf3dd59bae66580f185` | control center:Seperator Movement |
| evaluation | 02-Semiurban/train | `ev_7bb8cd58a5ec6e685f4d` | control center:Transformer Maintenance |
| evaluation | 02-Semiurban/test | `ev_0c08ce74d40931b74df0` | control-and-freeze:control-and-freeze |
| evaluation | 02-Semiurban/test | `ev_f7bce2b07965f3d54423` | control-and-freeze:control-and-freeze |
| evaluation | 02-Semiurban/test | `ev_6182d95c34d95866f8b1` | drift-off:drift-off |
| evaluation | 02-Semiurban/test | `ev_5fbea088e70b34749755` | drift-off:drift-off |
| evaluation | 02-Semiurban/test | `ev_a50c6019708978b4f2a5` | industroyer:industroyer |
| evaluation | 02-Semiurban/test | `ev_fa8e045e341a6397db03` | industroyer:industroyer |
| evaluation | 02-Semiurban/test | `ev_0431e34c3ed30056a8f0` | control center:Generator Control |
| evaluation | 02-Semiurban/test | `ev_50b143b3c49e56cb4c57` | control center:Generator Control |
| evaluation | 03-Rural/test | `ev_54f129e565141b49466d` | arp-spoof:arp-spoof-dos |
| evaluation | 03-Rural/test | `ev_a9fae32d1b8c5ad5da48` | arp-spoof:arp-spoof-dos |
| evaluation | 03-Rural/test | `ev_6545a8576a07a2c06b5c` | control center:Cable Maintenance |
| evaluation | 03-Rural/test | `ev_a0511b88a60de51f8897` | control center:Close Ring |
| evaluation | 03-Rural/test | `ev_0ed0845aa71a77f06ba3` | control center:Generator Control |
| evaluation | 03-Rural/test | `ev_56f6a02bdb6cd6262ef2` | control center:Open Ring |
| evaluation | 03-Rural/test | `ev_7cafdb049b6397dab355` | control center:Separator Movement |
| evaluation | 03-Rural/test | `ev_06ea9a17a9417b83c52b` | control-and-freeze:control-and-freeze |
| evaluation | 03-Rural/test | `ev_906c24cffc08c5783c45` | control-and-freeze:control-and-freeze |
| evaluation | 03-Rural/test | `ev_3855d8c61d1bd55fa074` | drift-off:drift-off |
| evaluation | 03-Rural/test | `ev_affcf9589116c90a0824` | drift-off:drift-off |
| evaluation | 03-Rural/test | `ev_02f636fa1aedfa7539fe` | industroyer:industroyer |
| evaluation | 03-Rural/test | `ev_7e55a0045a505982b278` | industroyer:industroyer |
| evaluation | 03-Rural/test | `ev_87eb044f38bd34bc8e99` | control center:Generator Control |

## 核准與更動

作者核准後先凍結 selected IDs，再進 final prompt/verifier 調整；任何更動必須記錄版本、原因與是否已看模型輸出。
不可在 evaluation 後替換難事件、只保留有 E+N 優勢者；不能拿 family label 作 retrieval key。
候選集中少數 exact family 只有 1 件；不能做可靠的 per-family 泛化推論。其他事件保留為未納入本輪 annotation，
不宣稱它們完全未被研究團隊看過。若需擴大 sample，應另定 protocol 並揭露既有資料使用。
