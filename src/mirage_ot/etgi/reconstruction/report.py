"""Phase 4: Evidence-Grounded Investigation Explanation & Report Renderer.

Uses Typed References and the Deterministic Verifier (`verify_claims`) over the
reconstructed transactions, temporal event graph, and storylines.
- The LLM selects structured anchors (`selected_transaction_ids`,
  `selected_storyline_ids`, and typed `claims` referencing `fact_id` / `edge_id`).
- The LLM never regenerates raw timestamps, IP addresses, CA/IOA strings, or
  measurement numbers in public report prose.
- Every prose line in `investigation_report.md` is rendered deterministically
  from verified claims and trusted reconstruction records. Unconfirmed cross-entity
  links are presented strictly as unresolved hypotheses.
"""
from __future__ import annotations
import json
from ..postalert.explain import _TYPED_CLAIM_ITEM, _object
from ..postalert.verify import verify_claims

SYSTEM_RECONSTRUCTION = """You are an ICS post-alert reconstruction analyst.
You receive JSON containing reconstructed IEC-104 protocol transactions, event-level
timeline facts, candidate graph edges, and reconstructed storylines.
Do not rewrite timestamps, IP addresses, CA/IOA strings, or measurement numbers.
Return one JSON object with keys:
- abstain (boolean)
- selected_transaction_ids (array of "TX..." strings)
- selected_storyline_ids (array of "SL..." strings)
- claims (array of typed claim objects referencing fact_id "EF..."/"TL..." or edge_id "R...")

Strict rules for claims:
- For a single timeline fact: {"claim_type": "observation_claim" or "measurement_claim", "fact_id": "<exact fact_id>", "claim_level": "observed_fact"}
- For a graph edge: {"claim_type": "relation_claim", "edge_id": "<exact edge_id>", "relation_type": "<exact edge relation_type>", "claim_level": "<exact edge claim_level>"}
- Never upgrade an observed_fact or temporal_cooccurrence edge to supported_inference.
- Keep at most 8 claims. Do not state a physical cause or attack label.
"""

RECONSTRUCTION_SCHEMA = {
    "type": "object",
    "properties": {
        "abstain": {"type": "boolean"},
        "selected_transaction_ids": {"type": "array", "items": {"type": "string"}},
        "selected_storyline_ids": {"type": "array", "items": {"type": "string"}},
        "claims": {"type": "array", "items": _TYPED_CLAIM_ITEM},
    },
    "required": ["abstain", "selected_transaction_ids", "selected_storyline_ids", "claims"],
}


def run_llm_explanation(
    db,
    llm,
    *,
    incident_start: float,
    incident_end: float,
    tx_result: dict,
    event_graph: dict,
    storyline_result: dict,
    num_predict: int = 512,
    num_ctx: int = 8192,
    seed: int = 1,
) -> dict:
    prompt_payload = _compact_prompt_payload(
        incident_start, incident_end, tx_result, event_graph, storyline_result,
    )
    if llm is None:
        return {
            "mode": "deterministic_only",
            "abstain": False,
            "partial_output": False,
            "selected_transaction_ids": [t["transaction_id"] for t in tx_result["transactions"]],
            "selected_storyline_ids": [s["storyline_id"] for s in storyline_result["storylines"]],
            "raw_claims": [],
            "verification": {"verified": [], "rejected": []},
            "prompt_payload": prompt_payload,
            "raw_output": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "done_reason": "deterministic",
            "model": "deterministic_renderer",
        }

    messages = [
        {"role": "system", "content": SYSTEM_RECONSTRUCTION},
        {"role": "user", "content": json.dumps(prompt_payload, default=str)},
    ]
    turn = llm.chat(
        messages, tools=None, temperature=0, seed=seed,
        num_predict=num_predict, num_ctx=num_ctx, response_format=RECONSTRUCTION_SCHEMA,
    )
    parsed = _object(turn.content, allow_salvage=False)
    partial = bool(turn.done_reason == "length" or parsed.get("json_truncated"))
    raw_claims = [c for c in (parsed.get("claims") or []) if isinstance(c, dict)] if not partial else []

    valid_tx_ids = {t["transaction_id"] for t in tx_result["transactions"]}
    valid_sl_ids = {s["storyline_id"] for s in storyline_result["storylines"]}
    sel_tx = [
        tid for tid in (parsed.get("selected_transaction_ids") or [])
        if isinstance(tid, str) and tid in valid_tx_ids
    ]
    sel_sl = [
        sid for sid in (parsed.get("selected_storyline_ids") or [])
        if isinstance(sid, str) and sid in valid_sl_ids
    ]

    checked = verify_claims(
        db,
        raw_claims,
        event_graph["edges"],
        event_graph["nodes"],
        lineage=event_graph["fact_lineage"],
    )
    return {
        "mode": "llm_typed_refs_with_verifier",
        "abstain": bool(parsed.get("abstain")) and not partial and not raw_claims,
        "partial_output": partial,
        "selected_transaction_ids": list(dict.fromkeys(sel_tx)),
        "selected_storyline_ids": list(dict.fromkeys(sel_sl)),
        "raw_claims": raw_claims,
        "verification": checked,
        "prompt_payload": prompt_payload,
        "raw_output": turn.content,
        "prompt_tokens": turn.prompt_tokens,
        "completion_tokens": turn.completion_tokens,
        "done_reason": turn.done_reason,
        "model": getattr(turn, "model", "") or getattr(llm, "model_name", ""),
    }


