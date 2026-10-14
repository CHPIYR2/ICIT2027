"""Build a small Pilot Candidate Pool from unused Sherlock windows for human annotation.

Guarantees:
- Never reads or exposes official event descriptions, attack types, `malicious`
  flags, or `physical.zip`.
- Never uses LLM choices or selector scores to create gold labels.
- Preserves atomic observations across network TCP flows, IEC-104 (entity, CA/IOA)
  points, and IPAL electrical updates, with complete evidence lineage.
- Emits de-identified, order-shuffled candidate packets for Annotator A and
  Annotator B, plus a custodian key for scoring after human adjudication.
"""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path
from ..evidence.index import index_window, open_indexed
from ..evidence.queries import EvidenceDB
from .eval_t3 import build_full_candidate_pool, stage1_baselines
from .pipeline import export_lineage_bundle, prepare


def build_pilot_package(windows: list[dict], out_dir: Path, *,
                        archive: Path = Path("data/raw/sherlock/v3/01-Basic.zip"),
                        context_seconds: float = 15.0) -> dict:
    if out_dir.exists():
        raise FileExistsError(f"{out_dir} already exists; refusing to overwrite")
    out_dir.mkdir(parents=True)
    custodian_dir = out_dir / "custodian"
    annotator_dir = out_dir / "annotator_pack"
    custodian_dir.mkdir()
    annotator_dir.mkdir()

    manifest_windows = []
    custodian_map = {}

    for idx, win in enumerate(windows, start=1):
        blind_wid = f"PILOT-W{idx:02d}"
        ep_id = win["episode_id"]
        scenario = win.get("scenario", "01-Basic")
        recording = win.get("recording", "test")
        start = float(win["start"])
        end = float(win["end"])

        win_cust_dir = custodian_dir / blind_wid
        win_cust_dir.mkdir()
        db_path = win_cust_dir / "evidence.sqlite"
        if win.get("db") and Path(win["db"]).exists():
            db_path = Path(win["db"])
        else:
            index_window(
                archive, scenario=scenario, recording=recording,
                start=start, end=end, out=db_path,
                context_seconds=context_seconds, modalities="both",
            )
        conn, meta = open_indexed(db_path)
        bg_start = max(start - context_seconds, float(meta.get("indexed_start") or (start - context_seconds)))
        db = EvidenceDB(conn, incident_start=start, incident_end=end)

        prepared = prepare(db, start, end, background_start=bg_start, background_end=start, limit=24)
        full_pool = build_full_candidate_pool(db, start, end, background_start=bg_start, background_end=start)
        # Export lineage across the selected 24 timeline events AND full candidate pool
        selected_bundle = export_lineage_bundle(db, prepared["timeline"], prepared["lineage"])
        full_tid_lineage = {e["timeline_id"]: full_pool["unit_lineage"][e["unit_id"]] for e in full_pool["candidates"]}
        full_bundle = export_lineage_bundle(db, full_pool["candidates"], full_tid_lineage)

        # Build bounded pilot annotation pool: the 24 selected atomic timeline facts
        # (which include TCP flows, IEC-104 control & monitor points, and IPAL electrical updates)
        pilot_units = prepared["timeline"]
        unit_forward, unit_inverse, blind_units = _deidentify_units(pilot_units, start)

        # Shuffle independently for Annotator A and Annotator B so order carries no selector rank
        pack_a = _shuffled_pack(blind_wid, start, end, blind_units, seed=100 + idx, annotator="A")
        pack_b = _shuffled_pack(blind_wid, start, end, blind_units, seed=200 + idx, annotator="B")
        template = _response_template(blind_wid, pack_a["units"])

        (annotator_dir / f"{blind_wid}_annotator_A.json").write_text(
            json.dumps(pack_a, indent=2, default=str), encoding="utf-8",
        )
        (annotator_dir / f"{blind_wid}_annotator_B.json").write_text(
            json.dumps(pack_b, indent=2, default=str), encoding="utf-8",
        )
        (annotator_dir / f"{blind_wid}_response_template.json").write_text(
            json.dumps(template, indent=2, default=str), encoding="utf-8",
        )

        stage1 = stage1_baselines(full_pool, prepared["exposed_timeline"], k=10, seeds=50)
        (win_cust_dir / "prepared_timeline.json").write_text(
            json.dumps(prepared["timeline"], indent=2, default=str), encoding="utf-8",
        )
        (win_cust_dir / "exposed_10_cards.json").write_text(
            json.dumps(prepared["exposed_timeline"], indent=2, default=str), encoding="utf-8",
        )
        (win_cust_dir / "full_candidate_pool.json").write_text(
            json.dumps({k: v for k, v in full_pool.items() if k != "unit_lineage"}, indent=2, default=str),
            encoding="utf-8",
        )
        (win_cust_dir / "evidence_audit_bundle.json").write_text(
            json.dumps(selected_bundle, indent=2, default=str), encoding="utf-8",
        )
        (win_cust_dir / "full_pool_lineage_bundle.json").write_text(
            json.dumps({k: v for k, v in full_bundle.items() if k != "rows"}, indent=2, default=str),
            encoding="utf-8",
        )
        (win_cust_dir / "stage1_baselines.json").write_text(
            json.dumps(stage1, indent=2, default=str), encoding="utf-8",
        )
        conn.close()

        by_mod = {}
        by_role = {}
        for u in pilot_units:
            mod = (u.get("source") or {}).get("modality") or "unknown"
            by_mod[mod] = by_mod.get(mod, 0) + 1
            role = u.get("role") or "unknown"
            by_role[role] = by_role.get(role, 0) + 1

        custodian_map[blind_wid] = {
            "blind_window_id": blind_wid,
            "episode_id": ep_id,
            "scenario": scenario,
            "recording": recording,
            "incident_start": start,
            "incident_end": end,
            "background_start": bg_start,
            "background_end": start,
            "unit_forward_map_timeline_to_blind": unit_forward,
            "unit_inverse_map_blind_to_unit": unit_inverse,
        }
        manifest_windows.append({
            "blind_window_id": blind_wid,
            "episode_id": ep_id,
            "duration_seconds": round(end - start, 3),
            "full_atomic_candidate_count": full_pool["candidate_count"],
            "pilot_annotation_unit_count": len(pilot_units),
            "pilot_units_by_modality": by_mod,
            "pilot_units_by_role": by_role,
            "selected_lineage_bundle": {
                k: selected_bundle[k]
                for k in ("requested_count", "expected_with_parents", "exported_count", "missing_ids", "row_check_failures")
            },
            "full_pool_lineage_check": {
                k: full_bundle[k]
                for k in ("requested_count", "expected_with_parents", "exported_count", "missing_ids", "row_check_failures")
            },
        })

    (custodian_dir / "custodian_key.json").write_text(
        json.dumps(custodian_map, indent=2, default=str), encoding="utf-8",
    )
    (annotator_dir / "ANNOTATION_INSTRUCTIONS_zh-TW.md").write_text(
        _instructions_markdown(), encoding="utf-8",
    )
    summary = {
        "status": "READY_FOR_HUMAN_ANNOTATION",
        "gold_included": False,
        "llm_outputs_included": False,
        "official_event_descriptions_used": False,
        "window_count": len(manifest_windows),
        "windows": manifest_windows,
    }
    (out_dir / "pilot_manifest.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def _deidentify_units(events: list[dict], window_start: float) -> tuple[dict, dict, list[dict]]:
    """Assign deterministic blind unit IDs without leaking selector rank."""
    # Sort by hash of timeline_id + entity before assigning U001..U024
    ordered = sorted(
        events,
        key=lambda e: hashlib.sha256(f"{e['timeline_id']}:{e['entity']}:{e.get('ca_ioa')}".encode("utf-8")).hexdigest(),
    )
    forward = {}
    inverse = {}
    for idx, event in enumerate(ordered, start=1):
        b_id = f"U{idx:03d}"
        tid = event["timeline_id"]
        kind = (event.get("source") or {}).get("kind") or "unknown"
        uid = f"{kind}|{event['entity']}|{event['ca_ioa']}" if event.get("ca_ioa") else f"{kind}|{event['entity']}"
        forward[tid] = b_id
        inverse[b_id] = {
            "timeline_id": tid,
            "unit_id": uid,
            "entity": event["entity"],
            "ca_ioa": event.get("ca_ioa"),
            "role": event["role"],
            "modality": (event.get("source") or {}).get("modality"),
        }

    # Map shared parent frames to blind unit IDs so annotators know when two points share one frame
    parent_to_blind: dict[str, list[str]] = {}
    for event in ordered:
        b_id = forward[event["timeline_id"]]
        for pid in event.get("lineage") or []:
            parent_to_blind.setdefault(pid, []).append(b_id)

    blind_units = []
    for event in ordered:
        b_id = forward[event["timeline_id"]]
        siblings = sorted({
            other for pid in (event.get("lineage") or [])
            for other in parent_to_blind.get(pid, [])
            if other != b_id
        })
        item = {
            "blind_unit_id": b_id,
            "relative_start_sec": round(float(event["time"]) - window_start, 4),
            "relative_end_sec": round(float(event["time_end"]) - window_start, 4),
            "timestamp_start": event["time"],
            "timestamp_end": event["time_end"],
            "modality": (event.get("source") or {}).get("modality"),
            "kind": (event.get("source") or {}).get("kind"),
            "role": event["role"],
            "record_class": event["record_class"],
            "entity": event["entity"],
            "ca_ioa": event.get("ca_ioa"),
            "vantages": (event.get("source") or {}).get("vantages"),
            "observation_summary": event["observation"],
            "evidence_ids_preview": event["evidence_ids"],
            "evidence_id_count": event["evidence_id_count"],
            "shared_source_frame_with_units": siblings,
            "independent_from_parent_packet": event.get("independent", True),
        }
        if event.get("value_present"):
            item["measurement"] = {
                "value_first": event.get("value_first"),
                "value_last": event.get("value_last"),
                "value_min": event.get("value_min"),
                "value_max": event.get("value_max"),
                "distinct_frame_samples": event.get("sample_count"),
            }
        elif event.get("packet_count") is not None:
            item["flow_counts"] = {
                "packet_count_sum_vantages": event.get("packet_count"),
                "packet_count_by_vantage": event.get("packet_count_by_vantage"),
                "distinct_frame_count": event.get("distinct_frame_count"),
                "packet_bytes_min": event.get("packet_bytes_min"),
                "packet_bytes_max": event.get("packet_bytes_max"),
            }
        else:
            item["frame_counts"] = {
                "distinct_source_frames": event.get("source_frame_count"),
            }
        blind_units.append(item)
    return forward, inverse, blind_units


def _shuffled_pack(blind_wid: str, start: float, end: float,
                   blind_units: list[dict], *, seed: int, annotator: str) -> dict:
    rng = random.Random(seed)
    units = list(blind_units)
    rng.shuffle(units)
    return {
        "blind_window_id": blind_wid,
        "annotator": annotator,
        "presentation_shuffle_seed": seed,
        "window_duration_seconds": round(end - start, 3),
        "window_start_timestamp": start,
        "window_end_timestamp": end,
        "note": (
            "Units are shuffled with a fixed seed. Selector scores, ranks, scenario names, "
            "and model outputs are withheld. IEC-104 and IPAL points for the same mapped entity "
            "are network-reported and are not independent physical confirmation."
        ),
        "unit_count": len(units),
        "units": units,
    }


def _response_template(blind_wid: str, units: list[dict]) -> dict:
    return {
        "blind_window_id": blind_wid,
        "annotator_id": "FILL_ANNOTATOR_ID",
        "window_sufficiency": "FILL_ONE_OF: sufficient | insufficient | cannot_judge",
        "unit_judgments": [
            {
                "blind_unit_id": u["blind_unit_id"],
                "necessity": "FILL_ONE_OF: needed | useful | not_needed | cannot_judge",
                "side": "FILL_ONE_OF: network | electrical | both",
                "basis": "FILL_SHORT_REASON_CITING_VALUES_OR_EV_IDS",
            }
            for u in units
        ],
    }


def _instructions_markdown() -> str:
    return """# MIRAGE-OT T3 Pilot 人類標註說明（去識別化候選池）

## 1. 標註目的與原則
本標註包用於評估工業控制系統（CPS）告警後事件調查管線之**證據選擇品質（Evidence Selection）**。
- 您看到的是單一可疑時間視窗內的**原子觀測單元（Atomic Candidate Units）**。
- 所有單元已移除統計排序分數、模型輸出、場景名稱、攻擊類別與官方事件文字，並依固定種子隨機排列，**呈現順序不代表重要性**。
- **來源獨立性提醒**：
  1. 同一乙太網／IEC-104 封包在多個交換器鏡像埠（如 `n302`、`n318`）被擷取屬於同一來源，已合併並標註 `distinct_frame_count` 或 `distinct_frame_samples`。
  2. 同一 IEC-104 封包若攜帶多個資訊物件（不同 `CA/IOA`），其 `shared_source_frame_with_units` 會列出同封包的其他單元；它們共享同一網路封包容器，並非獨立來源。
  3. 電力側 `electrical_update`（IPAL 狀態更新）在 Sherlock 中源自網路協定解碼後的狀態表，與對應的 `iec104_asdu` 點位屬於同一通訊來源，不可當作獨立的物理感測器驗證。

## 2. 每個單元的標註欄位
請在對應的 `*_response_template.json` 中，為每個 `blind_unit_id` 填寫：
1. `necessity`（擇一）：
   - `needed`（權重 2）：若缺少此單元，對該視窗內網路控制／通訊活動或電力狀態變化的調查報告將會不完整或遺漏關鍵變化。
   - `useful`（權重 1）：可提供輔助佐證（例如同一點位在另一層級的轉錄紀錄、或次要背景流量），但即使沒有它，主要事件過程仍可由其他 `needed` 單元完整呈現。
   - `not_needed`（權重 0）：與說明該視窗的主要變化無關之常規背景紀錄。
   - `cannot_judge`（權重 0）：僅憑現有欄位無法判斷。
2. `side`（擇一）：`network`、`electrical` 或 `both`。
3. `basis`：簡短說明標註理由，請引用該單元的數值變化、角色（如 `command`、`electrical_change`）或 `EV-...` 編號。

## 3. 視窗整體的標註欄位
- `window_sufficiency`：`sufficient`（池內證據足以整理出該視窗的觀測摘要）、`insufficient`（證據不足，系統應棄權或僅輸出最低限度觀測清單）或 `cannot_judge`。
- 本標註**不標註因果關係或攻擊分類**。
"""
