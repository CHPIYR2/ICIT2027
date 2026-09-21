"""Render descriptive pre-approval audit; no estimator operations."""
from pathlib import Path
import json
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[1]
load=lambda name:json.loads((ROOT/'results/exploratory-v2/audit'/name).read_text())
D=load('feature_distributions.json');C=load('coverage_summary.json');T=load('existing_prediction_transitions.json')['rows']
fmt=lambda x:'缺失' if x is None else f'{x:.5g}'
def stat(v):
    if not v['valid']:return '全缺失'
    return f"{fmt(v['min'])}–{fmt(v['max'])}; {fmt(v['median'])}; {fmt(v['iqr'])}"

def write(name,lines):
    p=ROOT/'docs'/name
    with p.open('x') as f:f.write('\n'.join(lines)+'\n')

lines=['# Electrical feature audit — Protocol v2 探索性稽核','',
'本文件是已觀察 Sherlock 119 個事件的描述性 audit，含 Basic 35 與先前評估 84；不是新模型結果。',
'所有數字來自既有 pipeline-v2 episodes/features，不使用 physical.zip、initial_value 或未來資料。',
'逐事件來源、quality-valid channel coverage 見 results/exploratory-v2/audit/episode_coverage.json。','',
'## 1. 哪些欄位實際有值','',
'每個場景的四個 numeric relative change、五個 post missing fraction 均為全事件非缺失。',
'但 state changed fraction 在 Basic 35/35、Semiurban 48/48、Rural 36/36 都缺失。',
'沒有可配對的 state pre/post channel，不能視為 zero transitions；missing fraction 有值也不代表 process value 已觀測。','',
'## 2. 可用的前後 channel coverage','',
'表格為每事件同時有有效 pre/post 的 channel 數：min / median / max（靜態 mapped 數）。',
'事件是統計單位，沒有把多個 channels 擴增為事件。','',
'| 場景 | Family | paired channel min/median/max | mapped channels |','|---|---|---|---:|']
for scene,row in C.items():
    for fam,v in row['families'].items():
        b=v['both_channels'];lines.append(f"| {scene} | {fam} | {fmt(b['min'])}/{fmt(b['median'])}/{fmt(b['max'])} | {fmt(v['mapped_channels']['median'])} |")
lines+=['','四個 numeric family 的每事件 pre/post 覆蓋普遍完整或接近完整；reported_state 的 paired coverage 一律零。',
'此結果支持保留現有 numeric E 作控制條件，不支持憑空恢復初始 state。','',
'## 3. CYBER/BENIGN 的既有 E 分布','',
'以下為 min–max；median；IQR。這些是所有場景合併的描述，會混入場景與事件家族構成差異，',
'不能據此挑閾值或宣稱特徵有因果效果。按場景×類別的全部統計見 feature_distributions.json。','',
'| E 欄位 | CYBER (75) | BENIGN (44) |','|---|---|---|']
for name in D['truth']['CYBER']['features']:
    if name.startswith('e_'):lines.append(f"| {name} | {stat(D['truth']['CYBER']['features'][name])} | {stat(D['truth']['BENIGN']['features'][name])} |")
lines+=['','四個 numeric change 都在兩類內變動；BENIGN 的典型變化也可能很大，不能把大幅電氣變動直接等同攻擊。',
'連續量的 missing fractions 在 44 個 BENIGN 均為零，部分 CYBER 大於零；missingness 的確可能帶有通訊／程序線索。',
'但目前沒有比較 values-only/missingness-only 模型，**不能回答缺失是否比數值更有預測力**。',
'如需這項比較，須另核准固定分組消融，不從本表挑最佳欄位。','',
'## 4. 電氣變化是否依事件家族不同','',
'原始 family_description 保留，不合併拼字相近名稱。下表只示既有變化特徵的 family median；',
'全部欄位、range/IQR 與 counts 已保存於 JSON，少數家族只有一件，不作顯著性推論。','',
'| 原始家族 | n | voltage relative change median | active-power relative change median |','|---|---:|---:|---:|']
for family,row in sorted(D['family'].items()):
    lines.append(f"| {family} | {row['events']} | {fmt(row['features']['e_voltage_relative_change'].get('median'))} | {fmt(row['features']['e_active_power_relative_change'].get('median'))} |")
