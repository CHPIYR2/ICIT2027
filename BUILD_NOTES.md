# Paper build and audit notes

**Status: DRAFT.** Author name, affiliation, location, and email remain placeholders; do not submit until the author block is completed.

- **PDF:** `icit2027_ot_investigation.pdf`, 5 pages, IEEEtran conference format, 128,490 bytes.
- **Build:** successfully rebuilt with Tectonic. The standalone editor compiler could not resolve the separate `figures/*.pdf` assets; the project build includes them.
- **Layout:** Table II appears before Results. Table III and Figure 2 appear within Results and before Discussion. Conclusion precedes References, which are the final paper content. The inapplicable acknowledgment placeholder was removed.
- **Citations:** all 10 cited BibTeX entries resolve. The primary Sherlock citation is the CODASPY 2025 publication (DOI `10.1145/3714393.3726006`); the separate v3 Zenodo artifact remains cited (DOI `10.5281/zenodo.18467070`). The review author is spelled Hayretdin Bahşi.
- **Warnings:** three underfull `\hbox` warnings, one underfull `\vbox` warning, and a `Text page 3 contains only floats` warning remain; visual inspection confirms the corresponding PDF page contains text and tables. No overfull boxes or unresolved citation/reference warnings. IEEEtran font-shape substitutions are emitted by the XeTeX toolchain. No font size was reduced to force float placement.
- **Science:** frozen experiment values, denominators, NA semantics, and interpretations were not changed.
