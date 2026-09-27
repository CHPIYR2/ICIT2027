# Investigation Protocol v1 — matching candidate

Version: matching-v1-candidate-20260925. Non-numeric rules below are the final
candidate under the current author direction. Numeric tolerances require author
approval. The protocol is not frozen and this document implements no evaluator.

## Exact gates

Before considering a numerical error bound, require the same event, authorized
evidence/export version, allowed view, actual retrieval snapshot and proposition
strength. The following match exactly: evidence ID and reference role; opaque
asset ID; channel ID; claim type; command ASDU type and COT; boolean/state value;
unit; temporal relation, direction and scope. Null is never a wildcard. A p/m/a
reference cannot substitute for an e reference or static meta reference. Existence
in the full universe does not establish availability in production retrieval.

Claim type is literal exact equality. Fact-key deduplication is a separate step:
reported_change and electrical_change describing one ordered pair/quantity cannot
earn two gold credits, but a matching key does not waive a type mismatch. No new
type normalization is silently introduced. The eight reviewed electrical_change
facts remain unchanged. Existing B0 emits reported_change for numerical pairs;
under this strict rule those labels differ. Before final execution the author must
accept literal matching or separately authorize/version a uniform representation
adapter. An adapter must never rewrite the frozen human annotations in place.

Require one complete approved alternative minimal support set for cited complete
support. Each set is AND; alternatives are OR. Verify the entire proposition and
each reference's role, not only a nonempty ID intersection. For optional-citation
B1/B2, human evidence checks may establish content support from the actual bundle;
they do not add citations or earn citation-validity credit on the system's behalf.

Exact referenced evidence is mandatory for accepting an explicitly cited claim.
For an uncited proposition, a reviewer must uniquely resolve its typed identity
within the bundle. Ambiguous identification is insufficient. Additional true
facts outside the salient gold set may count as supported precision claims after
independent review; they do not expand frozen recall denominators.

## Numerical values and changes — approval pending

Ground truth is the finite numeric value in the cited approved E observation, or
the result of the frozen derived formula from its exact ordered pair. Recompute
the reference; rounded human prose is a readable rendering, not a replacement
reference. Preserve signed difference = after − before; percent change =
100 × (after − before) / abs(before). Zero baseline makes percent unavailable.
Do not swap difference and percent, infer unit conversions, drop quality flags,
or use initial/configuration values. Booleans compare exactly and never as 0/1
floating values. Nonfinite numbers fail.

Proposed acceptance formula, after all exact gates:

`abs(predicted − reference) <= max(atol[unit, quantity], rtol[unit, quantity] * abs(reference))`

The numeric token and approved binary value should be compared with exact rational
or sufficient decimal precision; avoid widening a tolerance to hide binary64
boundary noise. Reference zero requires predicted zero in the recommended profile.
There is no tolerance for evidence identity, unit, sign/direction of an asserted
increase/decrease, boolean transition or capture ordering.

Recommended **A: typed numeric fidelity**: absolute tolerance **0**, relative
tolerance **5e-8**, for reported values and signed changes in AMPERE, PER_UNIT,
WATT and VAR, and for derived percent in percentage points. This explicitly
requires at least eight significant digits or round-trip numeric output; reference
zero is exact. The relative bound follows half a decimal unit at eight significant
digits and covers the empirically tested formatting error (<5e-8). A zero absolute
floor preserves the pilot's tiny nonzero WATT/VAR values instead of erasing them.
This is a proposed serialization rule, not a claim about physical accuracy.

Alternative **B: six-decimal compatibility**: absolute tolerance **5e-7** in each
of those output units (percentage points for percent), relative tolerance **5e-8**.
The absolute bound is half a unit in the sixth decimal place, matching some
reviewed prose renderings. It can treat small distinct values as equivalent,
including zero versus tiny nonzero values if the sign/zero gate is relaxed; it is
therefore not recommended for typed numeric evaluation. If approved, explicitly
retain the zero/sign gate and require significant-digit rendering near zero.
Neither profile is active until approved; no other unit receives a guessed bound.

Percentages with tiny nonzero denominators can be enormous. The approved formula
still defines the number; do not introduce an undocumented denominator floor or
clip it. Report denominator/value and human interpretability separately. These
pilot facts do not require percent-positive gold; a large computed percent alone
does not establish security relevance.

Duration/delta numeric rendering proposal: `atol = 5e-7 SECOND`, `rtol = 0`, only
for the displayed difference of exact referenced capture timestamps (six decimals).
Ordering itself uses exact stored timestamps: earlier < later, or exact equality.
Never round timestamps to manufacture simultaneity or tolerate reversed order.
This duration bound is also pending author approval.

## Relationships and text

Mapped command requires m+a+control M with matching ASDU/COT/time and exact asset
and control point. Same-asset N/E time relation additionally requires valid E and
its channel M; both opaque assets agree. Episode-only order does not need an asset
claim and cannot imply one. Shared packet ancestry must be disclosed when relevant;
it is not independent corroboration. Capture order does not establish action time.

Use exact typed identity and reviewed fact keys to propose matches, followed by all
support, payload and scope checks. One gold fact earns at most one recall credit.
Only semantically identical full propositions may be deduplicated for precision;
a correct and an incorrect value sharing a key are distinct assertions. Preserve
all raw duplicates and contradictory variants for audit. Human-authorized alternate
support sets can support one gold fact; the key alone cannot invent equivalence.

Human review of all raw and final free text is required for stronger interpretation,
including overclaims placed under an innocuous claim type. Natural-language
similarity, embeddings and edit distance are not correctness metrics. A supported
typed payload does not excuse unsupported execution, causation, intent, compromise,
attribution or safe-from-absence text. A qualified sentence is assessed according
to the actual weaker assertion retained, not merely the presence of a hedge word.

All evaluation decisions use a predeclared rubric independently of future verifier
statuses. The gold method is single-reviewer gold; no independent dual annotation,
adjudication or inter-annotator agreement has occurred. Changes informed by final
evaluation gold/results require a new exploratory protocol version.
