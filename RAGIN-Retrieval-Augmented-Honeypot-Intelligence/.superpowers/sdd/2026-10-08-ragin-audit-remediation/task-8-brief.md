### Task 8: Close provider/catalog and reproduction blockers

**Files:**
- Review/update: `results/apmix_quota_status.json`, `results/apmix_probe_history.jsonl`, provider configuration/docs, `results/sp2027_rescue/README.md`
- Do not relabel: existing provider pilot outputs

**Interfaces:**
- Consumes: Task 4 evidence ledger and the recorded catalog drift/quota status.
- Produces: a reproducible provider status with a clear blocked/fallback-only decision and no unsupported provider comparison.

- [ ] **Step 1: Recheck catalog/quota only within authorized project scope.** Record timestamp, catalog response, requested model availability, quota probe result, and error/status codes.
- [ ] **Step 2: Keep the blocked branch explicit.** If requested models are absent or quota remains unprobed, mark provider-backed reruns blocked and retain the rescue benchmark as provider-free evidence only.
- [ ] **Step 3: If models become available, run a controlled smoke check first.** Verify model identity, endpoint, authentication state, response schema, rate limits, and one bounded sample before any campaign.
- [ ] **Step 4: Re-run provider experiments only after smoke verification.** Record exact model IDs, prompts/configuration, seed/session IDs, failures, fallback use, and raw-to-derived artifact links.
- [ ] **Step 5: Update claims and release status.** Provider-backed findings may enter the ledger only with complete provenance; otherwise the release report must state that provider evidence is unavailable.

**Pass condition:** The repository never treats an unavailable model, HTTP 404/unknown model, empty catalog, or fallback trace as a provider result.

