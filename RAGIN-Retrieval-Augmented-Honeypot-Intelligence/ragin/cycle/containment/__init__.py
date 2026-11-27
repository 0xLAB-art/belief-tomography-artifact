"""WS3 Security Containment — container egress, metadata isolation, protected audit.

Implemented as pure-Python, localhost-testable policy logic and helper utilities.
The Docker / host-level firewall / seccomp / read-only-fs / no-new-privileges
mechanisms are the OUT-OF-SCOPE platform enforcement described in the acceptance
packet; this module captures the app-level invariants those mechanisms must protect,
provides a local egress-guard the harness can consult, and proves (in tests) that
rejected/unverified model responses are never served.

Destructive firewall experiments are NOT run on production EC2; the module is
tested locally and through the existing harness/verifier contracts.
"""
