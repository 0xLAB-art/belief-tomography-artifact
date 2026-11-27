# Reference 169 APMIX Run Validation Report

## Verdict

`REFERENCE 169 RUN COMPLETE — SINGLE-MODEL INTEGRITY VERIFIED`

The completed run used APMIX at `https://api.apmix.ai/v1` with the fixed model `claude-sonnet-4-6-free`. All three primary whole-packet responses exposed the same model, parsed to 169 unique cases, and passed the frozen taxonomy/schema checks.

## Scope and provenance

- Planned cases: **169**
- Completed primary passes: **3 x 169**
- Adjudicator: **1**, same provider/model, applied only to the 53 non-exact primary cases
- Provider/model switches: **none**
- Old annotations mixed into this run: **no**
- Automatic retries: **none**
- Request timeout: **900 seconds**
- Credential material detected in retained outputs: **no**
- First-response preflight: **REFERENCE_ANNOTATION_PREFLIGHT_OK**

The driver’s actual execution unit was a whole packet, not 169 separate HTTP requests. The retained raw API responses are the three `RAW_API_RESPONSE.txt` files listed in the manifest. This report does not relabel that design as per-case HTTP execution.

## Integrity checks

| Check | Result |
|---|---|
| Expected IDs | 169 |
| Unique IDs per primary pass | 169, 169, 169 |
| Required fields | pass for all primary rows |
| Allowed taxonomy | pass |
| Non-empty rationales | pass |
| Provider response model | `claude-sonnet-4-6-free` for all primary passes |
| Parsed-output hashes | pass |
| JSON-fence handling | accepted by parser in all three responses |
| Credential leakage scan | none detected |
| Silent fallback | none detected |

## Final reference distribution

```text
{"BENIGN": 80, "DATA_ACCESS": 13, "EXPLOITATION": 5, "OTHER_ATTACK": 6, "PERSISTENCE": 5, "PRIVILEGE_ESCALATION": 5, "RECON": 51, "UNCERTAIN": 4}
```

- Exact 3/3 primary agreement: 116/169
- Adjudicated cases: 53
- Resolved concrete labels: 165
- UNCERTAIN: 4
- Binary evaluable: 165
- Multiclass Fleiss kappa: 0.6521288938235258
- Binary Fleiss kappa on jointly eligible cases: 0.6661677139191367

## Failure ledger

`REFERENCE_169_FAILURES.jsonl` is empty. No provider HTTP error, rate limit, timeout, empty response, refusal, invalid JSON, schema-invalid response, or parser error was retained in this completed run.

## Reproducibility

The exact driver, packet, prompt-file, raw-response, parsed-output, runtime, adjudication, and manifest hashes are in `REFERENCE_169_RUN_MANIFEST.json`. The API credential is intentionally absent from all artifacts.
