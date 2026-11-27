# RAGIN AWS Live Recovery — Execution Handoff

Execution date UTC: 2026-10-11

---

## 1. What succeeded

- Recovered authorized AWS access from the existing AWS CLI/SSO refresh flow.
- Confirmed STS identity: assumed-role session in account REDACTED_ACCOUNT, region eu-north-1.
- Performed live read-only inventory for:
  - EC2 CORE and EDGE
  - VPC, subnets, route tables, IGW
  - Security groups (inbound and egress)
  - EC2 Instance Connect Endpoint, ENI, and management SG
  - Volumes, NACLs, VPC endpoints, Flow Logs, egress-only IGW
  - SSM instance information and live SSM command execution
  - Cost Explorer daily unblended cost for the recent window
- Ran bounded live SSM probes on CORE and EDGE, including:
  - process and listener inventory
  - certificate metadata (public attributes and fingerprints only; no keys exported)
  - env redaction of secret-bearing keys
  - Cowrie config listing with sensitive lines redacted
  - CORE loopback OpenSSL probe to confirm listener binding behavior

Evidence stored under:
- `docs/aws_live_recovery/evidence/`

---

## 2. What is verified as current state

- CORE: running, public IPv4, public subnet, main route table with IGW default route, `172.31.17.217:8443` listener, mTLS required, allowed identity `spiffe://ragin/edge`, provider models disabled-local-provider in env.
- EDGE: running, public IPv4, public subnet, Cowrie running, socat OpenSSL chain configured to CORE, client cert identity `CN=RAGIN-EDGE` / `URI:spiffe://ragin/edge`.
- Private subnet: exists, private, local-only route table exists and is associated to it.
- EIC endpoint: exists in the private subnet with the private route table, DNS name available, management SG permitting SSH to CORE/EDGE.
- Both root volumes: unencrypted.
- Both SGs: all-protocol egress to `0.0.0.0/0`; CORE SG still has `tcp/8443 from 172.31.35.203/32` temporary staging rule.
- No VPC endpoints, no Flow Logs, no configured durable protected audit verified.

---

## 3. What failed or was inconclusive this session

- CORE loopback OpenSSL probe to `127.0.0.1:8443` failed with connection refused, because the listener binds only to `172.31.17.217:8443`. This confirmed binding, not a live mTLS acceptance result.
- Live EDGE OpenSSL probe to CORE was not completed this session: the first script attempt hit a local shell substitution error before reaching OpenSSL.
- An earlier EDGE-side HTTPS probe used the wrong framework path `/ragin/v1/command` and returned `404: Not Found`. That result established HTTPS reachability but not the real application contract.
- Missing-client-cert and bad-CA negative probes did NOT demonstrate the expected TLS rejections this session.

Conclusion:
- LIVE_MTLS_PASS is not established this session.
- The current deployment posture is compatible with mTLS, but several acceptance gates remain PARTIAL/BLOCKED.

---

## 4. What remains blocked

- Live mTLS acceptance end-to-end:
  - Needs verified negative-case confirmation and a correct verifier-level application response for the real service contract from EDGE to CORE.
- Negative-case completion:
  - missing-client-cert rejection, untrusted-client rejection, wrong-service-identity rejection, and invalid/missing application auth must all be demonstrated before PASS.
- Private CORE placement:
  - desired and approval-ready, but not deployed.
- Encrypted root storage for CORE/EDGE:
  - desired and approval-ready, but not deployed.
- SSM survivability in a no-public-IP subnet:
  - not proven; must be verified or a different management path approved before cutover.
- Provider inference connectivity:
  - not in scope for the private CORE cutover; separate approval required if wanted.
- Egress containment, Flow Logs, durable protected audit:
  - approval-required.
- Public Cowrie or public honeypot activation:
  - not approved; blocked.
- Deletion of current CORE/EDGE resources:
  - not authorized.

---

## 5. Historical reconciliation completed

