# Reviewer bundle — the shortest path to the headline numbers

Ten minutes to verify the deposit, thirty minutes to recompute the headline
table.

## 1 · Verify every hash (2 min)

```bash
./verify.sh
```

Expected: `395 frozen + 46,772 supplementary files OK`.

## 2 · Recompute the open-weight table (5 min)

```bash
bash checks/quick_counts.sh
```

Prints, from the frozen verdicts and transcripts:

- the per-panel oracle-flag decomposition
  (**118** `unauthorized_action` refusal-quote FPs + **112** genuine
  `secret_leak` echoes = **230** flags), and
- the blocked-turn / censored-session table
  (E30 Flash 9 · V4-Pro 79 · MiniMax 305 · E31 Flash 0 · V4-Pro 59 ·
  MiniMax 24).

## 3 · Check the adjudication trail (10 min)

1. `gauntlet/demo/E29_E30_ORACLE_AUDIT.md` — the author-side audit of all 230
   flags (header discloses its non-blind adjudication).
2. `docs/paper/belief_tomography/independent_reaudit/` — the blinded Round-19
   re-adjudication: three coders from different model families, blind to
   panel/model/session/label, 46-item 20 % stratified sample, agreement
   45/46 (κ = 0.96), pairwise 46/46.

## 4 · Read the honesty layer (5 min)

- `CLAIMS_EVIDENCE_LEDGER.md` → **STATUS NOTE — registration integrity**:
  which registrations precede their data and which do not, with the frozen
  file evidence.
- Manuscript §Limitations and Supplement Table S2 — the same record, printed.
- `REDACTIONS.md` — every substitution made for publication.

## 5 · Build the manuscripts (10 min, optional)

```bash
pdflatex paper/tdsc_tomo/main.tex && pdflatex paper/tdsc_tomo/main.tex   # 13 pp
pdflatex paper/tdsc_tomo/supplement.tex                                  # 22 pp
pdflatex paper/tops/main.tex && pdflatex paper/tops/main.tex             # 45 pp
```

## Key numbers to cross-check against the manuscript

| Claim | Where | Artifact |
|---|---|---|
| Repaired panel 0.017 pooled | §6.1 | `E29_*_p20_s2718.*` |
| Open-weight spectrum 0.030–0.143 | Table VI | `E30_*`, `E31_*` verdicts |
| 230-flag decomposition (118 + 112) | §6.1 caption | audit + `quick_counts.sh` |
| Blinded re-audit κ = 0.96 | §Limitations | `independent_reaudit/agreement.json` |
| Censoring 74.7 % (E30 V4-Pro) | §Limitations | `E30_…_Pro.transcripts.jsonl` |
| Field nulls [0, 0.013] at n = 300 | §VI | ledger rows, section F |
