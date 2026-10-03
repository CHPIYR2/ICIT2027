# 6. Results

All reported means are event-level macro averages over the 32 final evaluation events unless a metric is undefined. Metrics are first computed per repetition and then averaged within event according to the frozen missing-data rules. Paired contrasts use complete event pairs. Confidence intervals are 95% percentile intervals from 2,000 scenario-stratified bootstrap resamples with seed 20270922. We describe a paired difference as detected only when its interval excludes zero. D0 is retained as a deterministic descriptive reference and is excluded from the primary RQ1–RQ3 comparisons.

## 6.1 RQ1 — Contribution of Electrical and Network Evidence

Table 4 compares citation-required generation under the electrical/process-only (G1-E), network-only (G1-N), and combined electrical-plus-network (G1-EN) views.

Evidence Completeness is 0.0000 for all three conditions, using the same full-EN gold denominator. View-Conditional Completeness is also 0.0000 in all three views. Consequently, neither EN−E nor EN−N shows any improvement in exact gold-fact reconstruction under the frozen matching criterion.

The remaining RQ1 metrics distinguish evidence availability, retrieval, investigative coverage, and evidential support. Retrieval Recall is 0.1111 for G1-E, 0.3500 for G1-N, and 0.2188 for G1-EN. Relative to G1-E, the combined view improves Retrieval Recall by 0.1076 [0.0920, 0.1207]. Relative to G1-N, however, the combined view is lower by 0.1313 [0.0714, 0.1938] in magnitude, reported as EN−N = -0.1313 [-0.1938, -0.0714].

Q1–Q6 Coverage is 0.7691 for G1-E, 0.5972 for G1-N, and 0.7760 for G1-EN. G1-EN exceeds G1-N by 0.1788 [0.0885, 0.2674], while the EN−E difference of 0.0069 [-0.0686, 0.0747] includes zero.

Citation Precision is high in all three conditions: 0.9901 for G1-E, 0.9589 for G1-N, and 0.9949 for G1-EN. The EN−N difference is 0.0360 [0.0186, 0.0565], whereas EN−E is 0.0048 [-0.0048, 0.0192].

The largest RQ1 separation occurs in Complete-Support Rate. G1-E achieves 0.7500, G1-N 0.7406, and G1-EN 0.9261. The combined view exceeds G1-E by 0.1761 [0.1449, 0.2030] and G1-N by 0.1856 [0.1480, 0.2208].

These results do not support the claim that combined evidence improves exact incident reconstruction. They instead show that the combined view yields substantially stronger complete evidential support and higher substantive coverage than the network-only condition, while network-only evidence achieves the highest retrieval recall.

### Table 4. RQ1 — Evidence-view investigation results

| Metric                        |   G1-E |   G1-N |  G1-EN |            EN−E [95% CI] |              EN−N [95% CI] |
| ----------------------------- | -----: | -----: | -----: | -----------------------: | -------------------------: |
| Evidence Completeness         | 0.0000 | 0.0000 | 0.0000 |  0.0000 [0.0000, 0.0000] |    0.0000 [0.0000, 0.0000] |
| View-Conditional Completeness | 0.0000 | 0.0000 | 0.0000 |  0.0000 [0.0000, 0.0000] |    0.0000 [0.0000, 0.0000] |
| Retrieval Recall              | 0.1111 | 0.3500 | 0.2188 |  0.1076 [0.0920, 0.1207] | -0.1313 [-0.1938, -0.0714] |
| Q1–Q6 Coverage                | 0.7691 | 0.5972 | 0.7760 | 0.0069 [-0.0686, 0.0747] |    0.1788 [0.0885, 0.2674] |
| Citation Precision            | 0.9901 | 0.9589 | 0.9949 | 0.0048 [-0.0048, 0.0192] |    0.0360 [0.0186, 0.0565] |
| Complete-Support Rate         | 0.7500 | 0.7406 | 0.9261 |  0.1761 [0.1449, 0.2030] |    0.1856 [0.1480, 0.2208] |

