# Human Reference Standard Protocol

Protocol version: `human_v1`
Status: preregistered and frozen before human labels are collected.
Scope: independent offline cybersecurity behavior classification of the
exact frozen V3 set of 120 opaque cases.

## 1. Purpose and evidence boundary

This study creates an independently collected human reference standard.
The existing V3 instrument and its 120 case IDs are immutable. Human
raters label only the observable evidence and neutral context supplied in
their packet. They must not infer source, honeypot status, authorization,
or actor intent from formatting or context.

The three valid V3 AI runs are exploratory reliability evidence only. They
are not human raters, are not a reference standard, and cannot be
majority-voted or adjudicated into truth. AI labels must not influence
human raters or adjudicators. The invalid run remains quarantined.

## 2. Human study design

There are three independent primary human raters:

- `human_rater_01`
- `human_rater_02`
- `human_rater_03`

Preferred expertise includes cybersecurity, systems security, incident
response, penetration testing, digital forensics, or security research,
with the ability to interpret Linux commands, shell behavior, privilege
operations, reconnaissance, exploitation, credential or data access, and
persistence. Primary raters work independently. No discussion is permitted
before all initial ratings are frozen.

A fourth expert, `human_adjudicator_01`, adjudicates every case that is not
a unanimous 3/3 non-`UNCERTAIN` primary result. The adjudicator is not one
of the primary raters if avoidable.

Pseudonymous IDs are used in all research artifacts. Personal names and
unnecessary personal information are not collected.

## 3. Metadata and contamination declaration

The metadata form records only pseudonymous rater ID, security expertise
category, approximate years of security experience, Linux familiarity,
incident-response familiarity, offensive-security familiarity, prior
familiarity with RAGIN, prior access to Chrollo/Laya outputs, conflict or
contamination declaration, and annotation start and finish timestamps.

Before annotation, every primary rater and the adjudicator must answer:

1. Have you seen any Chrollo predictions for these cases?
2. Have you seen any Laya predictions for these cases?
3. Have you seen prior AI annotations for these cases?
4. Have you seen another human rater's annotations?
5. Have you previously worked directly on constructing this exact 120-case
   evaluation set?

Any `YES` is recorded and flagged for PI review before inclusion; it does
not automatically delete the rater. The coordinator maps the neutral
declaration fields in the handoff form to these five questions.

## 4. Frozen taxonomy

The taxonomy cannot change after human labeling begins:

- `BENIGN`: observable routine or defensive administration or information
  lookup with no defensible evidence of attack behavior.
- `RECON`: observable enumeration or probing reasonably associated with
  discovery or preparation for attack.
- `SUSPICIOUS`: observable concerning behavior that does not justify a
  stronger category.
- `EXPLOITATION`: observable active exploitation, payload execution,
  injection, vulnerability abuse, malicious download-and-execute, or
  equivalent.
- `PRIVILEGE_ESCALATION`: observable attempt to gain privileges beyond the
  current level.
- `DATA_ACCESS`: observable reading, collecting, staging, or exfiltration
  of credentials, tokens, private keys, databases, or other data.
- `PERSISTENCE`: observable creation of a durable foothold.
- `OTHER_ATTACK`: clearly adversarial behavior not better represented by
  another attack category.
- `UNCERTAIN`: evidence insufficient to assign a defensible category.

Critical labeling rules:

- Label observed behavior, not presumed actor intent.
- Do not infer source, honeypot status, or authorization merely from
  formatting.
- Natural-language discussion of an attack technique is not execution.
- A standard Linux command alone is not automatically malicious.
- Do not balance categories or use expected prevalence.
- `UNCERTAIN` is valid when evidence is genuinely insufficient.

## 5. Binary analysis boundary

Human raters and the adjudicator are not shown the binary projection. The
locked internal mapping is:

- `BENIGN` -> `NEGATIVE`.
- `RECON`, `SUSPICIOUS`, `EXPLOITATION`, `PRIVILEGE_ESCALATION`,
  `DATA_ACCESS`, `PERSISTENCE`, and `OTHER_ATTACK` -> `POSITIVE`.
- `UNCERTAIN` -> unresolved and excluded from the primary binary reference
  until adjudication.

## 6. Primary annotation packet and output

Each primary rater receives all 120 cases in an independent deterministic
order. The packet contains only an opaque `case_id`, frozen `evidence`,
frozen neutral `context`, and empty `label` and `note` fields. Evidence and
context are byte-equivalent to the frozen V3 instrument. Raters must
annotate all 120 cases independently.

For each case, complete:

