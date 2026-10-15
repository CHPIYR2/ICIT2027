# MIRAGE-OT Review Artifacts

- **Stage 1 Complete 28-Window Basic Frozen Experiment (`2981fb0`)**: `review_artifacts/stage1-basic-frozen-20261015/` & `docs/STAGE1_BASIC_FROZEN_EXPERIMENT_RESULTS.md` (all 28 Sherlock v3 `01-Basic` `test` windows, 100% Quality & Lineage Consistency pass rate).
- **Method-Freeze Synthesis outputs (`2981fb0`)**: `review_artifacts/synthesis-method-freeze-20261015/` (per-target first ARP timestamp precedence and bridge RTU IP exact alignment check).
- **Earlier Synthesis reliability outputs (`286f4c2`)**: `review_artifacts/synthesis/` (preserved unchanged).
- **R5 Behavioral Reconstruction outputs (`2083eb7`)**: `review_artifacts/behavioral-r5-20261015/` (preserved unchanged).

# MIRAGE-OT Review Artifacts (`behavioral-r5-20261015`)

This directory contains self-contained, auditable reconstruction outputs for the four Sherlock v3 `01-Basic` no-control-command windows evaluated in the **R5 Behavioral Reconstruction Refinement** round (`runs/etgi/behavioral-r5-20261015/reconstruction/`).

---

## 1. Code Commit, Provenance & Experiment Settings

All artifacts in `review_artifacts/behavioral-r5-20261015/` were produced under a single clean Git commit and identical reconstruction parameters:

| Field | Value |
| --- | --- |
| **Git Branch** | `mirage-ot` |
| **Generating Code Commit (`git_commit`)** | `2083eb76484f21a2db3b2d0c91c7a573fa077421` |
| **Working-Tree Dirty Diff Hash (`git_dirty_diff_sha256`)** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty diff; clean tree) |
| **Reconstruction Code Hash (`code_sha256`)** | `935c4dff083df3c461e9e7370a2875e8d671fa0ff5f2cc3e72dfce6d2289f162` |
| **Evidence Layer Code Hash (`evidence_code_sha256`)** | `032c6977ac0507e9c442b37e4e78455d0ab6d1a21b1efe751a0ccf37242a3b85` |
| **Upstream Raw Dataset** | Sherlock v3 `01-Basic.zip` (MD5 `c482e0dc7e56b063b357d8b03be5cce6`), recording `01-Basic/raw/test/` |
| **Inputs Explicitly Excluded** | Official event labels (`events.json` / `events.jsonl`), attack type, `malicious` flags, `physical.zip` |
| **Execution Mode** | `--no-llm` (`model = "deterministic_renderer"`, `selection_limit = 24`, `num_predict = 512`, `num_ctx = 8192`, `seed = 1`, `background_start = incident_start - 15.0`) |

### Per-Window Experiment Configuration & Database Fingerprints

| Episode ID | `incident_start` | `incident_end` | `background_start` | `config_sha256` | Full Window DB Rows (`evidence.sqlite`) | `db_fingerprint.meta_sha256` |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `ev_564bebaa45f0686cf98d` | `1742922604.1942136` | `1742922784.4018285` | `1742922589.1942136` | `d993265355d3c95b77ceea8acd97964dc6448758cb8309f8ca1e6f75b19a6502` | `17,211` | `e13ac701fd1211cfe9aef3ea3351029703929760bfd04e862d6e489c4938c089` |
| `ev_4e913b93a51e7b3c9e31` | `1742926251.1947885` | `1742926421.521569` | `1742926236.1947885` | `3e45ee738ec842a4e82a9b91457ec740183f3819a63a0107ef629b7935dc2c71` | `17,429` | `9eaca5ce91f11308810dadf8d7e54163e50c092be53bad11357a0ec01a6348a8` |
| `ev_812f8057d7c974d9cf36` | `1742933403.2674494` | `1742933529.526473` | `1742933388.2674494` | `2db9a5cbb48ffd06ab40bc1397ae153012ad90b0cf3e18f3b7836e3caa759032` | `13,532` | `d20ac72e808f6812d0db0c14b131cbf9ee825454062c66f5f9ee9c98cb0d18f4` |
| `ev_cbe1e5bef23346604396` | `1742953785.268002` | `1742953913.4897654` | `1742953770.268002` | `4604403e55d95e0dd69dd4c3d5fb893c747313dae5325af195e8e3f61a6aa1c4` | `13,548` | `259fd1cd1f81673da7402725f75f93a5eda1fa80ec876cc3e3233fd15a7b169e` |