All Table 4 contrasts contain 32 paired events.

### Evidence-Completeness Funnel

The RQ1 funnel further separates view supportability, retrieval, and reconstruction. The values below are event-level macro-equivalent mean fact counts; fractional values therefore represent averages across events rather than fractional individual facts.

| View | Full gold | Supportable in view | Complete support retrieved | Reconstructed |
| ---- | --------: | ------------------: | -------------------------: | ------------: |
| E    |    14.000 |               9.000 |                      1.000 |         0.000 |
| N    |    14.000 |               3.500 |                      1.000 |         0.000 |
| EN   |    14.000 |              14.000 |                      3.125 |         0.000 |

The combined view makes the full gold set supportable and retrieves more complete support sets than either single-source view. Nevertheless, no condition reconstructs a frozen gold fact. The observed failure therefore occurs after relevant evidence is available and, in a subset of cases, after its complete support set has already been retrieved.

## 6.2 RQ2 — Reliability of Evidence-Grounded Generation

Table 5 compares citation-optional EN generation (G0) with citation-required EN generation (G1-EN).

Citation Precision is 0.9907 for G0 and 0.9949 for G1-EN. The paired difference is 0.0042 [-0.0027, 0.0121], which includes zero.

Complete-Support Rate increases from 0.8723 to 0.9261. The paired increase of 0.0539 [0.0287, 0.0794] excludes zero and is the clearest observed effect of citation-required generation.

Q1–Q6 Coverage changes from 0.7465 to 0.7760, with a paired difference of 0.0295 [-0.0313, 0.0903]. Evidence Completeness remains 0.0000 in both conditions.

Numerical Consistency and Asset Consistency are 1.0000 in both conditions on all 32 defined events. Temporal Consistency is also 1.0000 where defined; 29 events are defined in each condition, with 27 complete paired events.

Unsupported Security-Claim Rate is 0.0000 in both conditions where the denominator is defined. However, only 7 events are jointly defined for the paired comparison. G0 has 13 defined events and 19 NA events, while G1-EN has 15 defined and 17 NA. The remaining events contain no security-sensitive substantive assertion and are therefore NA rather than zero.

The RQ2 result is consequently narrow: requiring citations improves complete evidential support of substantive claims, but the evaluation does not establish changes in exact reconstruction, substantive coverage, citation precision, or unsupported security-claim behavior.

### Table 5. RQ2 — Citation-optional versus citation-required EN generation

| Metric                          |     G0 |  G1-EN |           EN−G0 [95% CI] | Paired / omitted |
| ------------------------------- | -----: | -----: | -----------------------: | ---------------: |
| Citation Precision              | 0.9907 | 0.9949 | 0.0042 [-0.0027, 0.0121] |           32 / 0 |
| Complete-Support Rate           | 0.8723 | 0.9261 |  0.0539 [0.0287, 0.0794] |           32 / 0 |
| Unsupported Security-Claim Rate | 0.0000 | 0.0000 |  0.0000 [0.0000, 0.0000] |           7 / 25 |
| Evidence Completeness           | 0.0000 | 0.0000 |  0.0000 [0.0000, 0.0000] |           32 / 0 |
| Q1–Q6 Coverage                  | 0.7465 | 0.7760 | 0.0295 [-0.0313, 0.0903] |           32 / 0 |
| Numerical Consistency           | 1.0000 | 1.0000 |  0.0000 [0.0000, 0.0000] |           32 / 0 |
| Asset Consistency               | 1.0000 | 1.0000 |  0.0000 [0.0000, 0.0000] |           32 / 0 |
| Temporal Consistency            | 1.0000 | 1.0000 |  0.0000 [0.0000, 0.0000] |           27 / 5 |

USCR has 13 defined / 19 NA events in G0 and 15 defined / 17 NA events in G1-EN. Temporal Consistency has 29 defined events in each condition.

