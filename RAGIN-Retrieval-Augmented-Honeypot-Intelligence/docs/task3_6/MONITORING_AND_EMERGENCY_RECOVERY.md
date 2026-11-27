# RAGIN Task 3.6: Monitoring and Emergency Recovery

## Current evidence

- Both EC2 instance and system status checks passed during final validation.
- SSM provides managed-node state and command/session evidence.
- UFW logging is active at low verbosity.
- No CloudWatch Agent is active.
- No VPC Flow Logs were configured in the inspected VPC.
- No configured CloudTrail trail was returned; CloudTrail Event History did record the approved IAM/EC2 API changes.
- No paid monitoring service or log destination was created.

## Emergency isolation runbook

1. From the independent AWS control plane, replace EDGE with a pre-reviewed quarantine SG that has no attacker ingress and preserves only the minimum recovery path, or stop public ingress at the existing dedicated SG.
2. Preserve CORE and collect protected audit evidence before any host shutdown.
3. Revoke the EDGE service certificate and remove its authorization from CORE.
4. Confirm EDGE public listeners and SG state are isolated, then retain the instance for evidence.
5. Recover operator access through Session Manager or the restricted SSH path.
6. Restore the last-known-good SG/certificate configuration only after review.

The runbook was not exercised against the live EDGE because it would change or interrupt the only public administrative path. It is therefore INCOMPLETE, not PASS. A non-destructive rehearsal should use a dedicated disposable test resource in a later approved window; no new instance was created here.