---

## 2. Generation Method & Reproduction Command

Each window was indexed from `data/raw/sherlock/v3/01-Basic.zip` into `runs/etgi/behavioral-20261015/index/<episode_id>/evidence.sqlite` and reconstructed at commit `2083eb76484f21a2db3b2d0c91c7a573fa077421` via:

```bash
.venv/bin/python -m mirage_ot.etgi.cli reconstruct \
  --db runs/etgi/behavioral-20261015/index/<episode_id>/evidence.sqlite \
  --out runs/etgi/behavioral-r5-20261015/reconstruction/<episode_id> \
  --no-llm
```

---

## 3. Scope, Epistemic Boundaries & Important Limitations

1. **Review Subset vs. Complete Raw Evidence (Non-Equivalence Notice)**:
   - These review artifacts **do NOT constitute the complete raw Sherlock v3 capture or the complete indexed SQLite database**.
   - Specifically, raw PCAPs (`switch-n302-pcap-mir2.pcap`, `switch-n318-pcap-mir3.pcap`, etc.), IPAL `.state.gz` archives, and the per-window `evidence.sqlite` files (`13,532` to `17,429` rows per window) are excluded from Git tracking due to size and dataset licensing constraints.
   - `evidence_audit_bundle.json` contains **only the exported lineage subset** of evidence rows cited by `timeline.json` / `event_graph.json` together with their `parent_evidence_id` rows (`1,048` rows for `ev_564bebaa45f0686cf98d`, `854` rows for `ev_4e913b93a51e7b3c9e31`, `631` rows for `ev_812f8057d7c974d9cf36`, and `588` rows for `ev_cbe1e5bef23346604396`), plus the `behavioral_anchor_lineage` verification summary (`192`, `11`, `24`, and `52` checked anchor evidence references respectively, all with `0` missing IDs and `0` row check failures).
2. **Verbatim ID Preservation & Zero Post-Hoc Modification**:
   - Every `evidence_id` (`EV-...`), `fact_id` (`EF...`, `BA...`, `BI...`), `edge_id` (`R...`), `anchor_id` (`A...`), and `storyline_id` (`SL...`) is preserved verbatim without renumbering, filtering, or rewriting.
   - All 68 JSON and Markdown files in `review_artifacts/behavioral-r5-20261015/` are **byte-for-byte identical copies** (identical SHA256 digests) of the original files in `runs/etgi/behavioral-r5-20261015/reconstruction/`.
3. **De-Identification & Sensitive Content Audit**:
   - All `source_ref` and `archive_member` fields generated by the indexer already use archive-relative identifiers (e.g., `01-Basic.zip:01-Basic/raw/test/pcap/switch-n302-pcap-mir2.pcap#t=...`).
   - An automated scan across all 68 files confirmed **zero** occurrences of local absolute filesystem paths (`/Users/...`, `/home/...`, `/tmp/...`), local usernames, API keys, tokens, or passwords. Consequently, **zero redaction edits (`0` bytes changed)** were required.
4. **Epistemic Limitations of the Reconstructed Outputs**:
   - **No grid topology model**: Cross-device links (e.g., between `switch.13`/`switch.14` and bus/line drops) lack topological or protocol linkage evidence and remain `cross_device_temporal_candidate` (`verification_status = "unresolved"`, `causal_status = "not_established"`).
   - **IPAL state rows have no packet lineage**: Time-aligned IPAL rows are typed as `temporal_correspondence` (`common_source_unconfirmed`, `counts_as_independent_source = false`) and never form storyline spine steps.
   - **Unverified observations are quarantined**: Anchors lacking a prior in-window state baseline (`no_prior_state_value_in_window`) or failing post-change persistence (`< 2` post samples or `< 80%` consistent samples) are retained as `unverified_observation` (`behavioral_unverified_observation`) and excluded from supported storyline spines.

---

## 4. Summary of Reconstructed Results Across the Four R5 Windows

