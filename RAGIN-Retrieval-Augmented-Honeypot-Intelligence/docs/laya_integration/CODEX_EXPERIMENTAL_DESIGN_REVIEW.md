# Independent experimental-design review: frozen 120-case RAGIN set

Role G · 2026-10-13 · Design audit, without model outcomes or rater labels.

## Verdict and scope

The permitted packet contains exactly **120 distinct case_id values** and no exact or whitespace-normalized duplicate evidence strings. This establishes record-level uniqueness, not 120 independent sessions or representative sampling. The permitted documents support a blinded three-rater workflow, but do not establish source allocation, independent sampling units, numerical acceptance criteria, or the detailed statistical analysis plan. **No critical integrity failure is proven by this audit.** These limitations do not justify changing the frozen set, threshold, taxonomy, or analysis rules. They limit the claims that this review can support.

Only these scientific inputs were read:

- `results/laya_research/blind_annotation_confirmatory.json`, for structure and duplicate comparisons only (hereafter **B**).
- `results/laya_research/annotation_manifest_v2.json` (hereafter **M**).
- `docs/laya_integration/INDEPENDENT_LABELING_PROTOCOL.md` (hereafter **P**).

Other documentation filenames were listed to identify permitted material; no other document contents were opened. No frozen predictions, preregistration JSON, private subset/source manifest, rater labels, existing AI-rater outputs, or red-team outputs were accessed. The label directory was not listed or checked, so its current emptiness is not independently certified. No inference, services, paid APIs, manuscript changes, or frozen-artifact changes were performed. No case was labeled. AI labels are exploratory and never human ground truth.

The packet's physical identifier field is `id`; this review uses **case_id** exclusively as the conceptual identifier and maps that field to case_id in structural checks. No identifiers were generated and no packet fields were rewritten. Context strings were not interpreted as provenance or as session identifiers.

The execution framework additionally requires the command/evidence record at `.omo/evidence/ROLE_G_EXPERIMENTAL_DESIGN_REVIEW_20261013.json`. It contains audit observations, not labels or model outcomes; this is the sole additional output beyond this review.

## Directly verified structure and documentary boundaries

| Property | Direct observation | Interpretation limit |
|---|---|---|
| Packet size and identifiers | 120 records; 120 unique nonempty string case_id values | Unique case_id does not establish independent origin |
| Record fields | Every record has exactly the identifier, evidence, and context fields; evidence/context are strings | No separate prediction, confidence, or provenance field; embedded-text leakage was not audited |
| Duplicates | Zero duplicate groups for exact evidence, exact evidence/context pairs, whitespace-normalized evidence, or normalized pairs | No semantic, template, session, or cross-split deduplication is established |
| Evidence length | Unicode character counts: minimum 2, median 52, maximum 1,221; zero empty strings | Length is not a judgment of attack behavior or evidence sufficiency |
| Context length | Minimum 61, median 64, maximum 103; zero empty strings; 10 distinct strings | Reused context may be generic; it does not prove ten sessions or dependence |
| Taxonomy/projection | Nine categories; every category has a projection: one benign, seven malicious, one excluded | These are category counts, not observed class frequencies |
| Manifest binding | M's `packet` value names the broader v2 packet, not B | M alone cannot attest to the frozen subset's membership or selection; this is not proof of a wrong join |

Sources: B, all 120 records and their field structure; M:4–5, 8–28. Input SHA-256 digests and exact check output are retained in the evidence record. Digests establish the versions inspected, not an earlier freeze date or provenance chain.

## Selection, spectrum, prevalence, and imbalance

P:18–34 discloses three candidate source families: historical controlled Cowrie sessions, real administration-style transcripts, and existing SSH session transcripts. Neither P nor M supplies the numbers selected from each family, their sampling fractions, inclusion probabilities, collection windows, or the count of independent sessions in the 120. **The frozen set's numerical source distribution is therefore unavailable within the inputs inspected.** No equal allocation or source-derived class balance is assumed. The private manifest was not accessed to fill this gap.

The design risks convenience-selection bias: an assembled candidate pool need not represent the traffic on which a deployed detector would operate. Source choice can also confound task difficulty with class if administration-like and attack-like material originate from different collection processes. P:241–246 explicitly acknowledges shallow prompts, varying context depth, and that provenance is not ground truth. These are documented limitations, not measured source-specific error rates. A knowledge query, an isolated command, and an executed multi-step session test different constructs. Performance on their mixture cannot by itself establish performance on live malicious sessions.