def build_investigation_report(
    *,
    incident_start: float,
    incident_end: float,
    tx_result: dict,
    event_graph: dict,
    storyline_result: dict,
    explanation: dict,
) -> dict:
    verified_claims = explanation["verification"].get("verified") or []
    rejected_claims = explanation["verification"].get("rejected") or []
    nodes_by_id = {n["fact_id"]: n for n in event_graph["nodes"]}

    # 1. Incident Sequence & Protocol Transactions (Trusted Data Only)
    tx_summaries = []
    for tx in tx_result["transactions"]:
        tx_summaries.append({
            "transaction_id": tx["transaction_id"],
            "start_time": tx["start_time"],
            "end_time": tx["end_time"],
            "entity": tx["entity"],
            "ca_ioa": tx["ca_ioa"],
            "type_name": tx["type_name"],
            "commanded_value": tx["commanded_value"],
            "session": f"{tx['master_ip']}:{tx['master_port']} -> {tx['rtu_ip']}:{tx['rtu_port']}",
            "vantages": tx["command_activation"]["vantages"],
            "command_acceptance_status": tx["command_acceptance_status"],
            "device_state_change_status": tx["device_state_change_status"],
            "transaction_completeness": tx["transaction_completeness"],
            "missing_stages": tx["missing_stages"],
            "evidence_ids": tx["all_evidence_ids"][:6],
        })

    # 2. Key Findings & Reconstructed Storylines
    storyline_summaries = []
    for sl in storyline_result["storylines"]:
        steps_rendered = []
        for st in sl["confirmed_and_supported_steps"]:
            s_node = nodes_by_id[st["source_fact_id"]]
            t_node = nodes_by_id[st["target_fact_id"]]
            indep_tag = "independent_evidence" if st["independent_support"] else "shared_source_not_double_counted"
            steps_rendered.append(
                f"Step {st['step_index']} [{st['edge_id']} | {st['modality_pair']} | {st['relation_type']} | "
                f"level={st['claim_level']} | {indep_tag}]: "
                f"{st['source_fact_id']} ({s_node['entity']} @ {round(s_node['time'], 4)}) -> "
                f"{st['target_fact_id']} ({t_node['entity']} @ {round(t_node['time'], 4)}) "
                f"[{', '.join(st['evidence_ids'][:4])}]"
            )
        storyline_summaries.append({
            "storyline_id": sl["storyline_id"],
            "transaction_id": sl["transaction_id"],
            "anchor_entity": sl["anchor_entity"],
            "completeness_status": sl["completeness_status"],
            "spine_fact_ids": sl["spine_fact_ids"],
            "independent_source_container_count": sl["independent_source_container_count"],
            "independent_support_edge_count": sl["independent_support_edge_count"],
            "steps_rendered": steps_rendered,
            "evidence_gaps": sl["evidence_gaps"],
        })

    # 3. Potential Impact (Confirmed Device Transitions vs Unresolved Cross-Entity Co-occurrence)
    confirmed_impacts = []
    for tx in tx_result["transactions"]:
        if tx["device_state_change_status"] == "state_change_observed":
            if tx["protocol_state_feedback"]:
                fb = tx["protocol_state_feedback"][0]
                ipal_vals = [u["value"] for u in tx["ipal_state_updates"] if u["entity"] == tx["entity"]]
                confirmed_impacts.append(
                    f"[{tx['transaction_id']}] Device {tx['device_stem']} reported spontaneous state feedback "
                    f"{fb['entity']} (CA/IOA={fb['ca_ioa']}, COT=3) at {round(fb['timestamp'], 4)} "
                    f"(IPAL state value={ipal_vals[0] if ipal_vals else 'n/a'}, network-reported) "
                    f"[{', '.join(fb['evidence_ids'][:2])}]."
                )
            if tx["measurement_transition"]:
                mt = tx["measurement_transition"]
                confirmed_impacts.append(
                    f"[{tx['transaction_id']}] Controlled generator point {mt['measurement_entity']} "
                    f"(CA/IOA={mt['ca_ioa']}) shifted from {mt['pre_command_value']} "
                    f"(@ {round(float(mt['pre_command_time']), 4)}) to {mt['post_command_value']} "
                    f"(@ {round(float(mt['post_command_time']), 4)}), matching commanded setpoint "
                    f"{mt['commanded_setpoint']} [{', '.join(mt['post_command_evidence_ids'][:2])}]."
                )

    unresolved_impacts = []
    for sl in storyline_result["storylines"]:
        for br in sl["unresolved_cooccurrence_branches"][:4]:
            unresolved_impacts.append(
                f"[{sl['storyline_id']} / {br['edge_id']}] Unresolved temporal co-occurrence "
                f"(level={br['claim_level']}, status={br['verification_status']}, causal_status=not_established): "
                f"{br['candidate_entity']} ({br['candidate_fact_id']}) changed at {round(br['candidate_time'], 4)} "
                f"({br['temporal_condition']}) [{', '.join(br['evidence_ids'][:2])}]."
            )

    # 4. Alternative Explanations & Competing Hypotheses
    competing_hypotheses = [
        {"storyline_id": sl["storyline_id"], **comp}
        for sl in storyline_result["storylines"]
        for comp in sl["competing_hypotheses"]
    ]

    # 5. Unresolved Questions, Evidence Gaps & Unconnected Observations
    evidence_gaps = []
    for tx in tx_result["transactions"]:
        if tx["missing_stages"]:
            evidence_gaps.append({
                "scope": tx["transaction_id"],
                "entity": tx["entity"],
                "missing_stages": tx["missing_stages"],
            })
    if tx_result["unpaired_protocol_messages"]:
        evidence_gaps.append({
            "scope": "unpaired_protocol_messages",
            "count": len(tx_result["unpaired_protocol_messages"]),
        })

    report = {
        "incident_start": incident_start,
        "incident_end": incident_end,
        "transaction_summaries": tx_summaries,
        "storyline_summaries": storyline_summaries,
        "verified_llm_claims": [
            {
                "claim_type": c.get("claim_type"),
                "fact_id": c.get("fact_id"),
                "edge_id": c.get("edge_id"),
                "claim_level": c.get("claim_level"),
                "rendered_text": c.get("rendered_text"),
                "evidence_ids": c.get("evidence_ids"),
            }
            for c in verified_claims
        ],
        "withheld_rejected_llm_claim_count": len(rejected_claims),
        "confirmed_device_impacts": confirmed_impacts,
        "unresolved_cooccurring_changes": unresolved_impacts,
        "competing_hypotheses": competing_hypotheses,
        "evidence_gaps": evidence_gaps,
        "unattached_observations": storyline_result["unattached_observations"],
    }
    report["markdown"] = render_investigation_markdown(report)
    return report


