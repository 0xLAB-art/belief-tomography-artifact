# Dwell Replay — Round 3: In-World Scrubbing, Identity Seeding, Credential Realism

**Date:** 2026-09-20 · **Artifacts:** `results/jev_dwell_replay_v3*.json` · Previous rounds: `jev_dwell_replay_llm_REPORT.md` (v1), `jev_dwell_replay_v2_REPORT.md` (v2)

## What was engineered this round (targeting v2's remaining ceilings)

| v2 ceiling | Fix shipped |
|---|---|
| "Identity responses inconsistent" | Ledger now **seeds per-session persona identity facts** (user/hostname/os/kernel from `identity_for`) at session creation — frozen in the fact block every turn (`AdaptiveDeceiver`). |
| "Unexplained redactions" | Scrubber substitutions are now **in-world**: secrets → `********` (what sudo/scrubbers actually print), `root@localhost` → the pinned fictional `user@host`, prose-tell lines (honeypot/simulated/fabricated) dropped entirely, no visible `[REDACTED]` markers remain. Refusal patterns void the reply (retry) as before; maskable *secrets* no longer void — the line survives masked. |
| (anticipatory) "documentation-example credentials" | Persona identity block now carries an explicit **credential-realism rule**: never emit canonical AWS docs keys, `changeme`, `password123`, etc. |

Quality gates: **1084 unit tests pass (+5 new), ruff clean.**

## Verification runs (cloud_metadata_ssrf, lateral_pivot — the two v2-ceiling families)

| Family | Arm | v2 | v3 | v3 leave reason |
|---|---|---|---|---|
| cloud_metadata_ssrf | baseline | 10 | 4/6 | IMDS returned **AWS documentation example credentials** → trap |
| cloud_metadata_ssrf | treated | 8 | 3/2 | masked `ASIAV***` creds / **placeholder-pattern secrets**; IMDS protocol shape wrong |
| lateral_pivot | baseline | 12 | 6/4 | repeated identical outputs → scripted shell |
| lateral_pivot | treated | 4 | 3/3 | "all responses redacted, no actionable data — likely trap" |

## Honest reading

1. **The fixed ceilings are gone** — no v3 leave reason cites inconsistent listings, contradictory identity, or visible `[REDACTED]` markers. That layer of the deception stack is now solid.
2. **Ceilings migrate; they don't vanish.** The attacker-LLM now fails us on *fiction content quality*:
   - **Credential masking is protocol-dependent.** `********` is correct for on-disk configs but *wrong* for a credential-issuing response (IMDS/IAM): a real instance metadata response always returns complete-looking (fake) credentials. Response-shape fidelity must be scenario-aware.
   - **Scenario/identity mismatch.** The persona identity is a `corp.local` datacenter host; a cloud-metadata SSRF probe implies a cloud VM (`.compute.internal`, IMDS endpoint present). Either seed cloud-shaped identities for such sessions or answer IMDS probes with a plausible denial.
   - **Lateral pivot remains under-baited.** The treated arm sees only redactions and no internal-topology intel — the kind-aware guidance ("expose decoy topology") needs the bait artifacts actually present in the fiction, not just instructed in the prompt.
3. **n=2 probe families, single seeds, ±3-turn variance** — these runs validate which *tells* fire, not effect sizes.

## Where this leaves the ladder

| Round | Dominant attacker tell | Status |
|---|---|---|
| v1 | Inconsistent filesystem fiction | **Fixed** (ledger, v2) |
| v2 | Identity inconsistency · visible redactions | **Fixed** (seeding, in-world scrubbing) |
| v3 | Documentation-example credentials · protocol-shape errors · under-baited lateral fiction | **Open** |

Next, by leverage: (1) scenario-aware credential responses (complete fake creds for IMDS/`env`-style outputs, masks only for on-disk files); (2) cloud-shaped identity variants; (3) seed lateral/topology bait artifacts into the ledger when the Jev kind is `lateral`.