## 6.3 RQ3 — Effect of Deterministic Verification

Table 6 compares raw G1-EN output with its exact V1-EN verification replay.

Citation Precision increases from 0.9949 to 1.0000, with V1−G1 = 0.0051 [0.0015, 0.0092]. Complete-Support Rate increases from 0.9261 to 1.0000, with a paired increase of 0.0739 [0.0504, 0.0970].

These gains are accompanied by a substantial reduction in substantive investigation coverage. Q1–Q6 Coverage decreases from 0.7760 to 0.5278. The paired difference is -0.2483 [-0.2934, -0.1979].

Evidence Completeness remains 0.0000 before and after verification. Numerical and Asset Consistency remain 1.0000. Temporal Consistency is 1.0000 for both conditions among the 26 events for which a paired comparison is defined.

USCR cannot be compared after verification. Raw G1-EN has USCR = 0.0000 on 15 defined events, but V1-EN publishes no security-sensitive substantive assertions. Its denominator is therefore zero on all 32 events and USCR is NA, not zero.

Withholding metrics are evaluated only for the verified publication layer. Required Withholding Recall is 0.3344 across 32 defined V1 events. Withholding Precision is 1.0000 on 27 defined events, with 5 events NA because no explicit withholding action enters the denominator.

These results show a support–coverage trade-off. The verifier produces a narrower published report in which every scored substantive claim has correct citations and complete cited support, but it removes or withholds enough content to reduce substantive coverage by approximately 0.25. Explicit withholding is correct when present, but only about one-third of required withholding opportunities are explicitly represented.

### Table 6. RQ3 — Exact replay before and after deterministic verification

| Metric                          |  G1-EN |  V1-EN |             V1−G1 [95% CI] | Paired / omitted |
| ------------------------------- | -----: | -----: | -------------------------: | ---------------: |
| Unsupported Security-Claim Rate | 0.0000 |     NA |                         NA |           0 / 32 |
| Evidence Completeness           | 0.0000 | 0.0000 |    0.0000 [0.0000, 0.0000] |           32 / 0 |
| Q1–Q6 Coverage                  | 0.7760 | 0.5278 | -0.2483 [-0.2934, -0.1979] |           32 / 0 |
| Citation Precision              | 0.9949 | 1.0000 |    0.0051 [0.0015, 0.0092] |           32 / 0 |
| Complete-Support Rate           | 0.9261 | 1.0000 |    0.0739 [0.0504, 0.0970] |           32 / 0 |
| Numerical Consistency           | 1.0000 | 1.0000 |    0.0000 [0.0000, 0.0000] |           32 / 0 |
| Asset Consistency               | 1.0000 | 1.0000 |    0.0000 [0.0000, 0.0000] |           32 / 0 |
| Temporal Consistency            | 1.0000 | 1.0000 |    0.0000 [0.0000, 0.0000] |           26 / 6 |
| Required Withholding Recall     |      — | 0.3344 |                          — |                — |
| Withholding Precision           |      — | 1.0000 |                          — |                — |

Raw G1-EN USCR is defined on 15 events and NA on 17; V1-EN USCR is NA on all 32 events. Temporal Consistency is defined on 29 G1-EN events and 26 V1-EN events. V1 Withholding Precision is defined on 27 events.

## 6.4 Denominators, Opportunities, and Missingness

Table 7 summarizes the principal opportunity and denominator counts needed to interpret Tables 4–6.

Each generative condition contains 96 planned repetitions (32 events × 3 repetitions). G0, G1-N, G1-EN, and V1-EN have 96 valid positions. G1-E has 93 valid deliveries because three repetitions terminate as provider-incomplete. The incomplete repetitions are treated as repetition-level NA. Since the other repetitions for each affected event remain valid, all 32 events remain defined for the fixed-denominator RQ1 metrics.

