# Laya optional assessment — real-inference status

## Objective

Decide whether the optional Laya-style assessment adapter should be run with real inference during the next stage, or remain as an adapter-only contract until reachability, time, and approval conditions are met.

## Current decision posture

This document records an **in-progress status**, not a completion claim.

- **Adapter contract:** reviewed as present in source.
- **Local unit contracts:** verified by direct file import in this environment without installing the full application dependency set.
- **Real inference from this host at this moment:** not completed and not asserted as completed.

## What is real from this host moment

### Verified locally

- The adapter module exists in the codebase and exposes a well-bounded `assess` contract with explicit timeout, state-size bounding, and typed failure paths.
- Local unit-style checks for the adapter contract passed when probed directly, including:
  - successful typed SIGNAL path from a fixture inference callable
  - provider-failure path returning `NO_SIGNAL`
  - provider-timeout path returning `NO_SIGNAL`
- The adapter is designed to treat inference as **outside the authority of the deterministic verifier**. It is an optional, non-authoritative assessment signal.

### Not verified live from this host

- No live Laya inference endpoint reachable from this host was confirmed in this execution environment.
- No real inference run producing a live assessment artifact was completed from this host in this session.
- Any claim of live Laya assessment success is out of scope for this status doc until such evidence exists.

## Constraints that apply

- Optional assessment is not part of the core authoritative serving decision.
- It must not be allowed to weaken the deterministic verification gate.
- If real inference requires credentials, egress, or runtime access that are not available from this host at this moment, the branch must stop for that reason and not be forced through.

## Timebox and feasibility

The real-inference decision is intentionally timeboxed. It is also constrained by:

- reachability of any live inference provider from this host
- availability of suitable credentials/runtime if required
- whether the inference would materially change the next-stage acceptance picture
- whether forcing real inference would consume disproportionate time or cost relative to its decision value

If real inference is feasible and worth doing, it should be treated as a separate evidence-capture step with its own artifact, not as a label applied to this status doc.

## Adapter-only posture

When real inference is not feasible within the timebox or from the current host, the acceptable posture is:

- keep the adapter contract validated locally
- keep the optional-assessment decision surface documented
- do not present the system as having live Laya-based assessment capability from this host
- mark the remaining gap explicitly rather than silently

## Uncompleted items that would close this status

- confirmation of a reachable live inference provider from this host
- a successful real-inference run with preserved raw artifact
- a clear decision that the inference was worth the cost/time/approval it required
- explicit handling of any credential/egress/runtime dependency

## Namespace rule

This status doc is a next-stage record. It must not be relabeled as a completed live-inference proof, and it must not be merged into manuscript or prior sprint headline evidence without an explicit controlled reason.

## Current evidence gap

```
OPTIONAL_ASSESSMENT_STATUS: in_progress
Local_adapter_contract: verified_without_app_deps
Local_unit_style_checks: passed_for_fixture_signals_and_failure_paths
Real_inference_from_this_host: not_completed
Real_inference_gating: reachability_timeout_credentials_approval
```

## Next action

Either:

- start a real inference run only if a reachable provider and acceptable time/cost posture exist, and capture raw evidence separately, or
- keep this item as adapter-only and leave the gap explicitly documented rather than inferring a completed capability.
