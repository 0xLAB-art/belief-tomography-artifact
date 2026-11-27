# E19 — Seed extension (robustness wave)

Pre-registered: `docs/paper/belief_tomography/PREREGISTRATION_E18E19E20.md`. Registered protocols re-run unchanged, one seed per run, at extension seeds (131, 2026, 90210); each seed carries a genuine per-seed verdict. Registered artifacts preserved (snapshots: *.json.registered).

## run_e6_composition

| seed | local_components_certified | composition_breaches | negative_control_clean | E6_H1_supported |
|---|---|---|---|---|
| 2718 (registered run) | True | True | True | True |
| 99001 (registered run) | True | True | True | True |
| 131 (ext) | True | True | True | True |
| 2026 (ext) | True | True | True | True |
| 90210 (ext) | True | True | True | True |

- Extension verdict: **ALL CONDITIONS HOLD**

## run_e7_gaming

| seed | public_accepts_probe_aware | held_rejects_probe_aware | gamma_exceeds_floor | controls_gamma_within_floor | E7_H1_supported |
|---|---|---|---|---|---|
| 2718 (registered run) | True | True | True | True | True |
| 99001 (registered run) | True | True | True | True | True |
| 131 (ext) | True | True | True | True | True |
| 2026 (ext) | True | True | True | True | True |
| 90210 (ext) | True | True | True | True | True |

- Extension verdict: **ALL CONDITIONS HOLD**

## run_e9_forgery

| seed | shaping_conditions | honest_control | E9_H1_supported |
|---|---|---|---|
| 2718 (registered run) | True | True | True |
| 99001 (registered run) | True | True | True |
| 131 (ext) | True | True | True |
| 2026 (ext) | True | True | True |
| 90210 (ext) | True | True | True |

- Extension verdict: **ALL CONDITIONS HOLD**

## run_e10_adaptive

| seed | meta_passes_published | meta_breaches_secret | control_detected | secret_defense_detects_meta | E10_H1_supported |
|---|---|---|---|---|---|
| 2718 (registered run) | True | True | True | True | True |
| 99001 (registered run) | True | True | True | True | True |
| 131 (ext) | True | True | True | True | True |
| 2026 (ext) | True | True | True | True | True |
| 90210 (ext) | True | True | True | True | True |

- Extension verdict: **ALL CONDITIONS HOLD**

## Secondary (E15/E16)

E15's release endpoints are exact for deterministic allocations and E16's closed form is validated by MC at the registered seed; a MC re-seed does not change any analytic endpoint. No extension required by the registration.

## Combined verdict

**Seed-robust: True** — every registered condition of E6/E7/E9/E10 holds at all three extension seeds (131, 2026, 90210).

