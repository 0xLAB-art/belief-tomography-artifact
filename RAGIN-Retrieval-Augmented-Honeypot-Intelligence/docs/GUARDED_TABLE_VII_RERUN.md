# Guarded Table VII Re-run — Operator Protocol

**Goal:** replace the pre-guard external-baseline ladder (Table VII / `tab:two-channel`
Table 2) with a fully guarded, model-coherent, served-text re-run of every arm on the
version-of-record 218-query workload (123 technique + 35 actor + 60 persona).

**Status 2026-09-29:** BLOCKED — apmix gateway returns HTTP 429
`insufficient_quota` / `allowance_exhausted` on `/v1/chat/completions`
(catalog endpoint still 200). See the latest record in
`results/apmix_probe_history.jsonl`. Resume when the monthly allowance
resets or a top-up is applied. This is a billing state, not throttling:
every LLM arm dies at turn one; only the cowrie arm needs no gateway.

## Preconditions

1. Quota live — verify:
   ```bash
   set -a; source .env; set +a
   .venv/bin/python - <<'PY'
   import json, os, urllib.request
   req = urllib.request.Request("https://api.apmix.ai/v1/chat/completions",
       data=json.dumps({"model": os.environ["RAGIN_HISOKA_MODEL"] if "RAGIN_HISOKA_MODEL" in os.environ else "deepseek-v4-flash-free",
                        "messages":[{"role":"user","content":"ping"}], "max_tokens":5}).encode(),
       headers={"Authorization": f"Bearer {os.environ['RAGIN_LLM_API_KEY']}",
                "Content-Type": "application/json"})
   try:
       r = urllib.request.urlopen(req, timeout=30)
       print("OK", r.status)
   except urllib.error.HTTPError as e:
       print("BLOCKED", e.code, e.read()[:120])
   PY
   ```
   HTTP 200 → proceed. 429 → stop.
2. Canary discipline: never trust the first serve; the smoke step below doubles as
   the canary (if every response is template-identical, generation is not live).
3. Do NOT push, do NOT delete artifacts; archive only (step 0).

## Step 0 — Archive stale score-only checkpoints (MANDATORY)

The September repro checkpoints persist scores without served text. Because the
runner resumes by row name, leaving them in place would replay 218 score-only rows
per arm and regenerate the exact provenance hole the scorer-validity audit exposed.

```bash
for arm in stateful_llm rag_no_verifier_repro ragin_full_repro ragin_hostfiction; do
  mv "results/external_baseline_${arm}_full_checkpoint.json" \
     "results/external_baseline_${arm}_full_checkpoint.prescoreonly-v1.json"
done
```

`run_external_baseline.py` now writes a `response_preview` (first 200 chars of the
served text) on every row of every arm, so any future scorer revision can be
applied offline. Verify the preview field is present after the first smoke:

```bash
python3 -c "import json; r=json.load(open('results/external_baseline_stateful_llm_limit5_checkpoint.json'))['rows'][0]; print('response_preview' in r)"
```

## Step 1 — Smoke each arm (`--limit` uses its own checkpoint; full artifacts untouched)

```bash
for arm in stateful_llm llm_unverified rag_no_verifier_repro ragin_full_repro ragin_hostfiction; do
  .venv/bin/python scripts/run_external_baseline.py --arm "$arm" --limit 5 || exit 1
done
```

Pass criteria per arm: 15/15 rows, no 429 in stderr, previews non-null on
generated rows, and at least two distinct preview strings (canary against
template-fallback deception).

## Step 2 — Full runs (in this order; per-row checkpoint resume, so re-invoke on any death)

```bash
for arm in stateful_llm llm_unverified rag_no_verifier_repro ragin_full_repro ragin_hostfiction; do
  .venv/bin/python scripts/run_external_baseline.py --arm "$arm" \
    || { echo "ARM $arm died — re-invoke to resume"; break; }
done
```

- ~40–70 min per arm on the free tier; to chunk wall-clock time add `--budget-s 3600`
  and re-invoke until the artifact reports no `error` field.
- Completion check: all five payloads report 218/218 rows and no `error`.

## Step 3 — Rebuild the model-coherent ladder

Assemble `results/external_baseline_model_coherent.json` in its existing shape
(`model_coherent_table.arms` — cowrie/stateful_llm/llm_unverified/
rag_no_verifier_repro/ragin_full/ragin_hostfiction), replacing every regenerated
row's suite avgs + composite from the new artifacts and updating each `note`
("guarded served-text re-run, <date>, generator deepseek-v4-flash-free"). Keep the
old artifact by copying it to `.pre-guarded-v1` first. The cowrie row is unchanged
(no LLM; composite 0.0006).

## Step 4 — Regenerate the §VI tables

```bash
.venv/bin/python scripts/gen_two_channel_tables.py
cp results/section_vi_two_channel_tables.tex paper/sections/two_channel_tables.tex
```

## Step 5 — Paper edits that the new numbers unlock

1. `evaluation.tex` "Effect under the guarded scorer" paragraph (~line 108): the
   "cannot be re-derived offline / released as the protocol's next step" disclosure
   is replaced by the new guarded served-text differential for every arm.
2. `tab:two-channel` Table 2 caption: drop the "pre-guard levels disclosed" hedge;
   state all arms guarded served-text, one generator, one date.
3. Threats/limitations: the honest-baseline-scorer limitation shrinks to the one
   surface that genuinely cannot be rescored (the Sep-22 VOR campaign), whose
   echo-zeroed lower bounds (`vor_guarded_served_text_lower_bounds.json`) remain
   correctly labeled.
4. Re-run the full numbers audit against the new artifacts before quoting anything.

## Step 6 — Guard spot-check on the new artifact (must be zero findings)

```bash
python3 - <<'PY'
import json, re
for f in ("external_baseline_stateful_llm", "external_baseline_llm_unverified",
          "external_baseline_rag_no_verifier_repro", "external_baseline_ragin_full_repro",
          "external_baseline_ragin_hostfiction"):
    d = json.load(open(f"results/{f}.json"))
    arms = d.get("arms", d)
    for name, arm in (arms.items() if isinstance(arms, dict) else []):
        for r in arm.get("per_row", []):
            p = r.get("response_preview") or ""
            if r["score"] > 0 and "command not found" in p.lower() and r.get("query_echo"):
                print("GUARD MISS", f, name, r["name"])
print("spot-check done")
PY
```

(If the `query_echo` flag is absent from rows, compare the preview against the
workload query verbatim as the VOR audit did.)

## Step 7 — Standing closure discipline

- `.venv/bin/python -m pytest -q` full suite green; `.venv/bin/ruff check` clean on
  touched files; `graphify update .` after edits; commit with artifact + paper in
  one change-set.
- Update `docs/SP2027_SUBMISSION_PLAN.md` close-out list: guarded Table VII moves
  from open to DONE with the artifact name.