def render_investigation_markdown(report: dict) -> str:
    lines = [
        "# Evidence-Grounded Incident Reconstruction Report",
        "",
        f"- **Incident Window**: `{report['incident_start']}` to `{report['incident_end']}`",
        f"- **Reconstructed IEC-104 Transactions**: `{len(report['transaction_summaries'])}`",
        f"- **Reconstructed Event Storylines**: `{len(report['storyline_summaries'])}`",
        f"- **Verified LLM Claims Published**: `{len(report['verified_llm_claims'])}` "
        f"(withheld unverified claims: `{report['withheld_rejected_llm_claim_count']}`)",
        "",
        "## 1. Incident Sequence & Protocol Transactions",
    ]
    if not report["transaction_summaries"]:
        lines.append("- No IEC-104 control transactions were observed in this window.")
    for tx in report["transaction_summaries"]:
        lines.append(
            f"- **{tx['transaction_id']}** (`{tx['start_time']:.4f}`–`{tx['end_time']:.4f}`): "
            f"`{tx['type_name']}` on `{tx['entity']}` (`CA/IOA={tx['ca_ioa']}`, value=`{tx['commanded_value']}`) "
            f"over `{tx['session']}` at vantages `{tx['vantages']}`. "
            f"**Command Acceptance**: `{tx['command_acceptance_status']}`; "
            f"**Device State Change**: `{tx['device_state_change_status']}`; "
            f"**Completeness**: `{tx['transaction_completeness']}`; "
            f"**Missing Stages**: `{tx['missing_stages']}` "
            f"(`{', '.join(tx['evidence_ids'][:4])}`)."
        )

    lines.extend(["", "## 2. Key Findings & Reconstructed Storylines"])
    for sl in report["storyline_summaries"]:
        lines.append(
            f"### {sl['storyline_id']} — Anchor `{sl['anchor_entity']}` "
            f"(tx=`{sl['transaction_id']}`, status=`{sl['completeness_status']}`, "
            f"independent_containers=`{sl['independent_source_container_count']}`, "
            f"independent_edges=`{sl['independent_support_edge_count']}`)"
        )
        for step_str in sl["steps_rendered"]:
            lines.append(f"- {step_str}")
        if sl["evidence_gaps"]:
            lines.append(f"- **Evidence Gaps**: `{sl['evidence_gaps']}`")

    if report["verified_llm_claims"]:
        lines.extend(["", "### Verified LLM Claims (Checked by Deterministic Verifier)"])
        for vc in report["verified_llm_claims"]:
            lines.append(f"- {vc['rendered_text']}")

    lines.extend(["", "## 3. Observed Network & Electrical Impact"])
    lines.append("### 3.1 Confirmed Same-Device State & Measurement Transitions")
    if report["confirmed_device_impacts"]:
        for item in report["confirmed_device_impacts"]:
            lines.append(f"- {item}")
    else:
        lines.append("- No confirmed post-command device state transition was observed.")

    lines.append("")
    lines.append("### 3.2 Candidate Cross-Entity Co-occurring Changes (Unresolved Hypotheses, Not Causal Proof)")
    if report["unresolved_cooccurring_changes"]:
        for item in report["unresolved_cooccurring_changes"]:
            lines.append(f"- {item}")
    else:
        lines.append("- No cross-entity temporal co-occurrences recorded.")

    lines.extend(["", "## 4. Alternative Explanations & Competing Hypotheses"])
    if report["competing_hypotheses"]:
        for comp in report["competing_hypotheses"]:
            lines.append(
                f"- **[{comp['storyline_id']} | {comp['hypothesis_type']} | status=`{comp['status']}`]**: "
                f"{comp['explanation']}"
            )
    else:
        lines.append("- No competing multi-branch hypotheses triggered in this window.")

    lines.extend(["", "## 5. Unresolved Questions, Evidence Gaps & Unattached Observations"])
    if report["evidence_gaps"]:
        for gap in report["evidence_gaps"]:
            lines.append(f"- **Evidence Gap**: `{json.dumps(gap, ensure_ascii=False)}`")
    if report["unattached_observations"]:
        lines.append(f"- **Unattached Observations (`{len(report['unattached_observations'])}` nodes not on a storyline spine)**:")
        for uo in report["unattached_observations"][:10]:
            lines.append(
                f"  - `{uo['fact_id']}` (`{uo['time']:.4f}`, `{uo['modality']}`, `{uo['role']}`): "
                f"`{uo['entity']}` (`{uo['reason']}`) [`{', '.join(uo['evidence_ids'][:2])}`]"
            )
    return "\n".join(lines) + "\n"


