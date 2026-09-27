"""Summarize verified Phase1 v2 outputs without converting candidates into gold."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import gzip
import json
from collections import Counter
from sherlock.io import ROOT,read_json,save_json,sha256

OUT=ROOT/'results/investigation-v2'


def main():
    verified=read_json(OUT/'verification.json')
    if verified['status']!='PASS':raise ValueError('Verification required')
    pilots=read_json(OUT/'pilot_summary.json')['rows'];inventory=read_json(OUT/'supportability_inventory.DRAFT.json')['events']
    all_counts=Counter();pilot_counts=Counter();insufficient=Counter()
    for e in inventory:
        all_counts.update({r['claim_type']:r['supportable_candidate_examples'] for r in e['rows']})
        insufficient.update({r['claim_type']:r['insufficient_probe_examples'] for r in e['rows']})
    for p in pilots:pilot_counts.update({r['claim_type']:r['supportable_candidate_examples'] for r in p['supportability']['rows']})
    eid='ev_0961f1c2da8a257e3ebc';folder=OUT/'B0'/eid/'EN'
    report=read_json(folder/'timeline.json');bundle=read_json(folder/'retrieved.json')
    claim=next(c for c in report['amendment_claims'] if c['claim_type']=='temporal_association')
    index={r['evidence_id']:r for r in bundle['entries']};a=index[claim['payload']['earlier_id']];e=index[claim['payload']['later_id']]
    supported={'status':'DRAFT_UNREVIEWED','event_id':eid,'B0_claim':claim,'command_message':index[a['parent_ids'][0]],'command_address':a,
        'control_mapping':bundle['control_metadata'][a['mapping_evidence_id']],'process_observation':e,'channel_mapping':bundle['metadata'][e['fields']['channel_id']]}
    save_json(OUT/'supported_example.DRAFT.json',supported)
    insuff_eid='ev_363ad64e92cfa74fd5f6';ir=read_json(OUT/'B0'/insuff_eid/'EN/timeline.json')
    probe=next(u for u in ir['amendment_insufficiency'] if u['reason']=='no_valid_later_same_asset_E_in_allowed_window')
    with gzip.open(OUT/'B0'/insuff_eid/'EN/eligible.json.gz','rt') as f:ip=json.load(f)
    same=[r for r in ip['records'] if r['source_type']=='process' and r['asset_id']==probe['mapped_asset_id'] and r['value'] is not None and not r['quality_flags']]
    bad={'status':'DRAFT_UNREVIEWED','event_id':insuff_eid,'B0_insufficiency':probe,'complete_window_valid_same_asset_E_count':len(same),
        'interpretation':'The mapping is available, but no qualifying same-asset E observation supports the cross-source link; no conclusion about execution or safety.'}
    save_json(OUT/'insufficient_example.DRAFT.json',bad)
    c=verified['counts']
    lines=['# Investigation Phase 1 — command-target amendment v2 results','',
        '本次作者核准範圍已完成：schema/policy、address adapter、static mapping、retrieval/receipts、B0、四份人工審查包。已停在 Phase 1；未實作 B1–B4，LLM calls = 0，human gold = 0。','',
        '## 1. 版本與邊界','',
        '`investigation-export-v2`、`investigation-command-address-v2`、`investigation-retrieval-v2`、`investigation-claim-v2`、`investigation-verification-v2`、`investigation-b0-v2`。',
        '設定：configs/investigation.phase1.v2.json；實作快照：configs/investigation_phase1.v2.lock.json。此為本次實作快照，並非 Investigation Protocol v1 最終凍結。',
        'B0 保留原有決定性觀測索引，新增 amendment_claims 採 typed claim v2 並逐條有限一致性檢查；verification schema 已修正，但完整 B3/任意自然語言 verifier 尚未實作。',
        '只解析已審核的 45/47/50；46/48/49/51 沒有 evaluated support。Raw CA/IOA 只在 private_provenance；控制值、初始值、select/execute、G/labels 不進 public address evidence。',
        '舊分類鎖、Phase1 v1 鎖均通過；144 份新版的 canonical E/N 投影逐份等於舊版，分類 contracts/features/models/results 未修改。','',
        '## 2. 驗證','',
        f"{verified['tests']['passed']} / {verified['tests']['tests']} tests PASS，包含 27 項新增 amendment 測試。144 條件的 output hashes、retrieval/B0 replay、原始 E/N 投影、映射雙邊、時間差、derived arithmetic、gap 與四包 lineage 均通過。",
        '完整機械驗證：results/investigation-v2/verification.json。測試指令：`.venv/bin/python -m unittest discover -s tests -q`。','',
        '## 3–4. 精確數量','',
        '| 完整 48 事件 EN universe | 數量 |','|---|---:|',
        f"| command-address children | {c['address_children']} |",f"| exact_static_match | {c['exact_mapped_children']} |",
        f"| 有同資產有效 E | {c['same_asset_valid_E_children']} / {c['address_children']} |",f"| 有較晚同資產有效 E | {c['same_asset_later_valid_E_children']} / {c['address_children']} |",
        f"| activation request children（COT=6） | {c['request_children']} |",f"| request 有較晚同資產有效 E | {c['same_asset_later_valid_E_requests']} / {c['request_children']} |",
        f"| EN B0 實際呈現同資產 temporal candidates | {c.get('EN_temporal_association',0)} |",'',
        '98 = 49 request + 49 activation-confirmation 地址子證據。類型 45:76、47:4、50:18。88 包含 request 與 response；44 是 request 的同資產時間關聯候選。其餘 5 個 request 雖 mapped 但缺同資產有效 E。',
        '以上為 evidence/candidate counts，不是 98 個事件，也不是 gold recall、模型準確率或 fusion superiority。','',
        '## 5. 有支援的 B0 範例','',f'Event `{eid}`，EN，claim `{claim["claim_id"]}`。','',
        f"- request `{a['parent_ids'][0]}`：ASDU {a['asdu_type']}、COT 6、capture t={a['observation_time']:.9f}s。",
        f"- address `{a['evidence_id']}` → `{a['mapped_control_point_id']}` → `{a['mapped_target_asset_id']}`，static M `{a['mapping_evidence_id']}`。",
        f"- E `{e['evidence_id']}` → channel `{e['fields']['channel_id']}` → 同一 asset，static M `{supported['channel_mapping']['evidence_id']}`；capture t={e['observation_time']:.9f}s，reported value={e['value']}。",
        f"- capture Δt={claim['payload']['delta_seconds']:.9f}s，兩條靜態映射一致。",'',
        '**這是 asset-linked temporal evidence。不是 execution proof、causal proof 或 malicious-intent proof。** 本例所引用的 boolean 僅支援 reported_value，並非 state change。',
        '完整可核對範例：results/investigation-v2/supported_example.DRAFT.json。','',
        '## 6. 不足範例','',f"Event `{insuff_eid}`：asset `{probe['mapped_asset_id']}` 的 command mapping 成功，但完整窗口同資產有效 E = {len(same)}；B0 明列 `{probe['reason']}`。這不是 top-k 遺漏，也不代表命令失敗或安全。",
        '完整範例：results/investigation-v2/insufficient_example.DRAFT.json。','',
        '## 7. 四份核准 pilot 包','',
        '| Event | p / m / E / a 完整筆數 | request / 同資產較晚 E | EN B0 links |','|---|---|---|---:|']
    for p in sorted(pilots,key=lambda p:p['event_id']):
        n=p['counts'];ac=p['supportability']['address_counts']
        lines.append(f"| {p['event_id']} | {n['packet']} / {n['message']} / {n['process']} / {n.get('command_address_observation',0)} | {ac['request_children']} / {ac['same_asset_later_valid_E_requests']} | {p['retrieved_EN_same_asset_temporal_claims']} |")
    lines+=['','Packets：annotations/events-v2/<event_id>/。每包都有完整允許 evidence、lineage、numeric candidates、E/N/EN retrieval+receipt+B0、13 類 supportability inventory 與空白人工 annotation/signoff。',
        '四包全部 DRAFT_UNREVIEWED；兩個無 request pilot 保留 no_command_request_in_allowed_window。reported_state_change 在四包皆 0。','',
        '## 8–9. 修訂 ontology inventory 與目前不可用類型','',
        '下表是完整 universe 的機械候選／探測數；不是人工 gold、metric 分母或互斥事實總數。','',
        '| Claim type | 48 事件候選 | 四 pilot 候選 | 解讀 |','|---|---:|---:|---|']
    notes={'reported_state_change':'0；留作 optional，不列最低充分性','reported_change':'與 electrical_change 共用 pair，禁止雙算 gold',
        'electrical_change':'reported_change alias，待人工定義合併','temporal_association':'44 個 request address 有較晚同資產 E；非因果',
        'asset_relationship':'E channel mapping + 49 command-address mapping；需人工選 meaningful facts',
        'security_indicator':'0 個已建立語意的正候選；不是缺少原始 primitive',
        'security_interpretation':'0；強安全結論均未建立',
        'unknown':'每事件固定 7 個 guardrail subjects，非獨立事件',
        'acknowledgement_observed':'TCP ACK / S-frame / COT7 候選混合，需分語意',
        'communication_gap':'完整 captured TCP2404 query，不證明 outage'}
    for kind,n in all_counts.items():lines.append(f"| {kind} | {n} | {pilot_counts[kind]} | {notes.get(kind,'需人工挑選、去重與確認 support sets')} |")
    lines+=['','目前 `reported_state_change` 沒有可觀察的合格正例；`security_interpretation` 沒有可支持的 execution/causal/intent/success/attribution 正例。`security_indicator` 的安全相關性尚待人工定義與審查，不把 primitive 自動升級為 attack evidence。',
        '完整逐事件 inventory：results/investigation-v2/supportability_inventory.DRAFT.json；四包另有局部 inventory。','',
        '## 10. 最終凍結前仍待決定','',
        '1. 人工審查四包：meaningful atomic facts、aliases/duplicates、alternative minimal support sets、unknowns/較強不支持敘述與 verifier 可行性；指定 reviewer 與 adjudication 流程。',
        '2. 根據 pilot 定稿 ontology：reported_change/electrical_change 去重；security_indicator 可操作定義；reported_state_change 保留 optional（已核准，不重問）。',
        '3. 定稿 Q1–Q7 answerability 與最低支持組，尤其 Q5 episode-only 與 same-asset 的計分分界、Q6 不把 primitive 當惡意證據；固定 metric 分母與 NA 規則。',
        '4. 本次 EN 新增依已觀察 command asset 優先檢索較晚 E，屬於 v2 系統改動；確認正式比較共用此版本，且每 view 預算上限 64 entries（EN 32+32）、48k bytes；待模型選定再補實際 token cap。',
        '5. 後續階段另行核准並固定模型/provider/snapshot、sampling/seed、輸入與輸出 token cap、prompt、重試與成本；目前未做 B1–B4，也未送任何 LLM API。',
        '6. 人工 gold、policy、retrieval、schema、prompts、metrics 與 model/code hashes 齊備後，才可稱 Investigation Protocol v1 正式凍結。事件 IDs 維持已核准的 16 development + 32 evaluation，這些資料已被檢視，不能稱 untouched test。','',
        '這次修改使可證實的跨域上限到達「同資產 capture-time 時間關聯」，尚未提供融合勝過網路單模態的效能證據。','']
    (ROOT/'docs/investigation_phase1_amendment_v2_results.md').write_text('\n'.join(lines))
    summary={'status':'PHASE1_AMENDMENT_COMPLETE_AWAITING_HUMAN_REVIEW','verification':verified,'pilot_paths':[p['packet_path'] for p in pilots],
        'inventory_counts':dict(all_counts),'pilot_inventory_counts':dict(pilot_counts),'supported_example':supported,'insufficient_example':bad,
        'report':'docs/investigation_phase1_amendment_v2_results.md','llm_calls':0,'human_gold_events':0,'B1_B4_implemented':False}
    save_json(OUT/'completion_summary.json',summary)
    print('Wrote completion summary and author report')


if __name__=='__main__':main()
