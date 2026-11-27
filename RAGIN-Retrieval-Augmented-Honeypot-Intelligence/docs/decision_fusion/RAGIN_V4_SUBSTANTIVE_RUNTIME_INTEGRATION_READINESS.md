# RAGIN V4 substantive runtime integration readiness

Classification: `SUBSTANTIVE_RUNTIME_EVALUATION_READY`

This is a synthetic development validation of the opt-in runtime integration. No HF-2024 holdout, historical result, model provider, AWS operation, network operation, or attacker command execution was used.

## Runtime path

The default `server_v2` mode remains `RAGIN_BASELINE`. The two explicit opt-in modes map to the existing V4 policy arms:

| Runtime mode | Existing policy arm |
|---|---|
| `RAGIN_BASELINE` | `RAGIN_BASELINE` |
| `RAGIN_V4_SUBSTANTIVE_DETERMINISTIC` | `RAGIN_V4_DETERMINISTIC` |
| `RAGIN_V4_SUBSTANTIVE_LOGISTIC` | `RAGIN_V4_LOGISTIC` |

The runtime sequence is now Chrollo -> Don evidence bundle -> existing V4 Evidence Gate and Policy -> versioned substantive Hisoka adapter -> mandatory verifier -> HITL gateway -> accepted-only fictional-state commit. The frozen strategy generator remains byte-identical to the authoritative implementation.

## Synthetic end-to-end result

Six strategies were exercised for three turns each through `Harness` with the actual mandatory `FictionConsistencyVerifier` and `ApprovalGateway`. Every accepted turn recorded valid evidence, the selected V4 strategy, generator version, action, before/proposed/after fictional-state hashes, verifier pass, automatic HITL approval, accepted commit, and served-response hash.

- 18/18 synthetic substantive turns passed verification.
- 18/18 received automatic approval; 0 human reviews were required in this low-risk fixture.
- 18/18 accepted-only fictional-state commits were observed.
- 18/18 had `attacker_command_executed = false`.
- State continuity held across all three turns of every strategy.
- Responses differed by strategy in their fictional behavior and state traces; no decorative strategy suffix was used.
- Malformed evidence produced a verified baseline fallback with no substantive generator state.
- Verifier rejection and HITL denial each produced no fictional-state commit.

The `expose_decoy_internal_topology` case is a synthetic strategy fixture passed through the same runtime seam and evidence gate. It does not imply that the unchanged V4 policy algorithms selected that strategy in the historical HF-2024 cohort.

## Strategy behavior

| Strategy | Observable runtime behavior | Committed fictional state |
|---|---|---|
| `maximize_recon_surface` | Stable fictional application path and service inventory | discovered paths/services |
| `fake_success_and_return_visits` | Stable successful fictional operation and follow-up status | completed operations |
| `steer_to_honeytoken_credentials` | Synthetic nonfunctional reference values and trace identifier | decoy credential references |
| `expose_decoy_internal_topology` | Stable fictional application/database/cache map | topology hosts/services |
| `contain_in_fiction_and_instrument` | Fiction-only resource and telemetry response | contained resources/events |
| `low_intensity_administration` | Narrow administrative status without extra bait | session visit count |
| baseline | Existing generator path | no substantive-generator state |

## Safety and limitations

The new adapter never executes the command string. It uses an explicit action allowlist, keeps state in immutable proposals, and calls the generator commit only after the Harness verifier and approval gateway both accept. Invalid evidence is routed to the existing baseline fallback. Runtime prompt binding and synthetic credential-label normalization occur at the adapter boundary so the authoritative generator and verifier remain unchanged.

The validation uses synthetic policy fixtures for complete six-strategy coverage. It is not an effectiveness experiment and does not evaluate policy correctness, deception quality, attacker engagement, or production deployment behavior. Logistic mode mapping is verified; no new logistic cohort was run. Full production HITL/operator interaction remains environment-dependent.

## Freeze

The complete per-turn trace records and SHA256 manifest are in `results/decision_fusion_v4/substantive_runtime_integration_v1/integration_validation_freeze_v1.json`. The authoritative generator SHA is `3c1e0c9f85510adc17758c4f4aded547c57fca8c7aa69fea209790315fdbdae2`.