| Episode ID | Anchors (Verified / Unverified) | Graph Nodes / Edges | Behavioral Storylines (Supported / Verified Single / Unverified) | Sequential Same-Entity Observations (Gate Failed) | Unresolved Cross-Device Branches | `quality_consistency` / `lineage_consistency` |
| --- | --- | --- | --- | --- | ---: | --- |
| `ev_564bebaa45f0686cf98d` | `32` (`23` / `9`) | `84` / `212` | `27` (`5` / `13` / `9`) | `3` (`R0134` `line.2`, `R0211` `line.2`, `R0212` `line.14`) | `129` | `True` / `True` |
| `ev_4e913b93a51e7b3c9e31` | `4` (`1` / `3`) | `32` / `35` | `4` (`0` / `1` / `3`) | `1` (`R0035` `sgen.0`) | `0` | `True` / `True` |
| `ev_812f8057d7c974d9cf36` | `2` (`2` / `0`) | `26` / `29` | `2` (`0` / `2` / `0`) | `0` | `1` | `True` / `True` |
| `ev_cbe1e5bef23346604396` | `7` (`4` / `3`) | `34` / `33` | `7` (`0` / `4` / `3`) | `0` | `7` | `True` / `True` |

---

## 5. File Inventory, Byte Sizes & SHA256 Checksums

Total across all 68 review artifact files: **`7,465,750` bytes (`7.12` MB)**. Machine-readable checksums are also recorded in `review_artifacts/SHA256SUMS.txt`.

### `ev_564bebaa45f0686cf98d` (`review_artifacts/behavioral-r5-20261015/ev_564bebaa45f0686cf98d/`)

| File | Size (Bytes) | SHA256 |
| --- | ---: | --- |
| `run_manifest.json` | `3,877` | `b52093b462bf05ab0d7676bd370f7872a2a5addd6fdb3e5273e3395a3eb3c73e` |
| `transactions.json` | `536` | `407283f29cd32bf82b6a1d0bb5fb558cdc86127b0686118046b084415e357264` |
| `event_anchors.json` | `112,600` | `1aaec04acfa65280a9d85a1f313a1efc3cbe199d549ca392a08082d1eec987f5` |
| `event_graph.json` | `556,232` | `eeadcfa0f0ee4d7a5cf7c6127d3023821da1747a1f2fae41509699f38362ae7c` |
| `graph.json` | `381,865` | `cd88715206e049f1332c3609bfff1d1137999037c8bba36d4bb0df06d2212f6f` |
| `timeline.json` | `45,478` | `9df37591a563d2cd7675e9b3d86f26512b1445c0e238b473ba180e8eb439991a` |
| `storylines.json` | `607,073` | `3eac0d924a2ecf8d15f31988028c489fa9e2fe2c0f2a6cf913aa9c1f502e8667` |
| `behavioral_storylines.json` | `424,591` | `249551e51bb44717187678af31df5b70301d8d5892ec348e35dd7206eac6dd50` |
| `unresolved_branches.json` | `120,108` | `2abc422288c5de54d282013413f3fe79038f355b7b26b5ce6a946d68b5ca79a9` |
| `lineage.json` | `32,804` | `e03de3059367a2a17f9c53b0e45211e7c690ca9c1e0bff46f24752316a735526` |
| `evidence_audit_bundle.json` | `1,326,888` | `719dca622baed3bfd7e9556463098e6a009b43c7e20aed2a5edea70753ac22c8` |
| `quality_consistency.json` | `21,907` | `3791927d63192323b5d638bc0d24fac3d2047cc34b15a4a9240c3d88d316fa3d` |
| `lineage_consistency.json` | `483` | `b4e0ceb8b0136bff3326ea9fc054dafc9f041e6bd715f16f50f9141f50947c75` |
| `llm_explanation.json` | `20,735` | `734f8bd2657a61885336babf1e4b93e250927d9674ffbe2c19b93beecec80141` |
| `verification.json` | `38` | `8ba8713a58c6ed82045464ddc6a10e9b008d9a1b7b7467306283eb4ba29f36d5` |
| `investigation_report.json` | `183,131` | `35a828ec47edf64c793b6ee90021175468e38e4246e8d7f2b577b45463497875` |
| `investigation_report.md` | `94,099` | `bab27a582461e1f6b16aec019040a58435e081bdbbb31de24e1c189d665ec30e` |
| **Subtotal (`ev_564bebaa45f0686cf98d`)** | **`3,932,445`** | — |

### `ev_4e913b93a51e7b3c9e31` (`review_artifacts/behavioral-r5-20261015/ev_4e913b93a51e7b3c9e31/`)

