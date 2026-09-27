# Network distribution shift — Protocol v2 探索性描述

只讀舊 features 與 LR contributions；未重新 fit scaler、threshold 或模型。
每格依序為 range；median；IQR。原 capture scope、feature definition 保持不變。

| N 欄位 | Basic n=35 | Semiurban n=48 | Rural n=36 |
|---|---|---|---|
| n_post_log_rate | 1.9718–2.1823; 2.0281; 0.030738 | 3.3911–4.3025; 4.0305; 0.21199 | 2.9078–3.8297; 3.6071; 0.19777 |
| n_log_rate_change | -0.044255–0.034046; 0.0065574; 0.016416 | -0.046891–0.017763; -0.0019335; 0.013135 | -0.072287–0.016514; -0.0027298; 0.013555 |
| n_command_log_count | 0–1.6094; 0; 0.69315 | 0–1.3863; 0; 0.69315 | 0–1.3863; 0; 0 |
| n_activation_response_log_count | 0–1.6094; 0; 0.69315 | 0–1.3863; 0; 0.69315 | 0–1.3863; 0; 0 |
| n_rst_log_count | 0–1.3863; 0; 0 | 0–0; 0; 0 | 0–0; 0; 0 |
| n_post_max_gap_fraction | 0.0099026–0.050321; 0.017378; 0.0039123 | 0.0018811–0.0060113; 0.0031483; 0.0011812 | 0.0025024–0.024811; 0.0056679; 0.0050544 |
| n_u_log_count | 0–1.6094; 0; 0 | 0–1.7918; 0; 0 | 0–1.3863; 0; 0 |
| n_endpoint_log_count | 3.5264–3.5264; 3.5264; 0 | 4.3041–4.3041; 4.3041; 0 | 4.1271–4.1271; 4.1271; 0 |

## 場景內類別條件摘要