```json
{"case_id": "...", "label": "...", "note": "short evidence-based reason"}
```

Notes must be short and evidence-based. Labels must be one of the nine
frozen taxonomy values. The human output schema requires exactly 120 unique
frozen case IDs, no blank labels, and no extra fields.

## 7. Predeclared agreement statistics

Before labels are collected, the following are frozen for the three
primary raters:

- Multiclass raw exact agreement.
- Pairwise exact agreement and pairwise Cohen's kappa.
- Fleiss' kappa.
- Category-specific disagreement.
- Binary eligible N, excluded N, observed agreement, and Fleiss' kappa.

For the pre-adjudication binary reliability calculation, use only cases
where all three initial ratings are non-`UNCERTAIN`. Report exclusions
explicitly; never silently recode `UNCERTAIN`.

## 8. Predeclared adjudication

After all three primary annotation files are frozen:

- If all three primary humans give the same non-`UNCERTAIN` multiclass
  label, mark `UNANIMOUS_REFERENCE`, use that exact label, and do not send
  the case to the adjudicator.
- Every other case is sent to the blinded adjudicator, including 2/3 exact
  agreement, three different labels, any `UNCERTAIN`, binary disagreement,
  or fine-grained category disagreement.

The adjudicator receives only the opaque case ID, evidence, neutral
context, and anonymized `RATER_A`, `RATER_B`, and `RATER_C` labels with
their short notes. The adjudicator must not receive AI labels, model
predictions or names, scores, source provenance, expected answers, or
previous correctness results. The adjudicator assigns one of the nine
taxonomy labels or `UNRESOLVED`, with a short rationale.

Final reference construction is immutable:

- 3/3 exact non-`UNCERTAIN`: `UNANIMOUS_PRIMARY_HUMANS`.
- Non-unanimous case adjudicated to a taxonomy label:
  `BLINDED_HUMAN_ADJUDICATION`.
- Adjudicator returns `UNRESOLVED`: `reference_status=UNRESOLVED`, with no
  forced truth label.

Preserve all three original ratings, original notes, the adjudicator
decision, and the adjudication rationale. Never overwrite primary ratings.

## 9. Confirmatory eligibility gate

Before labels exist, primary binary confirmatory analysis is eligible only
if all of the following hold:

- At least 100 of 120 cases receive a resolved human reference label.
- At least 90 cases remain evaluable after the binary reference projection.
- All model predictions were frozen before human reference creation.
- No threshold or decision rule changed after labels.

If fewer than 100 cases resolve, binary model comparison is exploratory.
Multiclass results are descriptive for all resolved cases. If fewer than
90 cases receive resolved multiclass references, multiclass model
comparison is explicitly exploratory. Human agreement is always reported.
AI agreement cannot satisfy any threshold.

## 10. Locked endpoints and paired test

On the same resolved paired cases, report balanced accuracy as primary.
Secondary binary metrics are accuracy, macro-F1, precision,
recall/sensitivity, specificity, FPR, FNR, and the confusion matrix.
Where applicable, multiclass metrics are macro-F1, per-class precision,
per-class recall, and the confusion matrix. All `UNCERTAIN` and
`UNRESOLVED` exclusions are reported with counts.

For the paired binary Chrollo-vs-Laya comparison use exact two-sided
McNemar/binomial treatment when the discordant count is small. Define:

- `C`: Chrollo wrong, Laya correct.
- `H`: Chrollo correct, Laya wrong.

Report `C`, `H`, `C+H`, exact p-value, and absolute paired accuracy
difference. Absence of significance is not interpreted as equivalence.

## 11. Locked bootstrap

Use paired bootstrap only. Each of 10,000 replicates resamples the same
case IDs jointly for the human reference, Chrollo result, and Laya result;
models are never bootstrapped independently. Report 95% percentile CIs for
balanced accuracy, accuracy, macro-F1, sensitivity, specificity, and
paired metric differences. If verified session groups later support
clustered resampling, report cluster bootstrap only as a sensitivity
analysis. Do not invent session groups.

## 12. Locked gated policy

The existing gate remains Chrollo confidence < 0.65 for invoking Laya.
Do not change or optimize this threshold on human labels. Unless its
scientific basis is independently justified with development data, all
gated-policy results are labeled `PREREGISTERED EXPLORATORY` and are not
promoted to primary confirmatory evidence because of favorable results.

## 13. Stop boundary

This freeze ends before label collection. No human annotation, simulated
judgment, adjudication case generation, prediction access, label join,
threshold tuning, model execution, or confirmatory analysis is performed
under this handoff.
