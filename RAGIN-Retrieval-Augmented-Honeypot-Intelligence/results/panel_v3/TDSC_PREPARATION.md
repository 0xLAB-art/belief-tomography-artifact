# TDSC/T-IFS Submission Preparation — Remaining Work Items

## Status: All experiments that CAN run have run. Below: what remains for 5/5 accepted, organized by who can execute it.

---

## 1. Human-Anchor Study (J1/J5/R1's price of admission) — READY TO RUN
### Needs: 2 human raters (the user + 1 colleague)
### Protocol: `docs/HUMAN_ANCHOR_PROTOCOL.md` (create from template below)
### Time: 2-3 hours total

Select 40 cases stratified at the benign/recon boundary (where the
deterministic oracle fails). Each rater labels independently, blind
to AI panel labels. Report:
- Human-vs-panel agreement (exact + binary κ)
- Human-vs-cross-family-juror agreement
- Propagate as uncertainty band on the 3.86/5 quality score

**Script to create:** `scripts/human_anchor_study.py` (packet selection, blinding, analysis)

---

## 2. v3 Decomposition Control (J3's decisive ask) — READY TO RUN
### Needs: API credit (agentrouter key works for gpt-6.1-sol)
### Time: 3-4 hours (10 sessions arm A with bait planted + cowrie restarted)

**Already done:** bait files planted in honeyfs volume.
**Remaining:** restart field-cowrie container, run 10 sessions with the
v3 driver (arm A, gpt-6.1-sol brain from V3 key), measure whether stock
cowrie WITH bait returns artifacts on reads.

**Script to create:** `scripts/run_v3_decomposition.sh`
**Expected outcomes:**
- Stock+baits yields artifacts → yield is bait placement, not generative deception → paper must reframe
- Stock+baits does NOT yield → dynamic serving is genuinely different → paper strengthened

---

## 3. Disjoint-Juror Re-score of the Ablation (J1/J4/J5 decisive) — READY TO RUN
### Needs: apinex credit (kimi/gemini/qwen — all free, all non-OpenAI families)
### Time: 2-3 hours (180 responses × 2 jurors)

**Already done:** 540 responses dumped with full text in
`results/b4_fresh_responses.jsonl`.
**Script to create:** `scripts/disjoint_juror_rescore.py` (read dump,
score blind to arm with kimi-k3 + gemini-3.8-flash, compute paired delta
under independent labeler, bootstrap CI)

**Expected outcomes:**
- Δ survives under independent labeler → J1/J4/J5 withdraw W1 (analysis-channel validity)
- Δ shrinks or vanishes → paper must report instrument bias → still publishable as honest negative result

---

## 4. Injection Containment on Live Path (J2-Q3) — READY TO RUN
### Needs: the running docker stack (already up)
### Time: 1 hour

**Already done:** `results/panel_v3/injection_containment.json` (unit-level).
**What's missing:** an on-path experiment through the actual serving
pipeline: send an injected draft through cowrie→gateway→verifier→response,
verify that the next session's fiction graph is unaffected.

**Script to create:** `scripts/injection_containment_onpath.py`
(requires the docker stack, no API credits)

---

## 5. Key Rotation (SECURITY — do before any submission)
- Rotate `AGENTROUTER_API_KEY_V3` (pasted in chat)
- Rotate `AGENTROUTER_API_KEY` (pasted in chat)
- Rotate `RAGIN_JEVI_API_KEY` (pasted in chat)
- Rotate `APINEX_API_KEY` (pasted in chat)

---

## 6. Top-up API Credits
- beatapi.io: needed for cross-family juror (claude-sonnet-5-5) and v3 brain extension
- apinex.bond: needed for disjoint-juror re-score (kimi/gemini/qwen)
- agentrouter.org: still has credit (gpt-5.6-sol/6-astra/6.1-sol work)

---

## 7. Paper Format Conversion (S&P → TDSC)
- Switch from IEEEtran conference to IEEEtran journal (TDSC uses IEEE Computer Society format)
- Expand to 14-18pp double-column
- Add: Threats to Validity section (DONE: sp_threats.tex)
- Add: expanded Implementation Details section
- Add: expanded Related Work
- Add: Data Availability Statement (mandatory for TDSC)
- Add: Author Contributions (CRediT taxonomy)
- Add: Conflicts of Interest statement
- Add: Funding statement
- Keep: Ethics section (already present)

---

## Priority Order for Maximum Acceptance
1. Disjoint-juror re-score (needs apinex credit) — answers 3 judges
2. Human-anchor study (needs 1 colleague) — answers 2 judges
3. v3 decomposition (needs agentrouter credit) — answers 1 judge
4. Injection containment on-path (free) — answers 1 judge
5. Paper format conversion (free) — required for TDSC
