# IEEE S&P hard-blocker closure plan

> Execution rule: resolve local evidence and manuscript blockers first; keep VPS,
> provider availability, and human-rater work explicitly blocked until their
> prerequisites are satisfied. Never convert an archived or fallback result into
> a fresh provider result.

## Goal

Move the RAGIN project from `AUDIT-DRAFT-ONLY` toward a defensible S&P release by closing every blocker that can be closed in the repository and by producing executable handoff packages for the blockers that require external infrastructure or independent people.

## Release states

- `CLOSED-LOCAL`: verified from repository sources/artifacts without new authority.
- `READY-FOR-VPS`: local harness and safety gates are complete; external deployment is the remaining dependency.
- `READY-FOR-HUMAN-EVAL`: blinded protocol, rubric, consent, and scoring pipeline are ready; independent raters are still required.
- `BLOCKED-EXTERNAL`: provider, VPS, or independent-rater evidence is required and unavailable.
- `SUBMISSION-READY`: only after all critical/major evidence and build gates pass; this plan does not assume that outcome.

## Workstreams

### A. Threat model and claim boundaries

- [x] Create a formal security/threat-model matrix covering attacker capabilities, trusted components, attack surfaces, security properties, evidence, and nonclaims.
- [x] Add the matrix to the canonical S&P source and align abstract, contributions, evaluation, discussion, and conclusion wording.
- [ ] Add held-out verifier stress cases for prompt injection, CTI poisoning, cross-session contamination, malformed output, retry/resource abuse, and verifier adaptation where these can be tested offline.
- [x] Preserve the closed-surface boundary when a case is not independently generated or does not exercise a real deployed boundary.

### B. Paired experiment and provenance

- [x] Add canonical scenario IDs, manifest hashes, prompt/config/model/provider metadata, seed/order/state metadata, and explicit pair assertions to B4 output.
- [x] Add a standalone pairing audit that fails on missing/duplicate IDs, asymmetric scenario sets, or mismatched suite membership.
- [ ] Recompute the paired CI from the auditable map and mark the archived result as historical until the new contract is demonstrated.

### C. Artifact and reproduction surface

- [x] Correct all canonical appendix artifact paths to resolve from the repository root.
- [ ] Add a machine-readable release manifest with source/artifact hashes, expected outputs, tool versions, and offline/provider requirements.
- [x] Add one command that validates path resolution, hashes, claim-source mappings, and offline replay prerequisites.
- [ ] Remove the repository-link omission from the paper's artifact statement when a stable release locator exists; otherwise state the exact local artifact boundary.

### D. Channel-specific evaluation claims

- [x] Make analysis-channel, raw served-text, both-channel, and echo-guarded metrics distinct in every canonical headline table/caption/contribution.
- [x] Replace unsupported “independent campaign” language with provenance-backed wording in the canonical S&P source.
- [x] Recast the unguarded +.154 value as archived model-coherent analysis evidence and do not call it clean served capability.

### E. Quality and baseline evidence

- [ ] Prepare and execute the independent judge-model sensitivity protocol, or demote the current 3.86/5 result to an internal diagnostic.
- [ ] Prepare the blinded human-rater package: rubric, sampling, consent, anonymization, agreement statistics, and adjudication rules.
- [ ] Add a related-work/baseline matrix for recent generative honeypots, runtime enforcement, RAG/prompt-injection defenses, and verifier approaches; narrow claims where direct comparison is unavailable.

### F. Deployment and adaptive evaluation

- [x] Finish the provider-free adaptive/rescue interpretation and keep it explicitly self-consistency only.
- [ ] Prepare a VPS deployment package with isolation, no real secrets, controlled egress, tailnet/private access first, rate limits, snapshot/rollback, and logs.
- [ ] Run the VPS field protocol only after local smoke gates and authorization are confirmed; measure multi-turn goals, attacker traffic, fallback/retry rates, cost, latency tails, and operational utility.

### G. Manuscript hygiene and final gates

- [x] Remove stale CI/type-check claims from the extended companion or label them historical.
- [x] Rebuild the canonical S&P manuscript from active sources, render and inspect at final size, and verify the PDF separately from the extended companion.
- [x] Run focused tests, static checks on changed files, path audit, paper diagnostics, and final claim search for the canonical surface.
- [x] Update the release decision with one status per workstream and an explicit residual-blocker list.

## Delegation lanes

1. **OpenCode lane 1, `opencode/fledge-alpha-free`:** implement B4 provenance metadata, pair assertions, pairing-audit script, and focused tests. Touch only B4 scripts/tests and a new audit artifact if needed.
2. **OpenCode lane 2, `opencode/fledge-alpha-free`:** create the threat-model/claim-boundary matrix and local artifact-path/manifest validation scaffold. Touch only new docs/scripts/tests; do not edit the paper or existing result JSON in this lane.
3. **Main agent:** integrate and review delegated changes, revise canonical paper sources, execute builds/tests, and handle external-dependency handoffs.

## Stop conditions

- Stop and report if a change would delete user data, publish an external service, expose secrets, or require credentials/authorization not present in the workspace.
- Do not claim `SUBMISSION-READY` while VPS/provider/human-evaluation work remains `BLOCKED-EXTERNAL` unless the paper explicitly narrows its claims so those experiments are no longer required.

## Current execution status (2026-10-08)

- `CLOSED-LOCAL`: threat-model matrix and canonical short-paper integration;
  B4 pair contract and audit CLI; artifact-path validator and corrected
  appendix paths; channel-specific claim wording; provider-free rescue
  nonclaim wording; stale companion CI wording; fresh 27-page companion and
  12-page S&P builds; `1622 passed, 116 skipped, 0 failed`; 23 focused
  remediation tests; changed-file Ruff and diff checks.
- `BLOCKED-EXTERNAL`: fresh provider-backed B4/live rerun because the requested
  models are absent from the observed catalog and quota is unprobed;
  independent human/judge-model quality validation; independently constructed
  adaptive attacks; stronger direct baselines requiring literature/replication
  work; authorized VPS/ambient-traffic deployment.
- Release state remains `AUDIT-DRAFT-ONLY`, not `SUBMISSION-READY`.
