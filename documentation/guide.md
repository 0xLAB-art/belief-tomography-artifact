# Ledger guide — how every printed number is checked

`docs/paper/belief_tomography/CLAIMS_EVIDENCE_LEDGER.md` maps **every
quantitative claim** in the manuscript to the artifact that carries it and to
the recomputation that was performed for this deposit.

## Reading order

1. **STATUS NOTE — registration integrity.** Experiment by experiment, which
   registrations precede their data and which do not; the retroactive
   header-date edits; the frozen twins. The manuscript discloses the same
   record in §Limitations and Supplement Table S2.
2. **The claim rows.** One row per number: *claim as printed · value ·
   artifact path(s) · commit · verification*.
3. **The pre-registration hash table** at the end pins every registration file
   as it exists now.

## Artifact schemas

Verdicts — one line per session:

```json
{"session_id": "…", "family": "…", "generation": 1, "passed": true, "violated": []}
```

Transcripts — one line per turn:

```json
{"session_id": "…", "family": "…", "generation": 1, "turn": 0,
 "adversary": "…", "environment": "…", "reply": "…", "blocked": false}
```

## Worked example: the 230-flag audit

```bash
for f in gauntlet/demo/E3{0,1}_*_p20_s2718.verdicts.jsonl \
         gauntlet/demo/E29_*_p20_s2718.verdicts.jsonl; do
  echo -n "$(basename "$f"): "
  jq -s '[.[]|.violated[]]|group_by(.)|map("\(.[0])=\(length)")|join(" ")' "$f"
done
```

Sums: `unauthorized_action` = 5+11+24+13+37+28 = **118** refusal-quote false
positives; `secret_leak` = 9+40+9+43+11 = **112** genuine case-insensitive
canary echoes. `gauntlet/demo/E29_E30_ORACLE_AUDIT.md` adjudicates all 230;
`docs/paper/belief_tomography/independent_reaudit/` re-checks a 20 % stratified
sample blind.

## Worked example: censoring

```bash
for f in gauntlet/demo/E3{0,1}_*_p20_s2718.transcripts.jsonl; do
  echo -n "$(basename "$f") "
  jq -s '[.[]|select(.blocked==true)]|length' "$f"
  jq -s '[.[]|select(.blocked==true)]|map(.session_id)|unique|length' "$f"
done
```

Reproduces the blocked-turn counts printed in Table VI and §Limitations.

## Path conventions

- `gauntlet/tomograph.py` / `gauntlet/verdict.py` (the estimator pin) are the
  package modules `gauntlet/gauntlet/tomograph.py` and
  `gauntlet/gauntlet/verdict.py`.
- `gauntlet/demo/PREREGISTRATION_E2V1B.md` is deposited there and
  manifest-pinned at `docs/paper/belief_tomography/PREREGISTRATION_E2V1B.md`
  (identical bytes).
- Bare `results/…` citations resolve both at the repository root and under
  `RAGIN-Retrieval-Augmented-Honeypot-Intelligence/results/…`.

## Provenance labels

Commit hashes cited in the ledger come from the author's private development
repository and are **not resolvable here**. The manifest hashes are the
operative freeze.
