# Paper build and audit notes

**Status: DRAFT pending author approval.** The author block lists PoTing Lu and
Eric Mao (corresponding author) under AvocadoAI, and Shih-Hao Chang under National
Taipei University of Technology. The paper is framed as a post-alert,
event-conditioned measurement study; it does not claim an anomaly-detector
baseline, end-to-end reconstruction, or independent truth verification.
Existing OT anomaly detection is the upstream context. The downstream gap is
evidence-bounded analysis under site data-governance constraints.

- **PDF:** `icit2027_ot_investigation.pdf`, 8 pages, IEEEtran conference format,
  125,860 bytes.
- **Project build:** Tectonic 0.17.0:

  ```sh
  "/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic" \
    --keep-logs --keep-intermediates icit2027_ot_investigation.tex
  ```

  The built-in standalone editor compiler uses guarded fallbacks because its
  single-file sandbox cannot load the separate figures or BibTeX database. The
  project build above includes both figures and the complete bibliography and
  finishes successfully.
- **Layout:** the full project build contains all 8 pages, both figures, and the
  results tables. No overfull boxes, missing glyphs, unresolved references, or
  missing figures are reported. Figure 1 is generated as a deterministic vector
  diagram; Table III remains the main source of underfull-box warnings.
- **Citations:** all 19 rendered references resolve. The paper includes the primary
  papers for PASAD, invariant-based detection, Seq2SeqNN, SIMPLE, and GeCo, and
  uses Sherlock Table 3 as an upstream operating-point benchmark. It also adds
  joint 2025 AI--OT guidance on data residency and on-premises operation and NIST
  SP 800-207 for least-privilege enforcement, while
  retaining direct 2025--2026 work on evidence verification, incident analysis,
  local-LLM forensic reporting, attribution faithfulness, and abstention.
- **Warnings:** underfull `\hbox` warnings and one underfull `\vbox` warning remain.
  There are no overfull-box, missing-citation, or missing-reference warnings.
- **System framing:** an investigation skill is defined as a versioned procedure
  with required inputs, permitted scope/view, output schema, provenance,
  stop/unknown conditions, and review state. Figure 1 separates the prompt/skill
  layer from case-scoped enforcement and links alert scope, evidence lineage,
  claims, dispositions, policy version, and review state in a case trace. The
  supplied course handbook informed this architecture but is not treated as
  experimental evidence.
- **Science:** frozen experiment values were not changed. Interpretation
  distinguishes Sherlock Table 3's upstream detector metrics from downstream
  claim metrics; treats E64/N64/EN32+32 as equal-total-budget configurations;
  and pairs policy-aligned support with Substantive Coverage and withholding recall.
  Skill contracts, authorization, sandboxing, egress control, injection defense,
  and tamper-resistant case tracking are design requirements, not evaluated
  capabilities. Data locality likewise remains unvalidated because the experiment
  uses sanitized public records and a fixed hosted model snapshot.
- **SHA-256:** source
  `8e6e59912b845fe3b946e130199ea69ee1fd3a97d7122e74540474559b0cf75f`;
  bibliography
  `8b2938b6c43a2e188b64efd5928aadf110a2ff910a6849f948f8b692589406f3`;
  Figure 1
  `67d4e7ea5d36113ac6a90118aca173f55ce09da2ad087326cecdd4b1bb6f48a5`;
  Figure 1 generator
  `39c42b2aa7564fe7ee3290e18cdddd6841c8dcd161a49ec6e48e42a9d6e71a6e`;
  PDF
  `ce2c1376871d0764407d65964c1632d76f0b276cf4d788f74aa24118836b113b`.