- Task 3.7 Python mTLS experiment on port 24443 and the 72-hour staging material on port 8443 are different runs; they are not merged.
- Current deployment is a separately verified state: CORE listener on `172.31.17.217:8443`, mTLS required, allowed identity `spiffe://ragin/edge`.
- Current staged certificate validity windows are short; any future reliance on these exact cert files must account for renewal/replacement.

---

## 6. Immediate next action

If the goal is to close live mTLS verification:
- Today's authorized probes reached the following state, recorded in `LIVE_MTLS_ACCEPTANCE_RESULTS.md`, `DEPLOYMENT_STATE_MATRIX.md`, `PRIVATE_CORE_COST_AND_APPROVAL.md`, and the corresponding evidence subtrees:
  - TLS verification from EDGE to CORE with `/etc/ragin/tls/edge.crt`, `/etc/ragin/tls/edge.key`, and `/etc/ragin/tls/ca.crt` succeeded.
  - A direct HTTPS application probe from EDGE to `https://172.31.17.217:8443/ragin/v1/command` reached CORE over mTLS with auth and returned `404: Not Found`.
  - The correct production app listener route is `POST /ragin/v2/session/command`, served from a single hardened control routeset on top of the hardened framework, not from the default framework routing layer.
  - A live positive HTTPS application probe on `POST /ragin/v2/session/command` reached CORE over mTLS with application auth and returned a verifier-controlled `TEMPLATE_FALLBACK_VERIFIED` response for a bounded benign echo command.
  - Raw SSM output, parsed probe summary, and event references are preserved under `docs/aws_live_recovery/evidence/phase3_positive/`.
  - Missing-client-cert and bad-CA negative probes did NOT demonstrate the expected TLS rejections this session.
- To move from PARTIAL to LIVE_MTLS_PASS, complete the missing negative-case demonstration for the current certificate versions and application contract, preserve raw results and correlation ids under `docs/aws_live_recovery/evidence/`, and read back that temporary test material is preserved only under the evidence path and not copied into the repository.

If the goal is to prepare the private CORE cutover:
- Obtain explicit approval on the PRIVATE_CORE_COST_AND_APPROVAL.md packet, especially the private management path choice and whether SSM interface endpoints are required.
- Before cutover, prove private-side management survives no-public-IP placement.

Do not start Task 4 and do not publicly activate Cowrie.

---

## 7. Evidence index

- Identity: `evidence/sts_caller_identity_*.json`
- EC2: `evidence/ec2_instances_*.txt`, `evidence/ec2_metadata_instanceprofile_*.txt`, `evidence/eni_*.txt`
- Volumes: `evidence/volumes_*.txt`
- VPC/subnets: `evidence/vpc_*.txt`, `evidence/subnets_*.txt`
- Route tables/IGW: `evidence/route_tables_*.txt`, `evidence/eigw_*.txt`
- NACLs: `evidence/nacls_*.txt`, `evidence/nacl_default_entries_*.txt`
- Security groups: `evidence/security_groups_inbound_*.json`, `evidence/security_groups_egress_*.json`, `evidence/eic_management_sg_*.json`
- EIC: `evidence/ec2-instance-connect-endpoint_*.json`, `evidence/ec2-instance-connect-endpoint_eni_*.txt`
- SSM instances: `evidence/ssm_instances_*.txt`
- SSM commands/outputs: `evidence/ssm_command_*.json`, `evidence/ssm_output_*.json`
- Cost: `evidence/ce_get_cost_and_usage_*.json`
- Flow logs/endpoints: `evidence/flow_logs_*.json`, `evidence/eigw_*.txt`

---

## 8. Safety summary

- No EC2/EBS/snapshot/KMS/endpoint/NAT created or modified this session.
- No private keys, API keys, provider credentials, or session tokens copied into the repository.
- No public exposure added.
- No Task 4 start and no public Cowrie activation.
- All mutations remain approval-gated.
