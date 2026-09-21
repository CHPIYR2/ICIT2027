"""Read-only result rendering: curves and family transitions; never fits a model."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/exploratory-v2'
load=lambda p:json.loads((OUT/p).read_text())
REGIMES={60:'N_TRANSPORT_T60',45:'N_DEGRADED_TRANSPORT_T45',30:'N_DEGRADED_TRANSPORT_T30',15:'N_DEGRADED_TRANSPORT_T15'}
MODELS={'logistic_regression':'Logistic Regression','random_forest':'Random Forest','gradient_boosting':'Gradient Boosting'}
fmt=lambda v:'NA' if v is None else f'{v:.3f}'
count=lambda d:f"{d['numerator']}/{d['denominator']}"


def main():
    data=load('evaluation/metrics.json')['metrics'];boots=load('evaluation/paired_bootstrap.json')['results']
    transitions=load('transitions/evaluation.json')['rows']
    features=load('features/held_out.json')['rows']
    figdir=OUT/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,3,figsize=(13.5,4.6),sharey=True)
    for ax,(model,title) in zip(axes,MODELS.items()):
        for view,color,marker,label in [('N','#2166ac','o','N only'),('EN','#b35806','s','E + N')]:
            ax.plot(list(REGIMES),[data[r][model][view]['overall']['macro_f1'] for r in REGIMES.values()],
                    color=color,marker=marker,linewidth=2,label=label)
        ax.axhline(data['E_REFERENCE'][model]['E']['overall']['macro_f1'],color='#777777',linestyle=':',label='E only reference')
        ax.set_title(title);ax.set_xlim(63,12);ax.set_xticks([60,45,30,15]);ax.set_ylim(0,1.03)
        ax.set_xlabel('Visible post-event network duration (s)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Macro F1');axes[0].legend(loc='upper left',fontsize=9)
    fig.suptitle('Exploratory Protocol v2 — transport visibility and incremental electrical evidence',y=.99)
    fig.text(.5,.015,'Previously evaluated 84 Sherlock events; pre-event 60 s retained; E unchanged; regime-matched Basic training.\nN-export tail outage, not physical capture loss. N-FULL is a separate categorical reference.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.13,1,.93]);fig.savefig(figdir/'network_observability_curve.png',dpi=180);fig.savefig(figdir/'network_observability_curve.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13.5,4.4),sharey=True)
    for ax,(model,title) in zip(axes,MODELS.items()):
        points=[];low=[];high=[]
        for r in REGIMES.values():
            v=boots[r][model]['overall']['EN-N']['macro_f1'];points.append(v['point']);low.append(v['ci95'][0]);high.append(v['ci95'][1])
        ax.plot(list(REGIMES),points,color='#6a3d9a',marker='o');ax.fill_between(list(REGIMES),low,high,color='#6a3d9a',alpha=.18)
        ax.axhline(0,color='#555555',linewidth=1,linestyle='--');ax.set_xlim(63,12);ax.set_xticks([60,45,30,15]);ax.set_title(title)
        ax.set_xlabel('Visible post-event network duration (s)');ax.grid(alpha=.2)
    axes[0].set_ylabel('Macro F1(E+N) minus Macro F1(N)')
    fig.suptitle('Exploratory incremental fusion value — paired event bootstrap',y=.99)
    fig.text(.5,.015,'Shading: 95% percentile CI, 2,000 paired resamples within scenario × truth.\nConditional on observed scenarios; not independent confirmation, causal effects, or scenario-population uncertainty.',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.13,1,.93]);fig.savefig(figdir/'delta_fusion_curve.png',dpi=180);fig.savefig(figdir/'delta_fusion_curve.pdf');plt.close(fig)
    lines=['# Protocol v2 — 探索性網路可觀測性結果','',
    '**Exploratory / post-confirmatory：相同、先前已評估的 84 個 Sherlock 事件；不是新的盲測或獨立確認。**',
    '作者已核准固定設計；模型／特徵／可見性程式先通過測試、凍結，再產生這些分數。原 v1 結果保留。','',
    '## 比較方式','',
    '- Basic 35 作原五折 OOF 及最終訓練；Semiurban/Rural 84 作探索性評估。',
    '- LR/RF/GB 使用原超參數、seed=20270921、threshold=0.5；不依新成績調參或選擇 levels。',
    '- N-FULL 原 8 欄；N-TRANSPORT 5 個 header-only 特徵，不讀取 ASDU/COT/U-format/process payload。',
    '- N 的 pre 60 秒保留，post 只可見 60/45/30/15 秒；E 全窗固定。各 regime 在訓練時也施加相同可見性。',
    '- rate/gap 使用實際可見時長；unknown 尾段不當成零流量。這是 N 分析出口尾段不可用，不是全域 raw-source loss。',
    '- 33 個 model/view 條件：9 個原 E/FULL 參考、24 個新條件。原參考的 saved-model predictions 已重現核對。','',
    '## 主量：N 與 EN 的整體 Macro F1 與 ΔFusion','',
    '| 網路條件 | 模型 | N | EN | Δ(EN−N) | 95% paired CI | 改對／改錯 |',
    '|---|---|---:|---:|---:|---|---:|']
    summary=[]
    for regime in ['N_FULL_T60',*REGIMES.values()]:
        for model,title in MODELS.items():
            n=data[regime][model]['N']['overall'];en=data[regime][model]['EN']['overall'];b=boots[regime][model]['overall']['EN-N']['macro_f1']
            tr=[r for r in transitions if r['regime']==regime and r['model']==model];c=Counter(r['transition'] for r in tr)
            lines.append(f"| {regime} | {title} | {fmt(n['macro_f1'])} | {fmt(en['macro_f1'])} | {b['point']:+.3f} | [{b['ci95'][0]:.3f}, {b['ci95'][1]:.3f}] | {c['corrected_N']}/{c['hurt_N']} |")
            summary.append({'regime':regime,'model':model,'N_macro_f1':n['macro_f1'],'EN_macro_f1':en['macro_f1'],'delta':b,'transitions':dict(c)})
    lines += ['', '## E-only 必須一併比較', '',
              '| 模型 | 固定 E-only Macro F1 | TRANSPORT/退化條件的 EN 範圍 |',
              '|---|---:|---|']
    for model,title in MODELS.items():
        ee=data['E_REFERENCE'][model]['E']['overall']['macro_f1']
        ens=[data[r][model]['EN']['overall']['macro_f1'] for r in REGIMES.values()]
        lines.append(f'| {title} | {ee:.3f} | {min(ens):.3f}–{max(ens):.3f} |')
    lines += ['', '**全部 12 個 TRANSPORT/退化 model-condition 中，E-only 的 Macro F1 都高於 EN。**',
              '因此，EN 相對弱化 N 的正增益不等於超過最佳單模態。原 FULL RF/GB 仍由 N 已可完全區分事件。',
              'RF 的 TRANSPORT T60 增益 +0.101，CI 跨零；RF 的 T45/T30/T15 與 GB 的 T45/T15 有較大的描述性增益，',
              '但沒有單調增加规律；LR 在全部條件仍無改善。CI 的條件式限制不變，不能只挑最大的一格。',
              '', '## 事件家族的改對與改錯', '',
              'N-FULL 各模型均無 N→EN 判斷改變。TRANSPORT T60 的 RF 共改對 16 件、改錯 12 件；',
              '其中 Industroyer 改錯 7 件、Drift-off 改對 1／改錯 4，許多良性操作則被改對。',
              'T45 的 RF 改對 15／改錯 0，其中 ARP-spoof DoS 7、Drift-off 4、Control-and-freeze 3、Industroyer 1。',
              '但 T30 的 RF 又改錯 7 件 Industroyer；GB 在 T45/T15 也會改錯部分良性操作。',
              '因此 aggregate F1 增益不能取代逐家族安全錯誤分析；完整所有家族與分母見 family report。']
    lines+=['','![Observability curve](/Users/potinglu/Documents/ICIT2027/results/exploratory-v2/figures/network_observability_curve.png)','',
    '圖：Protocol-v2 探索性結果；x 軸只比較同一 TRANSPORT 語意下的可見秒數，FULL 不混作連續退化刻度。',
    '![Delta fusion](/Users/potinglu/Documents/ICIT2027/results/exploratory-v2/figures/delta_fusion_curve.png)','',
    '區間為 scenario×truth 分層、同 event 配對、2,000 次重抽樣的 percentile CI；全 regime 共用相同抽樣索引。',
    '不代表獨立 simulation runs 或未見場景的不確定性，未作多重比較顯著性宣稱。','',
    '## Balanced accuracy 與錯誤方向','',
    '| 條件 | 模型 | N BA | EN BA | N FP/benign | EN FP/benign | N FN/cyber | EN FN/cyber |',
    '|---|---|---:|---:|---:|---:|---:|---:|']
    for regime in ['N_FULL_T60',*REGIMES.values()]:
        for model,title in MODELS.items():
            n=data[regime][model]['N']['overall'];en=data[regime][model]['EN']['overall']
            lines.append(f"| {regime} | {title} | {fmt(n['balanced_accuracy'])} | {fmt(en['balanced_accuracy'])} | "+' | '.join(count(x) for x in [n['false_cyber_attribution'],en['false_cyber_attribution'],n['missed_cyber'],en['missed_cyber']])+' |')
    lines+=['','## 分場景的 Macro F1','', '| 條件 | 模型 | Semiurban N / EN | Rural N / EN |','|---|---|---|---|']
    for regime in ['N_FULL_T60',*REGIMES.values()]:
        for model,title in MODELS.items():
            cells=[]
            for scene in ['02-Semiurban','03-Rural']:
                cells.append(' / '.join(fmt(data[regime][model][v]['scenario'][scene]['macro_f1']) for v in ['N','EN']))
            lines.append(f'| {regime} | {title} | '+' | '.join(cells)+' |')
    lines+=['','## 保留比例','', '| post 可見秒數 | 時間保留占完整 120 秒 | post packet retention min/median/max |','|---:|---:|---|']
    for t,r in REGIMES.items():
        xs=[row['retention'][r]['packet_retention'] for row in features]
        lines.append(f'| {t} | {(60+t)/120:.1%} | {min(xs):.1%}/{np.median(xs):.1%}/{max(xs):.1%} |')
    lines+=['','原始 E-only 只作一套參考；不是每個 level 重新宣稱另一份 E dataset。',
    '被隱藏的 p IDs、全部禁止的 IEC m IDs、完整 E canonical hash 均保存在 visibility receipts；所有網路特徵從可見 p 重算。','',
    '## 判斷界線','',
    '請同時解讀每個模型、各場景、錯誤方向与非單調曲線；不以最大正 Δ 取代全部矩陣。',
    '觀測到的電氣數值仍可能被操弄，缺失比例也可能攜帶通訊線索；E/N 共用 packet lineage，不是独立感測佐證。',
    '本研究條件是已知起點的 event-conditioned triage，加上已知 regime 的 matched training；不是未知 onset 偵測，',
    '也不是 full-trained 模型在突發 outage 下的部署 robustness。僅五份 recording 且家族不均，限制外推。',
    '任何額外調整需另立版本、維持探索性標記。若要形成確認性主張，需預先註冊後用真正新的資料或獨立模擬驗證。','',
    '## 可追溯產物','',
    '- configs/protocol.v2.lock.json：新成績前的程式／設定／输入雜湊。',
    '- results/exploratory-v2/development/：1155 個 OOF/reference predictions、24 個 Basic-only 模型與每折 training IDs。',
    '- results/exploratory-v2/evaluation/：2772 個 predictions、全部 scenario/recording/family metrics、配對 bootstrap 與 run manifest。',
    '- results/exploratory-v2/transitions/evaluation.json：1260 個 paired event-condition records，含 N/EN scores、改對/改錯/未變、可見性 receipt 路徑和 SHA256。',
    '- results/exploratory-v2/features/visibility/：119 個 private receipts，保存每 level 的 visible/hidden p IDs；不是 runtime/LLM 輸入。',
    '- docs/observability_family_results_v2.md：完整逐家族 paired transition 表。',
    '- results/exploratory-v2/figures/：PNG 與向量 PDF。LLM 尚未實作。']
    (ROOT/'docs/network_observability_results_v2.md').write_text('\n'.join(lines)+'\n')
    (OUT/'evaluation/summary_table.json').write_text(json.dumps({'interpretation':'exploratory / post-confirmatory Protocol v2','rows':summary},indent=2)+'\n')
    family=['# Event-family transitions — Protocol v2 探索性結果','',
        '84 個已觀察過的事件。保留原始 family_description 拼字與各家族分母；不把同事件多 regime/model 當獨立事件。',
        '以下按每個已核准條件完整呈現，包含沒有改變或變差的家族。N-FULL 是既有結果重列。','']
    for regime in ['N_FULL_T60',*REGIMES.values()]:
        family += ['## '+regime,'','| 模型 | 家族 | n | N 正確 | EN 正確 | 改對 | 改錯 | 均對／均錯 |','|---|---|---:|---:|---:|---:|---:|---|']
        for model,title in MODELS.items():
            groups=defaultdict(list)
            for r in transitions:
                if r['regime']==regime and r['model']==model:groups[r['family']].append(r)
            for name,rs in sorted(groups.items()):
                c=Counter(r['transition'] for r in rs)
                family.append(f"| {title} | {name} | {len(rs)} | {sum(r['N_correct'] for r in rs)} | {sum(r['EN_correct'] for r in rs)} | {c['corrected_N']} | {c['hurt_N']} | {c['unchanged_both_correct']}/{c['unchanged_both_wrong']} |")
    (ROOT/'docs/observability_family_results_v2.md').write_text('\n'.join(family)+'\n')
    (figdir/'manifest.json').write_text(json.dumps({'interpretation':'exploratory / post-confirmatory Protocol v2',
        'renderer':'matplotlib','version':matplotlib.__version__,'input_metrics_sha256':hashlib.sha256((OUT/'evaluation/metrics.json').read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')

if __name__=='__main__':main()