lines+=['','家族摘要差異明顯，但同時混有場景規模、資產類型、動作方式與數值 baseline。',
'目前 max aggregation 會隨 channel 數及極端值改變，尤其 near-zero baseline 由固定 floor 穩定後仍可產生很大比值。','',
'## 5. 足夠性與候選改進（未實作）','',
'建議第一輪 observability matrix 保持原 10 欄 E，讓網路條件成为唯一主要變動因素。',
'這套 E 足夠作保守參考，但不能表示全部製程行為或獨立物理真值。','',
'後續獨立提案可考慮：','',
'- 最大 post deviation：每 channel 的 max(abs(post−mean(pre)))/max(abs(mean(pre)),既有 family floor)，再以固定 family 90th percentile 聚合；需 pre>=1、post>=1。',
'- 變異變化：每 channel 的 log1p(var(post)/floor²)−log1p(var(pre)/floor²)，population variance，需兩邊各>=2；family 取中位數。',
'- freshness：每 channel 到可見截止時間的最後有效觀測 age，無觀測為 None；不得補窗外舊值。',
'- 狀態轉移數：只有同一 channel 至少兩筆有效已觀測 state 才能計算，不能用 initial state 補起點；先核對實際可用性。',
'- 超過偏差門檻的 channel fraction 如需使用，門檻只能由 Basic training fold 定義，不能依已見 84 labels 設計。','',
'上述候選沒有計算新 feature matrix、沒有 fit/predict，也沒有選出「最能讓融合勝出」的一组。',
'是否新增 E 是獨立作者 gate；本提案建議暫不新增。']
write('electrical_feature_audit_v2.md',lines)

N=[k for k in D['scenario']['01-Basic']['features'] if k.startswith('n_')]
lines=['# Network shortcut analysis — Protocol v2 探索性稽核','',
'僅重分析已凍結的 features/predictions，不重訓、不選新閾值、不產生新 observability 成績。',
'完整分布：results/exploratory-v2/audit/feature_distributions.json；規則分組：existing_command_rule.json。','',
'## 直接與間接資訊路徑','',
'- command/activation response：直接 ASDU/COT 語意。既有 >0 規則使用合法觀測欄位，未讀取 event truth 作輸入。',
'- APDU rates/gaps：不直接解碼命令類別，但仍需要 IEC framing，命令程序可改變 count/timing。',
'- U-format：IEC 控制格式，非 TCP 資訊，可能與啟停／測試程序相關；不能僅以「沒有 ASDU」稱 transport-only。',
'- RST：普通 TCP 行為，仍可能對應特定腳本。',
'- endpoint count：合法 transport 數量，但每場景固定且不同，呈現 topology/recording 結構。',
'- packet size、fine timing 是潛在消息型態／腳本 proxy；最小提案先不加入 packet-size 統計。','',
'這些關聯稱 dataset-specific/procedural shortcut；未發現使用 forbidden G 的證據，不能單憑強預測性称 data leakage。','',
'## 既有 N 按類別分布','',
'每格為 min–max；median；IQR。全場景合併，類別組成與場景偏移需另看分層摘要。','',
'| N 欄位 | CYBER 75 | BENIGN 44 |','|---|---|---|']
for n in N:lines.append(f"| {n} | {stat(D['truth']['CYBER']['features'][n])} | {stat(D['truth']['BENIGN']['features'][n])} |")
lines+=['','## 原命令存在規則：按 recording／scenario／family 重列','',
'原先已定義規則：command log count>0 判 BENIGN，否則 CYBER；本輪沒有搜尋門檻。',
'119 個事件（CYBER 75、BENIGN 44）全部符合，包含原 84 評估事件。這不是新增獨立驗證。',
'activation-response 欄在此資料亦呈現相同有／無分隔，但不新增調參規則。','',
'| Recording | n | command log-count range | response range | post log-rate median | endpoint log-count median |','|---|---:|---|---|---:|---:|']
for group,row in sorted(D['recording'].items()):
    f=row['features'];rg=lambda k:f"{fmt(f[k]['min'])}–{fmt(f[k]['max'])}"
    lines.append(f"| {group} | {row['events']} | {rg('n_command_log_count')} | {rg('n_activation_response_log_count')} | {fmt(f['n_post_log_rate']['median'])} | {fmt(f['n_endpoint_log_count']['median'])} |")