True positive prevalence and category imbalance are unknown without independent labels. A seven-to-one mapping of positive versus negative category names is not a seven-to-one case ratio. Overall accuracy can conceal failure on a rare class. Precision and negative predictive value depend on deployment prevalence; sensitivity and specificity may also change with the evidence spectrum. Neither operational prevalence nor transported predictive value can be inferred here.

**Future v2:** state the target population and unit of evaluation; sample independent sessions prospectively or with a declared sampling frame; disclose aggregate source counts and context-depth strata without revealing them to raters; specify selection before scoring. Include legitimate privileged administration and realistic ambiguous behavior to test construct boundaries. Prespecify per-class denominators, sensitivity/specificity, balanced accuracy, and source-stratified descriptive results with uncertainty. Report precision at the sampled prevalence and label any external-prevalence standardization as assumption-dependent. Keep small strata descriptive rather than claiming source-specific superiority.

## Duplication, pseudo-replication, and session dependence

Zero exact and whitespace-normalized duplicates is useful, but variants of one command template or multiple steps from one session can remain strongly dependent. P:257 merely lists a deduplication artifact; it does not document its algorithm, thresholds, or cluster assignments. That artifact was not opened. No conclusion about its effectiveness follows from its existence in the protocol.

Three ratings per case would produce 360 judgments, not 360 independent experimental units. Likewise, multiple model outputs or repeat runs for the same case do not increase the number of independent cases. The ten repeated context strings cannot substitute for a verified session grouping. Effective sample size may be below 120; its magnitude cannot be estimated from these permitted structural inputs.

**Future v2:** define near-duplicate and session grouping before splitting, keep whole groups on one side of development/evaluation boundaries, and retain a protected case_id-to-group mapping with an independent custodian. The scientific report should still identify individual records only by case_id. Use a prespecified session/cluster analysis when dependence is plausible; do not invent clusters from wording after seeing errors. Disclose the number and size distribution of independent groups. An ordinary case-level bootstrap cannot repair unmodeled session dependence.

## Taxonomy and the meaning of the binary target

P:55–139 supplies operational definitions. Its instruction to label observable behavior is appropriate, and P:143–149 explicitly distinguishes technique discussion from execution. However, the binary projection assigns RECON and SUSPICIOUS to the malicious/positive class (P:156–161; M:19–28). SUSPICIOUS is expressly defined as ambiguous and not a direct attack step. The operational endpoint therefore includes behavior warranting investigation; it is not equivalent to proven malicious intent or an executed exploit.

Single-label boundaries overlap: credential reading can also involve elevated privileges; persistent access can be installed during exploitation; routine authorized administration can alter security-relevant state. The BENIGN definition restricts such state changes, while several attack definitions depend on authorization or intent not necessarily visible in a short transcript. No precedence rule for a multi-behavior case is specified in P or M. These are construct-validity and reproducibility concerns, not newly assigned labels.

**Future v2:** separate observed behavior from authorization evidence and investigation priority; define a deterministic primary-label precedence or a multilabel scheme and its binary projection. Pilot the taxonomy on disjoint development examples with human raters. Do not revise the present positive mapping after observing which categories improve a model's score.

## UNCERTAIN, majority voting, and adjudication

The frozen documented rule excludes UNCERTAIN from the primary binary metric and reports it separately (P:151–161, 248–249; M:28). This makes the primary estimand performance among cases retained after reference-label resolution, not unconditional performance on all 120. If thin context, particular source families, or difficult behaviors drive uncertainty, exclusion is informative and can change both spectrum and prevalence. It can favor either model; the direction cannot be determined without labels and outcomes.

P:196–216 and M:30–41 require at least two agreeing raters, retention of original judgments, and disagreement reporting. They do not resolve all aggregation details: whether category voting precedes projection, whether adjudication covers every 2:1 split or only absence of a majority, how an all-different triplet is handled, or how missing ratings and a majority UNCERTAIN interact with acceptance. For example, RECON/EXPLOITATION/BENIGN has a binary majority but no category majority. This is a hypothetical rule illustration, not a case label. Category-first voting and binary-first voting are not interchangeable.