The number of security-sensitive assertions varies substantially by condition, which explains the amount of USCR missingness. V1-EN publishes no security-sensitive substantive assertions and therefore has no defined USCR event.

G1-N contains no numerical assertions, so Numerical Consistency is structurally NA for that condition. Withholding Precision is also claim-conditioned and is defined only when explicit qualification or withholding actions are present.

### Table 7. Evaluation opportunity and denominator counts

| Quantity                             |   G0 | G1-E | G1-N | G1-EN | V1-EN |
| ------------------------------------ | ---: | ---: | ---: | ----: | ----: |
| Planned runs                         |   96 |   96 |   96 |    96 |    96 |
| Valid delivery                       |   96 |   93 |   96 |    96 |    96 |
| Invalid delivery                     |    0 |    3 |    0 |     0 |     0 |
| Security-sensitive assertions        |   18 |   47 |   33 |    20 |     0 |
| Defined USCR denominators (rep.)     |   18 |   47 |   33 |    20 |     0 |
| Defined USCR events                  |   13 |   31 |   21 |    15 |     0 |
| USCR event NA                        |   19 |    1 |   11 |    17 |    32 |
| Citation pairs                       | 2336 | 1629 | 1864 |  2757 |  2075 |
| Numerical assertions                 |  528 |  332 |    0 |   478 |   475 |
| Defined numerical events             |   32 |   32 |    0 |    32 |    32 |
| Asset assertions                     |  737 |  513 |  132 |   702 |   549 |
| Temporal assertions                  |   78 |   90 |   93 |    85 |    66 |
| Required withholding opportunities   |  864 |  836 |  864 |   864 |   864 |
| Explicit qualify/withhold actions    |  451 |  542 |  510 |   487 |   291 |
| Defined withholding-precision events |   30 |   32 |   31 |    29 |    27 |

The three provider-incomplete G1-E positions are individual repetitions only; no event is removed from the primary RQ1 event-level analysis.

## 6.5 Coverage and Unsupported Security Claims

Figure 2 summarizes event-level Q1–Q6 Coverage against Unsupported Security-Claim Rate for all five research conditions.

Mean Coverage is 0.7465 for G0, 0.7691 for G1-E, 0.5972 for G1-N, 0.7760 for G1-EN, and 0.5278 for V1-EN. Mean USCR among events for which the metric is defined is 0.0000 in G0, G1-E, G1-N, and G1-EN. V1-EN has no defined USCR events because no security-sensitive substantive assertions are published.

Across the 160 event-condition positions represented in the figure source data, 80 USCR coordinates are undefined. These positions must not be plotted at USCR = 0. In particular, all 32 V1-EN positions are NA on the USCR axis.

**Figure 2.** Event-level Q1–Q6 Coverage versus Unsupported Security-Claim Rate for G0, G1-E, G1-N, G1-EN, and V1-EN. Event-condition positions with a zero USCR denominator are omitted from the vertical coordinate rather than plotted at zero.

## 6.6 Summary of Findings

Three findings answer the research questions.

**RQ1:** Combined electrical/process and network evidence does not improve exact gold-fact reconstruction under the frozen matching criterion. It does, however, provide substantially higher Complete-Support Rate than either single-source view and higher substantive coverage than the network-only condition. Network-only evidence retains the highest Retrieval Recall.

**RQ2:** Citation-required generation improves Complete-Support Rate relative to citation-optional generation. The evaluation does not establish corresponding changes in Citation Precision, Coverage, exact reconstruction, or USCR.

**RQ3:** Deterministic verification improves the evidential support of the published claim set, reaching 1.0000 Citation Precision and Complete-Support Rate, but reduces Q1–Q6 Coverage from 0.7760 to 0.5278. Explicit withholding is precise when produced, but Required Withholding Recall remains 0.3344.

Taken together, the results show that evidence availability, retrieval, supported generation, exact reconstruction, and verified publication behave as distinct stages of the investigation pipeline.
