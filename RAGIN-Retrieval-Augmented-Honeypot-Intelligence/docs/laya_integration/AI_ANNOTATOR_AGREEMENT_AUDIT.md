# AI Annotator Agreement Audit

Blinded reliability audit of annotation runs for the confirmatory study.

This audit compares annotation files only. It does not inspect:
- Chrollo predictions
- Laya predictions
- frozen_predictions.jsonl
- confirmatory_frozen_predictions.jsonl
- ground truth
- provenance
- source identities
- model confidence
- confirmatory analysis outputs

## Runs found

| run_id | original_path | rater_id | model | sha256 |
|---|---|---|---|---|
| packet_r1 | results/laya_research/rater_packets/r1.json | r1 | blank template | 498b48622a45f04d597a89f147a5d045e38e41a4f4c01e81499b37dba5530277 |
| packet_r2 | results/laya_research/rater_packets/r2.json | r2 | blank template | 1388048aa4ac6a46a30756e8226109df9979b10e0c14904203e335c5f01e4af1 |
| packet_r3 | results/laya_research/rater_packets/r3.json | r3 | blank template | 280d6e0e12d5deefa42e0a833c6f56fcde221a4e7ac2b38378344be78dda1f3d |
| ai_r1 | results/laya_research/ai_raters/codex_r1.json | r1 | Codex | b1b9bade5e7a40962e573e8acf0ab8c4cea7b4cfe4bea7eb3fe896b3e27a9c37 |
| ai_r2 | results/laya_research/ai_raters/codex_r2.json | r2 | Codex | a953002be5feaf3ead9dded7106b4bc3c76f6344ca8db25f6d1a869a77717f07 |
| ai_r3 | results/laya_research/ai_raters/codex_r3.json | r3 | Codex | b30a155f86a3d69ce22ddec7089183058d4558ae477c16b7f6f58bae4e2a817d |
| human_r1 | results/laya_research/rater_labels/r1.json | r1 | human annotation records | 707d685fd780d6e5b78b46a9637f4443f037e8f9130b7ae2429c96ec8a3d45ba |
| human_r2 | results/laya_research/rater_labels/r2.json | r2 | human annotation records | 595d83e14c464ab14410e62307db1b0a766c0bf2381fb4e9c5378920e5daadd3 |
| human_r3 | results/laya_research/rater_labels/r3.json | r3 | human annotation records | 544d5766030e7e9479feb631459d9c1ca3a03e0353c458144132ded500ab7e6e |

Blank packets are retained as run records because they are the instruction instruments. They carry no labels.

All runs cover the same 120-case confirmatory set.

## Multiclass agreement

Pairwise exact multiclass agreement on the 120-case shared set.

| pair | exact | rate | disagree | Cohen's kappa |
|---|---|---|---|---|
| ai_r1 x ai_r2 | 97 | 0.8083 | 23 | 0.6454 |
| ai_r1 x ai_r3 | 95 | 0.7917 | 25 | 0.5946 |
| ai_r2 x ai_r3 | 98 | 0.8167 | 22 | 0.6966 |
| ai_r1 x human_r1 | 84 | 0.7000 | 36 | 0.4003 |
| ai_r1 x human_r2 | 73 | 0.6083 | 47 | 0.3639 |
| ai_r1 x human_r3 | 77 | 0.6417 | 43 | 0.3021 |
| ai_r2 x human_r1 | 96 | 0.8000 | 24 | 0.6614 |
| ai_r2 x human_r2 | 88 | 0.7333 | 32 | 0.6042 |
| ai_r2 x human_r3 | 92 | 0.7667 | 28 | 0.6112 |
| ai_r3 x human_r1 | 88 | 0.7333 | 32 | 0.5324 |
| ai_r3 x human_r2 | 79 | 0.6583 | 41 | 0.4900 |
| ai_r3 x human_r3 | 84 | 0.7000 | 36 | 0.4832 |
| human_r1 x human_r2 | 88 | 0.7333 | 32 | 0.5962 |
| human_r1 x human_r3 | 103 | 0.8583 | 17 | 0.7493 |
| human_r2 x human_r3 | 96 | 0.8000 | 24 | 0.6982 |

Full transition tables are in `results/laya_research/ai_rater_pairwise_agreement.json`.

## Binary agreement

Binary projection:

- BENIGN -> NEGATIVE
- RECON, SUSPICIOUS, EXPLOITATION, PRIVILEGE_ESCALATION, DATA_ACCESS, PERSISTENCE, OTHER_ATTACK -> POSITIVE
- UNCERTAIN -> excluded from that pair for the primary binary metric, but counted separately