The acceptance terms “enough adjudicated cases” and “agreement is defensible” are qualitative, leaving room for outcome-sensitive acceptance decisions. The wording is directly verified; whether another inaccessible frozen document already resolves it is unknown. The protocol's assertion that the contract preceded scores (P:218) is not independently established by this review. Independent shuffles help order effects but do not establish independent expertise or independent errors. Agreement is reproducibility evidence, not truth; Fleiss kappa is sensitive to marginal category frequencies and must be interpreted with raw and category-specific agreement.

**Future v2:** lock the order of voting/projection, tie and missing-rating rules, blinded adjudicator workflow, minimum retained count, and agreement acceptance thresholds before collecting evaluation labels. Set thresholds from a disjoint pilot and the scientific estimand, not from this set. Retain the flow from all sampled cases through completed ratings, majority decisions, adjudication, UNCERTAIN exclusions, and final paired comparisons. Report UNCERTAIN at rating and case levels separately. Prespecify exclusion sensitivity analyses or bounds; never relabel UNCERTAIN as benign for convenience. Human consensus remains an operational reference standard with uncertainty. AI ratings must remain separate exploratory evidence.

## Confidence gate, post-hoc choices, leakage, and calibration

The requested design statement is **route when Chrollo confidence <0.65**; equality at 0.65 is outside that strict inequality. This statement comes from the audit assignment. P and M mention confidence but do not specify that threshold, its derivation, missing-confidence behavior, or implementation. No gate membership, routing coverage, freeze chronology, or preregistration compliance was checked. Nothing here verifies the inaccessible preregistration JSON.

A confidence score need not equal probability of correctness. Its interpretation depends on the predicted class, source spectrum, and scoring mechanism. A threshold of 0.65 consequently does not establish a 35% conditional error rate or a calibrated risk guarantee. A gated subset is selected for the base model's uncertainty: conditional benefits within it cannot be generalized to all cases or compared fairly against an ungated method using a different denominator. Route frequency and fallback behavior are part of the policy's performance.

P:234–237 says a combination rule must be explicit and treats later combined results as post-hoc/exploratory. A routing gate alone does not define the final prediction: SIGNAL/NO_SIGNAL, disagreement, unparsable answers, missing responses, and abstention all require declared handling. Choosing overrides or adjusting the threshold after observing labels would contaminate a confirmatory claim. Such behavior is a risk assessed here, not an observed violation.

Structural inspection found only the allowed record fields. It did not test semantic leakage, example overlap, training exposure, or whether frozen outputs were available to selectors/raters. P:172–176 reports zero remaining leakage items and removal of provenance wording; these are documentary claims, not independently verified audit findings. Removing an explicit source field cannot guarantee that transcript style conceals source or label cues. P also displays the binary projection under wording that says it is “not shown here” (P:156–161); the text inconsistency is observable, but rater exposure is unverified because rater packets were not read. Distinguish intentional ontology instructions from prohibited model-output leakage.

**Future v2:** choose the gate and complete fallback/override policy on separate development data, preserve a verifiable chronology, and evaluate the locked policy on new sessions. Define what confidence estimates, assess reliability and class/source-specific calibration with suitable uncertainty on disjoint data, and evaluate both conditional routing outcomes and the end-to-end policy. Keep selectors, human raters, and adjudicators blind to model outputs. Audit development/evaluation and instruction-example overlap before freeze. No threshold, packet, or policy change is recommended for the current frozen set.

## N=120 and planned McNemar/bootstrap analyses

McNemar and bootstrap are plans named in the audit assignment, not analysis details verified in P or M. The reviewed documents do not specify endpoints, test sidedness, alpha, resampling units, interval construction, multiplicity handling, or power assumptions. This audit therefore evaluates their suitability conditionally; it does not attest that an implementation follows them.

For a paired binary-correctness comparison on one common reference-labeled set, let **C** count cases where the base model is wrong and the locked comparison policy is correct, and **H** count the reverse. McNemar evaluates the discordance asymmetry, not a difference between independent proportions. With independent case pairs, the exact null conditions on C+H and uses a Binomial(C+H, 0.5) distribution. Small discordance counts warrant exact treatment; absence of discordance provides no evidence of improvement and does not establish equivalence. Plain McNemar is not a nine-category confusion-matrix test, nor is its ordinary binomial justification assured with correlated session fragments.