| 場景與類別 | 欄位 | n | range；median；IQR |
|---|---|---:|---|
| 01-Basic / BENIGN | n_post_log_rate | 17 | 2.0082–2.1823; 2.0347; 0.086461 |
| 01-Basic / BENIGN | n_log_rate_change | 17 | 0.0059347–0.034046; 0.017392; 0.015539 |
| 01-Basic / BENIGN | n_command_log_count | 17 | 0.69315–1.6094; 0.69315; 0.69315 |
| 01-Basic / BENIGN | n_activation_response_log_count | 17 | 0.69315–1.6094; 0.69315; 0.69315 |
| 01-Basic / BENIGN | n_rst_log_count | 17 | 0–0; 0; 0 |
| 01-Basic / BENIGN | n_post_max_gap_fraction | 17 | 0.0099026–0.050321; 0.018067; 0.0042881 |
| 01-Basic / BENIGN | n_u_log_count | 17 | 0–0; 0; 0 |
| 01-Basic / BENIGN | n_endpoint_log_count | 17 | 3.5264–3.5264; 3.5264; 0 |
| 01-Basic / CYBER | n_post_log_rate | 18 | 1.9718–2.0477; 2.026; 0.02494 |
| 01-Basic / CYBER | n_log_rate_change | 18 | -0.044255–0.01105; -0.0010977; 0.0081334 |
| 01-Basic / CYBER | n_command_log_count | 18 | 0–0; 0; 0 |
| 01-Basic / CYBER | n_activation_response_log_count | 18 | 0–0; 0; 0 |
| 01-Basic / CYBER | n_rst_log_count | 18 | 0–1.3863; 0; 0 |
| 01-Basic / CYBER | n_post_max_gap_fraction | 18 | 0.012973–0.028912; 0.017118; 0.0033625 |
| 01-Basic / CYBER | n_u_log_count | 18 | 0–1.6094; 0; 0 |
| 01-Basic / CYBER | n_endpoint_log_count | 18 | 3.5264–3.5264; 3.5264; 0 |
| 02-Semiurban / BENIGN | n_post_log_rate | 19 | 3.6239–4.3025; 4.0407; 0.27059 |
| 02-Semiurban / BENIGN | n_log_rate_change | 19 | -0.0078474–0.0090928; 0.00176; 0.0031826 |
| 02-Semiurban / BENIGN | n_command_log_count | 19 | 0.69315–1.3863; 0.69315; 0.40547 |
| 02-Semiurban / BENIGN | n_activation_response_log_count | 19 | 0.69315–1.3863; 0.69315; 0.40547 |
| 02-Semiurban / BENIGN | n_rst_log_count | 19 | 0–0; 0; 0 |
| 02-Semiurban / BENIGN | n_post_max_gap_fraction | 19 | 0.0018811–0.0057691; 0.0031516; 0.0010752 |
| 02-Semiurban / BENIGN | n_u_log_count | 19 | 0–0; 0; 0 |
| 02-Semiurban / BENIGN | n_endpoint_log_count | 19 | 4.3041–4.3041; 4.3041; 0 |
| 02-Semiurban / CYBER | n_post_log_rate | 29 | 3.3911–4.202; 4.0167; 0.1777 |
| 02-Semiurban / CYBER | n_log_rate_change | 29 | -0.046891–0.017763; -0.0094404; 0.025167 |
| 02-Semiurban / CYBER | n_command_log_count | 29 | 0–0; 0; 0 |
| 02-Semiurban / CYBER | n_activation_response_log_count | 29 | 0–0; 0; 0 |
| 02-Semiurban / CYBER | n_rst_log_count | 29 | 0–0; 0; 0 |
| 02-Semiurban / CYBER | n_post_max_gap_fraction | 29 | 0.0019975–0.0060113; 0.003145; 0.0012752 |
| 02-Semiurban / CYBER | n_u_log_count | 29 | 0–1.7918; 0; 0 |
| 02-Semiurban / CYBER | n_endpoint_log_count | 29 | 4.3041–4.3041; 4.3041; 0 |
| 03-Rural / BENIGN | n_post_log_rate | 8 | 2.9078–3.8232; 3.6659; 0.25467 |
| 03-Rural / BENIGN | n_log_rate_change | 8 | -0.0027574–0.016514; 0.0058717; 0.0080019 |
| 03-Rural / BENIGN | n_command_log_count | 8 | 0.69315–1.3863; 0.69315; 0.47739 |
| 03-Rural / BENIGN | n_activation_response_log_count | 8 | 0.69315–1.3863; 0.69315; 0.47739 |
| 03-Rural / BENIGN | n_rst_log_count | 8 | 0–0; 0; 0 |
| 03-Rural / BENIGN | n_post_max_gap_fraction | 8 | 0.0033223–0.024811; 0.0052686; 0.007281 |
| 03-Rural / BENIGN | n_u_log_count | 8 | 0–0; 0; 0 |
| 03-Rural / BENIGN | n_endpoint_log_count | 8 | 4.1271–4.1271; 4.1271; 0 |
| 03-Rural / CYBER | n_post_log_rate | 28 | 3.0956–3.8297; 3.6041; 0.18642 |
| 03-Rural / CYBER | n_log_rate_change | 28 | -0.072287–0.0048478; -0.0085775; 0.014542 |
| 03-Rural / CYBER | n_command_log_count | 28 | 0–0; 0; 0 |
| 03-Rural / CYBER | n_activation_response_log_count | 28 | 0–0; 0; 0 |
| 03-Rural / CYBER | n_rst_log_count | 28 | 0–0; 0; 0 |
| 03-Rural / CYBER | n_post_max_gap_fraction | 28 | 0.0025024–0.024273; 0.0056679; 0.0046596 |
| 03-Rural / CYBER | n_u_log_count | 28 | 0–1.3863; 0; 0 |
| 03-Rural / CYBER | n_endpoint_log_count | 28 | 4.1271–4.1271; 4.1271; 0 |

## 保留原 LR 失敗的解讀

Basic 的 post log-rate 1.972–2.182，已見其他場景 2.908–4.302，範圍不重疊。
原 LR N/EN 把全部 84 事件判 BENIGN；其 N 的 post-rate 平均 log-odds 貢獻 −17.347。
這支持資料規模偏移壓過其他訊號的描述性解釋，不是 proof of physical causality。
endpoint count 在 Basic、Semiurban、Rural 內各固定，不能因 topology 可見就認為它具有跨場景分類能力。
不以這些已見分布重設原 scaler。若將來研究 per-endpoint rates/normalization，屬另行核准的 Protocol-v2 探索性變更，
且 transformation 的任何 learned 統計只能來自 Basic training fold，不能用全部場景 fit。
