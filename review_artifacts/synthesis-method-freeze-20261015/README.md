# Incident Synthesis Method-Freeze Review Artifacts (`synthesis-method-freeze-20261015`)

These files are byte-for-byte copies of the Method-Freeze synthesis run (`runs/etgi/synthesis-method-freeze-20261015/reconstruction/`), preserving all prior directories (`review_artifacts/behavioral-r5-20261015/` and `review_artifacts/synthesis/`) untouched.

| Field | Value |
| --- | --- |
| **Generating Commit (`git_commit`)** | `2981fb062b127218a34f23f2ff0292e4ca8cfea7` |
| **Reconstruction Code Hash (`code_sha256`)** | `d43d9867ce847df169e13345e4c3461cd99fd5167292a85cedaaa553d93e5bb3` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Working-Tree Dirty Diff Hash (`git_dirty_diff_sha256`)** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty diff) |
| **Method Freeze Manifest** | `configs/etgi/method_freeze.v1.json` & `docs/METHOD_FREEZE_MANIFEST.md` |

## What Changed Between `286f4c2` (`review_artifacts/synthesis/`) and `2981fb0`

1. **Per-Target First ARP Timestamp Precedence (`anchors.py`, `synthesis.py`)**:
   - `_arp_anchors()` records `target_first_seen` and `target_first_evidence_ids` for each target IP.
   - `_arp_link_precedence()` evaluates each `(arp_anchor, communication_anchor)` pair using the **target RTU's first ARP packet timestamp** (`timestamp_basis = "per_target_first_arp_packet"`), falling back to a weaker window-level co-occurrence claim (`arp_and_iec104_link_temporal_cooccurrence_without_per_target_timestamp`) if per-target timestamps are unavailable.
   - **Impact on `ev_cbe1e5bef23346604396`**:
     - `A001 -> A002` (RTU `172.16.3.10`): first ARP `EV-0e9f6fb66f6907e4` at `1742953786.677999` precedes link change at `1742953792.79` (`dt = +6.112s <= 15s`) $\to$ **Eligible**.
     - `A001 -> A004` (RTU `172.16.3.9`): first ARP `EV-fd36a37175d5af9d` at `1742953786.648633` precedes link change at `1742953800.09818` (`dt = +13.450s <= 15s`) $\to$ **Eligible**.
     - `A001 -> A003` (RTU `172.16.3.20`): first ARP `EV-dd59c3d758762e69` at `1742953831.077105` occurred **after** the link change at `1742953793.37` (`dt = -37.707s`) $\to$ **Rejected (`ineligible_arp_link_pairs`)** and excluded from the `EXP-001` precedence claim (`scope = ['A001', 'A002', 'A004']`, `overlapping_target_rtu_ips = ['172.16.3.10', '172.16.3.9']`).
   - **Impact on `ev_564bebaa45f0686cf98d`**: Byte-identical `incident_synthesis.json`, `investigation_report.json/.md`, `quality_consistency.json`, `lineage_consistency.json`, and `evidence_audit_bundle.json` (12 bundles, 5 cross-RTU bridges).
2. **Bridge RTU IP Exact Alignment Check (`consistency.py`)**:
   - `check_quality_consistency()` verifies that `from_rtu_ip` and `to_rtu_ip` on every `VerifiedElementBridge` match both the underlying event-graph nodes and the referenced RTU bundles (`synthesis_bridge_rtu_ip_mismatch`).

## Files & SHA256 Checksums

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `ev_564bebaa45f0686cf98d/evidence_audit_bundle.json` | `1,326,888` | `719dca622baed3bfd7e9556463098e6a009b43c7e20aed2a5edea70753ac22c8` |
| `ev_564bebaa45f0686cf98d/incident_synthesis.json` | `199,144` | `34974448c2cdca8181c27c6cb39594f4d9c477cb849dac8b0f3cf5b3a8108bad` |
| `ev_564bebaa45f0686cf98d/investigation_report.json` | `391,725` | `5e3dbd5b45f03589c172eaab45e9a0805e1cf9d61736a77759944cfbd64dc91e` |
| `ev_564bebaa45f0686cf98d/investigation_report.md` | `106,101` | `228d3ae66dd32eab4016dcdbbd37e325a06fe7a39cc2497d49ba525354c897e0` |
| `ev_564bebaa45f0686cf98d/lineage_consistency.json` | `483` | `b4e0ceb8b0136bff3326ea9fc054dafc9f041e6bd715f16f50f9141f50947c75` |
| `ev_564bebaa45f0686cf98d/quality_consistency.json` | `22,126` | `bc61ab08f21e5818fc6a2e4edb7e0c181b753dbb235b7abb7e5ef47af32f5ac9` |
| `ev_564bebaa45f0686cf98d/run_manifest.json` | `3,980` | `587dce9947e7bee344b4e6d989c10f7e7444ca1ebd6e4e925ea1d8d5fb2c1ebb` |
| `ev_cbe1e5bef23346604396/evidence_audit_bundle.json` | `702,157` | `96209578eaa965f7c3a309a08d5f31cb666f848000430f6918d94b4f944354f3` |
| `ev_cbe1e5bef23346604396/incident_synthesis.json` | `31,540` | `41f8cca9671a46afba6ca18fe3e066adbecf434e739847234a773421282beb6f` |
| `ev_cbe1e5bef23346604396/investigation_report.json` | `74,135` | `91cbb1c0447bbaa82485955daeada10a52933b62313f7e1178ec007d9fb68bbd` |
| `ev_cbe1e5bef23346604396/investigation_report.md` | `21,807` | `50a0d2f57796534947eea5345b178af3f4c88a990618418eb4c798d3bafe4ae7` |
| `ev_cbe1e5bef23346604396/lineage_consistency.json` | `478` | `016a709b231bad81b5f5f2deb944170b372a3b0e0440b4f061ebc6de23b9e52a` |
| `ev_cbe1e5bef23346604396/quality_consistency.json` | `4,713` | `9be18eca7f60f40a0b5c0babbb4023f8b8ae4359508a90a61813c08ec5f11f89` |
| `ev_cbe1e5bef23346604396/run_manifest.json` | `3,977` | `d4dc8d7df45465a06411fc2ce783f31d41121dbe2ddd6f2a94373380ec398943` |
