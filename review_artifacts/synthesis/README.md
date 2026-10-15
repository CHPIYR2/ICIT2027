# Incident Synthesis review artifacts

These files are byte-for-byte copies of the synthesis reliability run. They are not a new reconstruction and they are not the raw Sherlock capture.

| Field | Value |
| --- | --- |
| Generating commit | `286f4c2341234a244538048644be5112e42de8a1` |
| `code_sha256` | `74369454c41f...` (full value is in each `run_manifest.json`) |
| `git_dirty_diff_sha256` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty diff) |
| Source run | `runs/etgi/synthesis-reliability-20261015/reconstruction/` |
| Earlier synthesis run | `runs/etgi/synthesis-20261015/` is unchanged |

## What changed in this run

`synthesis_version` is `1.1`.

- A verified element bridge requires two bundles, two RTU addresses, and an edge that passed the behavioral consistency gate. Same-RTU supported relations are listed separately and are not cross-RTU support.
- The consistency checker compares each bridge with its bundle, anchor, fact and edge endpoints.
- An ARP-before-link explanation is emitted only when the ARP target includes that RTU, the ARP anchor starts no later than the link anchor, and the gap is at most 15 seconds.
- The source ledger counts IEC-104 ASDU, TCP link, ARP and composite containers separately.

## Results that survived the stricter rule

| Window | Bundles | Cross-RTU bridges | Container split | Precedence explanation |
| --- | ---: | ---: | --- | --- |
| `ev_564bebaa45f0686cf98d` | 12 | 5 (`line.0`, `line.1`, `line.3`, `line.4`, `line.12`, each with two RTUs) | 12 IEC-104 ASDU | not applicable |
| `ev_cbe1e5bef23346604396` | 4 | 0 | 3 TCP link, 1 ARP | eligible: ARP from `172.16.3.28` targets `.9`, `.10` and `.20` before those links change, within 15 s |

`quality_consistency` and `lineage_consistency` are both true. Evidence, fact, edge, anchor and storyline ids are the originals.

## Limits

`evidence_audit_bundle.json` is the cited-lineage subset, not the full `evidence.sqlite` and not the PCAP. No local paths, credentials or dataset archives are in this directory. Checksums: `SHA256SUMS.txt`.

## Files

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `ev_564bebaa45f0686cf98d/evidence_audit_bundle.json` | 1,326,888 | `719dca622baed3bfd7e9556463098e6a009b43c7e20aed2a5edea70753ac22c8` |
| `ev_564bebaa45f0686cf98d/incident_synthesis.json` | 199,144 | `34974448c2cdca8181c27c6cb39594f4d9c477cb849dac8b0f3cf5b3a8108bad` |
| `ev_564bebaa45f0686cf98d/investigation_report.json` | 391,725 | `5e3dbd5b45f03589c172eaab45e9a0805e1cf9d61736a77759944cfbd64dc91e` |
| `ev_564bebaa45f0686cf98d/investigation_report.md` | 106,101 | `228d3ae66dd32eab4016dcdbbd37e325a06fe7a39cc2497d49ba525354c897e0` |
| `ev_564bebaa45f0686cf98d/lineage_consistency.json` | 483 | `b4e0ceb8b0136bff3326ea9fc054dafc9f041e6bd715f16f50f9141f50947c75` |
| `ev_564bebaa45f0686cf98d/quality_consistency.json` | 22,126 | `bc61ab08f21e5818fc6a2e4edb7e0c181b753dbb235b7abb7e5ef47af32f5ac9` |
| `ev_564bebaa45f0686cf98d/run_manifest.json` | 3,980 | `d93043e66fd7c28388c7f9a1f58453dcdf17e4af4a827192242d54531e4b8fbf` |
| `ev_cbe1e5bef23346604396/evidence_audit_bundle.json` | 701,123 | `894bad7a950dcf71e4e596096851dd8558d8a14bf64817d81564b7d1e919b4e4` |
| `ev_cbe1e5bef23346604396/incident_synthesis.json` | 30,171 | `a61861ece64ea50eb7e62a09b9e1c80b4220dd2fa6479e2f12408650c5e63383` |
| `ev_cbe1e5bef23346604396/investigation_report.json` | 72,712 | `981b141bda6a86b77e7cf6eefeb817928180e319a490a4183450c3d8b9ef2214` |
| `ev_cbe1e5bef23346604396/investigation_report.md` | 21,673 | `67bf245bb20b2de846c3ec06d20f5133b5a31349a1dbe00de51c166ba81b36e6` |
| `ev_cbe1e5bef23346604396/lineage_consistency.json` | 478 | `6e95b969e507f0bf01c3a39e0f87699d7ac3d393be349f55df763dde8ca0057a` |
| `ev_cbe1e5bef23346604396/quality_consistency.json` | 4,713 | `9be18eca7f60f40a0b5c0babbb4023f8b8ae4359508a90a61813c08ec5f11f89` |
| `ev_cbe1e5bef23346604396/run_manifest.json` | 3,977 | `9ba4b41e8d0eb655b0ecdf8591b8b8a16db3bc27ff92987f0f80cbc5b8428ae1` |

Total: 2,885,294 bytes.
