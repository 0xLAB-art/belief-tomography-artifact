# Full regression results — status

## Objective

Record the regression posture for the next stage in a way that does not overclaim.

A full regression claim requires a working test runner environment and either a passed suite or an explicit listed failure set. This document currently records the status in this host moment, not a completed regression.

## Current regression status

- **Full pytest suite run from this host in this session:** not completed.
- **pytest in the environment used from this host in this session:** not present.
- **Regression claim made in this session:** none.

## What can be asserted locally

- Selected contracts were probed directly by importing the relevant source files and exercising narrow behaviors without installing the full application dependency set.
- Those local checks were used only to confirm that specific core behaviors appear to behave as designed in this host moment. They are not a substitute for the full suite.

## What is still gated

- A working test environment with the project's chosen test runner.
- The full suite execution.
- A clear pass/fail artifact that can be preserved and revisited.

Until those exist, any statement that the full regression passed or failed would be fabricated. The gap is therefore left explicit.

## Evidence required to close this status

- A reproducible way to run the project's full regression from a reachable environment.
- Either a passed suite report or an explicit failure list with preserved output.
- Clear separation between:
  - local contract probing
  - full suite regression
  - any live-end-to-end evidence that depends on reachable hosts

## Namespace rule

This status file is a next-stage record. It must not be relabeled as a completed regression report, and it must not be merged into manuscript or prior sprint headline evidence without an explicit controlled reason.

## Current evidence gap

```
REGRESSION_STATUS: not_completed_from_this_host
Full_suite_run: absent
Project_test_runner_in_env: absent
Local_contract_probing_only: present
Regression_claim_made: none
```

## Next action

Either:

- stand up or access a working test environment that can run the full suite, then record the real outcome here with preserved output, or
- keep this item as an explicit gap and do not assert a completed regression from this host.