rule=load('existing_command_rule.json')['groups']
lines+=['','| 原始家族 | n | 命令存在事件 | 原規則正確 |','|---|---:|---:|---:|']
for family,row in sorted(rule['family'].items()):lines.append(f"| {family} | {row['events']} | {row.get('command_present',0)} | {row['correct']}/{row['events']} |")
lines+=['','全部八個 N 欄位按 scenario、recording、family 與 scenario×truth 的完整 range/median/IQR 均在 JSON；',
'場景分布也另表於 network_distribution_shift_v2.md。未檢查程序碼因果機制，不把統計分隔當因果證明。','',
'## 原預測的 event transition 稽核','',
'主比較：每個模型均 84/84 unchanged。既有兩欄消融只有 RF 改變 20 件：15 corrected_N、5 hurt_N。',
'其餘模型亦全部 unchanged。以下按原始家族列既有 RF 消融，並非新 Protocol-v2 regime。','',
'| 家族 | n | N 正確 | EN 正確 | corrected_N | hurt_N | unchanged |','|---|---:|---:|---:|---:|---:|---:|']
g=defaultdict(list)
for r in T:
    if r['condition']=='without_commands' and r['model']=='random_forest':g[r['family']].append(r)
for f,rs in sorted(g.items()):
    c=Counter(r['transition'] for r in rs)
    lines.append(f"| {f} | {len(rs)} | {sum(r['N_correct'] for r in rs)} | {sum(r['EN_correct'] for r in rs)} | {c['corrected_N']} | {c['hurt_N']} | {c['unchanged']} |")
lines+=['','每一個改變與未改變事件均有診斷列，包括 ID、scenario、family、N/EN scores/predictions、正確性與 evidence hash，',
'見 existing_prediction_transitions.json。這是模型對照造成的判斷差異，不是操弄 E 的物理因果效果。']
write('network_shortcut_analysis_v2.md',lines)

lines=['# Network distribution shift — Protocol v2 探索性描述','',
'只讀舊 features 與 LR contributions；未重新 fit scaler、threshold 或模型。',
'每格依序為 range；median；IQR。原 capture scope、feature definition 保持不變。','',
'| N 欄位 | Basic n=35 | Semiurban n=48 | Rural n=36 |','|---|---|---|---|']
for n in N:lines.append('| '+n+' | '+' | '.join(stat(D['scenario'][s]['features'][n]) for s in ['01-Basic','02-Semiurban','03-Rural'])+' |')
lines+=['','## 場景內類別條件摘要','', '| 場景與類別 | 欄位 | n | range；median；IQR |','|---|---|---:|---|']
for key,row in sorted(D['scenario_truth'].items()):
    for n in N:lines.append(f"| {key.replace('|',' / ')} | {n} | {row['events']} | {stat(row['features'][n])} |")
lines+=['','## 保留原 LR 失敗的解讀','',
'Basic 的 post log-rate 1.972–2.182，已見其他場景 2.908–4.302，範圍不重疊。',
'原 LR N/EN 把全部 84 事件判 BENIGN；其 N 的 post-rate 平均 log-odds 貢獻 −17.347。',
'這支持資料規模偏移壓過其他訊號的描述性解釋，不是 proof of physical causality。',
'endpoint count 在 Basic、Semiurban、Rural 內各固定，不能因 topology 可見就認為它具有跨場景分類能力。',
'不以這些已見分布重設原 scaler。若將來研究 per-endpoint rates/normalization，屬另行核准的 Protocol-v2 探索性變更，',
'且 transformation 的任何 learned 統計只能來自 Basic training fold，不能用全部場景 fit。']
write('network_distribution_shift_v2.md',lines)