N=120 alone cannot establish adequate power. Power depends on discordance probabilities, retained paired cases, dependence, the target improvement, and multiplicity. As an **illustration, not an observed result**, six corrections and no harms give a two-sided exact probability of 2/2^6 = 0.03125; five and no harms give 2/2^5 = 0.0625. If all 120 were evaluable, the former would be a five-percentage-point accuracy difference. This does not mean the study has adequate power for a five-point effect: a different correction/harm balance changes the test. Gating and UNCERTAIN exclusions can further reduce the relevant denominator. No numerical power claim is supported here.

Bootstrap comparisons must preserve pairing: draw the same case_id sample for both models and the reference label on each replicate. Independently bootstrapping model rows destroys the paired design. If sessions are the sampling units, resample whole independently sampled sessions; with very few clusters, bootstrap coverage itself becomes unreliable. Stratification or weighting must reflect the sampling design and target estimand. Undefined metrics in single-class replicates require a declared rule; silently dropping those replicates changes the analysis. A bootstrap over adjudicated labels estimates sampling uncertainty conditional on those labels, not uncertainty in human judgment. Neither bootstrap nor McNemar removes convenience-sampling bias.

**Future v2:** prespecify one primary paired endpoint, comparison, sidedness, alpha, practical effect target, multiplicity strategy, resampling unit, random seed, replicate count, and interval method. Base sample-size planning on independently estimated discordance and cluster structure, allowing for abstention/exclusion. Report paired effect intervals alongside exact counts and test results; do not interpret a nonsignificant difference as equivalence. Keep additional thresholds, categories, or policies exploratory unless prospectively included with appropriate error control.

## Correction versus harm

The analysis should distinguish four joint-correctness cells: both correct, correction C, harm H, and both wrong. On a common binary-evaluable denominator **n**, the difference in accuracy is **(C−H)/n**. Report C/n and H/n alongside that net effect; a net gain can conceal operationally consequential new errors. C divided by the number of base-model errors measures recovery opportunity, while H divided by the number of base-model correct decisions measures introduced-error risk. These conditional rates have different denominators and must not be subtracted as an accuracy gain. Zero denominators are undefined, not zero success or zero harm.

Separate new false positives from new false negatives, and the corresponding repaired errors, using the same reference labels and eligible cases. Any utility weighting needs externally justified, prospectively fixed costs. Disagreement, Laya SIGNAL, changed output, or reported confidence alone is not a correction. In multiclass reporting, both outputs can be wrong even when they disagree, and binary correctness can hide an incorrect attack subtype. Service failure and abstention require the policy's declared treatment and a full case flow; performance conditional on a successful answer is a separate estimand.

For a gate-based policy, report both the full-cohort policy effect and the prespecified routed-subset effect with explicit denominators and route coverage. If the policy leaves ungated predictions unchanged, ungated cases contribute zero net change but still belong to the overall policy denominator. That invariant must be checked by an authorized outcomes analyst; it was not tested here. Do not count unattempted or unavailable responses as inferred corrections.

**Future v2:** lock the correction/harm definitions and policy fallbacks before evaluation, retain the four-cell paired table, decompose errors by direction, and report full-cohort versus conditional effects and uncertainty separately. This report computes no corrections, harms, performance scores, or confidence intervals on the frozen cases.

## Evidence and completion boundary

The saved evidence record contains the exact shell invocations, exit statuses, input hashes, structural output, illustrative exact-test arithmetic, and a verification of this report's required topic coverage. Its scenario ledger names each audited requirement, its binary observable, and the captured artifact location. Topic-coverage checks certify presence in the report; they do not certify scientific validity or an unseen analysis implementation.

The directly reproducible checks are packet size/schema, identifier uniqueness, four duplicate comparisons, string-length summaries, taxonomy/projection coverage, and manifest binding. Documentary findings are grounded in the P/M line references above. Source quotas, session independence, semantic deduplication, actual rater independence, current human-label availability, calibration, freeze chronology, and model results remain unverified under this role's access boundary. No absence of evidence is treated as a proven integrity failure or a passing scientific validation.

All proposed methodological changes concern a **future v2**. Preserve the frozen design and independently enforce its existing rules; this audit supplies no retrospective authorization to amend them. Confirmatory performance, deployment readiness, and superiority over a baseline cannot be concluded from this design-only review.