| File | Size (Bytes) | SHA256 |
| --- | ---: | --- |
| `run_manifest.json` | `3,876` | `f941cf48b29ccd543871c218b30dd49c2fa5e5b99ef8986e1cf5b8da33385c9f` |
| `transactions.json` | `535` | `138420830af741b48d2ad0a5b79a8b378f4bceb8ac86f4dd195410c78c96a363` |
| `event_anchors.json` | `9,967` | `dd9d6170fba26ea8676581ea333f7279b6bb21ec08364ed7dbf0a3153bd1b115` |
| `event_graph.json` | `107,684` | `693c975d777a38c868f196837b0ef7b0d8f61dee8e14c1e60c5615fa9d73461c` |
| `graph.json` | `69,615` | `85ed6dabdb3a99c0e55d87790a90dd89e24d6c5a0826a73485a87ec936e4f156` |
| `timeline.json` | `16,471` | `ababf5db64e9d2a7cdb1898cc76ee2d9738a8142325691d3bd22497e4ec2b90c` |
| `storylines.json` | `43,331` | `7739418a828f92415a6ea72ce73433c4bf0d6d05632b1715392bd411abe2d345` |
| `behavioral_storylines.json` | `16,253` | `90bd46032b088f0faff9d0ab4ed4864c75c6c51a79c643a3a7a7f32c9133637a` |
| `unresolved_branches.json` | `2` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `lineage.json` | `25,143` | `ded648ed9763e4679740f874c5ae3ddc1f32be147e324ce533522efa34e75aea` |
| `evidence_audit_bundle.json` | `986,502` | `e9c62d238303b492960da919abd7c4c7268acb4ee5d6c66b0096ca29a4a50cb5` |
| `quality_consistency.json` | `3,314` | `fd333d3a828bfbb64c1aa81d88643e8da3b9c460f616c2ae8c599b94044eef06` |
| `lineage_consistency.json` | `478` | `b391f0d064a35f98f3b80f3f892be95e654dfc1296beabbab4de0c869f2bc2fe` |
| `llm_explanation.json` | `13,334` | `4b8dc42adaab4de403a3985dabde10a428bfa50f207349c56cc384d5f9fa98e4` |
| `verification.json` | `38` | `8ba8713a58c6ed82045464ddc6a10e9b008d9a1b7b7467306283eb4ba29f36d5` |
| `investigation_report.json` | `30,338` | `a89ae4d5ae7a7bc89037d3e4fa67734100d6b8055f4b05fe219f3c35ee61df5b` |
| `investigation_report.md` | `11,819` | `3c15d756221863ffbc7066a4016b35485452aa1e293ed04a5b47c9860e0ac33b` |
| **Subtotal (`ev_4e913b93a51e7b3c9e31`)** | **`1,338,700`** | — |

### `ev_812f8057d7c974d9cf36` (`review_artifacts/behavioral-r5-20261015/ev_812f8057d7c974d9cf36/`)

| File | Size (Bytes) | SHA256 |
| --- | ---: | --- |
| `run_manifest.json` | `3,876` | `b1e9c69fe6f7696480f2e6fc5a239d7ec90f3d385bca3c2d11682188094a82d2` |
| `transactions.json` | `535` | `4001bb5cd93794eab13d2b66603626e1e10a8fbd4579030540b46cacb085d0c6` |
| `event_anchors.json` | `31,699` | `3fcb78ab4f66fb497ecdf5b3c8d11cd652f34607d7ea3a771ea1c539e9fd3001` |
| `event_graph.json` | `86,752` | `339af3cf06ca15eb8245705c061a550ecf55bc2e9f0d4c9a00602b67edc0b076` |
| `graph.json` | `58,822` | `95119670f7820873b04efe001b8edf1d1855c182c328d9295ba19955ea636c0f` |
| `timeline.json` | `14,518` | `f5fcbb4530de76ca3c12952ebb4e9372dd888da55d27395f32d23c22757ee3a0` |
| `storylines.json` | `37,576` | `c0abe44eb7540cd07af0cb9c9a3cb490aecd61d7cea1b181796747747bc238c0` |
| `behavioral_storylines.json` | `6,793` | `3611f5096557eefde5789cca0f541fb368a28e30e4324547125829e6992a1764` |
| `unresolved_branches.json` | `969` | `bacb67af566ae0a5b7dfcf7fd973fb5323e97bbfd04c7e00dcebd0761a8da367` |
| `lineage.json` | `17,481` | `01fdb0ca3caa35f7df162900e38a139df75f0eaecb5f106d7b119744430a6202` |
| `evidence_audit_bundle.json` | `738,542` | `62ad79d40f05f295308827a94cc152b096c7927433160210949353cf3f8fab1a` |
| `quality_consistency.json` | `1,432` | `a7558884c3bfacfe167ed8c49dd03cd8c72027a1e4d01c523831b16bc96d5f66` |
| `lineage_consistency.json` | `478` | `b039d780fdf92478256575da95b3bef30a03499b93fb80289f1466b7319b7237` |
| `llm_explanation.json` | `12,899` | `fcd23fbfb2f478dd003e21639f6f4e6ccde8bd3ecd4a9b877958f1176738ad8e` |
| `verification.json` | `38` | `8ba8713a58c6ed82045464ddc6a10e9b008d9a1b7b7467306283eb4ba29f36d5` |
| `investigation_report.json` | `24,109` | `21653d63cbb70d765244df202d36de32cb6dbcb7e0c338cc533d5cf67f0494b2` |
| `investigation_report.md` | `11,736` | `164ce1399ef125d56dcb454e112e205afc6a2c646b745bfe9bf1686dee9ba528` |
| **Subtotal (`ev_812f8057d7c974d9cf36`)** | **`1,048,255`** | — |