| pair | binary_n | binary_exact | binary_rate |
|---|---|---|---|
| ai_r1 x ai_r2 | 117 | 97 | 0.8291 |
| ai_r1 x ai_r3 | 106 | 94 | 0.8868 |
| ai_r2 x ai_r3 | 106 | 97 | 0.9151 |
| ai_r1 x human_r1 | 117 | 84 | 0.7179 |
| ai_r1 x human_r2 | 117 | 75 | 0.6410 |
| ai_r1 x human_r3 | 115 | 79 | 0.6870 |
| ai_r2 x human_r1 | 117 | 103 | 0.8729 |
| ai_r2 x human_r2 | 118 | 94 | 0.7966 |
| ai_r2 x human_r3 | 108 | 97 | 0.8981 |
| ai_r3 x human_r1 | 106 | 90 | 0.8491 |
| ai_r3 x human_r2 | 114 | 83 | 0.7281 |
| ai_r3 x human_r3 | 104 | 87 | 0.8365 |
| human_r1 x human_r2 | 117 | 94 | 0.8034 |
| human_r1 x human_r3 | 113 | 107 | 0.9469 |
| human_r2 x human_r3 | 117 | 96 | 0.8205 |

Binary n can be lower than 120 because pairs where either annotator answered UNCERTAIN are excluded from the primary binary metric. Blank labels are also excluded.

## Cross-model stability

Same rater_id, different underlying model. Not test-retest reliability of one annotator. Treated as cross-model annotation stability.

### r1 packet - Codex vs human

- exact multiclass: 84/120 (0.7000)
- binary: 84/117 (0.7179)
- Cohen's kappa: 0.4003
- most common transitions:
  - BENIGN -> EXPLOITATION: 6
  - RECON -> BENIGN: 11
  - BENIGN -> DATA_ACCESS: 5
  - BENIGN -> RECON: 5
  - BENIGN -> OTHER_ATTACK: 2
  - BENIGN -> PERSISTENCE: 2

### r2 packet - Codex vs human

- exact multiclass: 88/120 (0.7333)
- binary: 94/118 (0.7966)
- Cohen's kappa: 0.6042
- most common transitions:
  - BENIGN -> RECON: 20
  - RECON -> BENIGN: 3

### r3 packet - Codex vs human

- exact multiclass: 84/120 (0.7000)
- binary: 87/104 (0.8365)
- Cohen's kappa: 0.4832
- most common transitions:
  - BENIGN -> RECON: 8
  - RECON -> BENIGN: 7

### Codex inter-rater stability

Same model, different shuffled Codex runs on the same packet set.

- ai_r1 x ai_r2: exact 97/120 (0.8083), binary 97/117 (0.8291), kappa 0.6454
- ai_r1 x ai_r3: exact 95/120 (0.7917), binary 94/106 (0.8868), kappa 0.5946
- ai_r2 x ai_r3: exact 98/120 (0.8167), binary 97/106 (0.9151), kappa 0.6966

Cross-model detail is in `results/laya_research/ai_rater_stability_summary.json`.

## Consensus structure

Defined on the 120-case complete set.

- STRONG_CONSENSUS: 60
- BINARY_CONSENSUS: 8
- MAJORITY_ONLY: 52
- HIGH_AMBIGUITY: 0
- TOTAL: 120

The empty HIGH_AMBIGUITY bucket is partly a definitional effect: any case with a 2-way majority is counted as MAJORITY_ONLY. Many of those 52 cases are near-50/50 RECON vs BENIGN splits, so they are not strong consensus in the practical sense.

## Most disagreed cases

Top 10 case IDs only. No predictions, no provenance.

1. F1AAE1C198D1
2. 00DBAC0794CA
3. 19595B9DEFEA
4. AD7B7844B156
5. E4E12ED202B2
6. F2135DA32462
7. 23A0BB12E4C1
8. 284C37E21B6F
9. 4CDF05DB8008
10. 4EC7E323A02A

These cases concentrate around the RECON/BENIGN boundary and the OTHER_ATTACK/EXPLOITATION/PERSISTENCE/DATA_ACCESS cluster.

Full per-case map is in `results/laya_research/ai_rater_disagreement_map.jsonl` (120 rows).

## Agreement coefficients

- Pairwise Cohen's kappa reported for every pair.
- Fleiss' kappa on the full 9-run complete set: 0.2356.

The Fleiss figure is reported for completeness but is not the primary reliability metric, because three of the nine runs are blank instruction packets.

## Interpretation

AI annotation on this confirmatory set is MODERATELY STABLE, with a clear RECON/BENIGN boundary sensitivity and a secondary seriousness-class sensitivity.

Evidence:

- Same-model Codex runs agree best. ai_r1 x ai_r2 and ai_r2 x ai_r3 are the strongest pairs overall (exact 0.81-0.82, binary 0.83-0.92, kappa 0.65-0.70).
- Model swap degrades agreement. For each rater_id, the Codex run disagreed more with the corresponding human run than the Codex runs disagreed with each other.
- The largest instability signal is RECON <-> BENIGN flipping, especially in the r1 pair.
- Human raters also disagree among themselves, mainly on RECON versus BENIGN.
- Human inter-rater agreement is good-to-moderate; human_r1 x human_r3 is the strongest human pair (kappa 0.75, exact 0.86).
- ai_r3 used UNCERTAIN much more than the human raters, which is itself a model sensitivity signal.

## Verdict

MODERATELY STABLE. Usable for confirmatory analysis, but not as a clean point estimate.

Do not treat any single annotation as ground truth, and do not majority-vote the annotations into the confirmatory truth yet. The main unresolved surface is the RECON/BENIGN boundary and the OTHER_ATTACK cluster.