def _compact_prompt_payload(
    incident_start: float,
    incident_end: float,
    tx_result: dict,
    event_graph: dict,
    storyline_result: dict,
) -> dict:
    return {
        "incident_start": incident_start,
        "incident_end": incident_end,
        "transactions": [
            {
                "transaction_id": tx["transaction_id"],
                "entity": tx["entity"],
                "ca_ioa": tx["ca_ioa"],
                "type_id": tx["type_id"],
                "commanded_value": tx["commanded_value"],
                "command_acceptance_status": tx["command_acceptance_status"],
                "device_state_change_status": tx["device_state_change_status"],
                "missing_stages": tx["missing_stages"],
            }
            for tx in tx_result["transactions"]
        ],
        "storylines": [
            {
                "storyline_id": sl["storyline_id"],
                "transaction_id": sl["transaction_id"],
                "anchor_entity": sl["anchor_entity"],
                "completeness_status": sl["completeness_status"],
                "spine_fact_ids": sl["spine_fact_ids"],
                "spine_edge_ids": sl["spine_edge_ids"],
                "evidence_gaps": sl["evidence_gaps"],
            }
            for sl in storyline_result["storylines"]
        ],
        "timeline": [
            {
                "timeline_id": n["fact_id"],
                "time": n["time"],
                "role": n["role"],
                "modality": n["modality"],
                "entity": n["entity"],
                "ca_ioa": n.get("ca_ioa"),
                "value": n.get("value"),
                "evidence_ids": n["evidence_ids"][:2],
            }
            for n in event_graph["nodes"][:18]
        ],
        "candidate_relations": [
            {
                "edge_id": e["edge_id"],
                "source_fact_id": e["source_fact_id"],
                "target_fact_id": e["target_fact_id"],
                "source_entity": e["source_entity"],
                "target_entity": e["target_entity"],
                "relation_type": e["relation_type"],
                "claim_level": e["claim_level"],
                "verification_status": e["verification_status"],
            }
            for e in event_graph["edges"]
            if e["relation_category"] != "temporal_cooccurrence"
        ][:12],
    }