### `ev_cbe1e5bef23346604396` (`review_artifacts/behavioral-r5-20261015/ev_cbe1e5bef23346604396/`)

| File | Size (Bytes) | SHA256 |
| --- | ---: | --- |
| `run_manifest.json` | `3,874` | `8b5bb34a731141240403cf56cee4eb46dd8260a642499a0c510973b5baa86c4e` |
| `transactions.json` | `535` | `498cedd9510b17582487c0f78a90805a98eb72f0b44e5743c3dc613997fa80ed` |
| `event_anchors.json` | `45,820` | `b45931dfc7a7400743103c44c12c7164e398489849ac8061dedef6d2e7905ab2` |
| `event_graph.json` | `114,234` | `560ede4e415748a75961c644e2c049a1a346e1076e0a59541b99b562b131d0bc` |
| `graph.json` | `70,319` | `a616216beee08d81fc85ff406a1c5caaab80678ae3322b4706f2b5a674e76783` |
| `timeline.json` | `18,835` | `66fe3bf3dece996c57669bbcaf06b76115e0e4d46000c5aea01f65372277e50f` |
| `storylines.json` | `59,605` | `8251e6da387dc15a03e7c224eae674d0eeda13761d6ce6b4ce3b4cb7d4809734` |
| `behavioral_storylines.json` | `34,665` | `f9051d3956c704dded3925919460c3ba522d76ca07e31662c1216e5f8589a573` |
| `unresolved_branches.json` | `6,638` | `c3b766f03f0467dda6414b9722492dc641c97ea206401d8eab0815940c3f7ae0` |
| `lineage.json` | `16,591` | `8c4d41ced60a9dc7d00a78db8ca90e29475bedd47e9e91f15a0897427aec1132` |
| `evidence_audit_bundle.json` | `701,123` | `894bad7a950dcf71e4e596096851dd8558d8a14bf64817d81564b7d1e919b4e4` |
| `quality_consistency.json` | `4,494` | `9deb64994e2bbf72f802d13880019687fae093f65caf9ef3f4a0f621c6af9da6` |
| `lineage_consistency.json` | `478` | `6e95b969e507f0bf01c3a39e0f87699d7ac3d393be349f55df763dde8ca0057a` |
| `llm_explanation.json` | `11,952` | `064a8c0de63f4f152422a1c12751430bbdb03ef1766225da1b2226ac9297ee0c` |
| `verification.json` | `38` | `8ba8713a58c6ed82045464ddc6a10e9b008d9a1b7b7467306283eb4ba29f36d5` |
| `investigation_report.json` | `40,907` | `e9688174896f1f340e32ee36641d34606b78f2da753dd3bbe7f6eed2ae69055b` |
| `investigation_report.md` | `16,242` | `cdaf081f9ae904a993661b5617ddfb73ec573dfffd8653e4047cbab49eeb38b0` |
| **Subtotal (`ev_cbe1e5bef23346604396`)** | **`1,146,350`** | — |
