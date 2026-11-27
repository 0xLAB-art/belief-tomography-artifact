# RAGIN AWS Live Recovery — Current Inventory

Status: live read-only inventory completed from authorized AWS session.
Session identity: `arn:aws:sts::REDACTED_ACCOUNT:assumed-role/AccountFullAccessRole/...` (account id redacted in shared text; raw STS response preserved under evidence).
Region: `eu-north-1`
Inventory timestamp UTC: 2026-10-11T14:29–14:57Z range across calls.

---

## 1. AWS access

- AWS CLI: `aws-cli/2.37.10` Python/3.14.6
- Config: `~/.aws/config` default profile with `region = eu-north-1`
- Credentials: assumed-role session; no static access keys present in environment
- Reauth: `aws login --profile default` was used to refresh the expired session
- STS identity confirmed: `sts get-caller-identity` succeeded
- Credential cache: no reusable SSO cache directory present after reauth
- SSM document run: `AWS-RunShellScript` reachable
- EC2 read access: confirmed
- Cost Explorer read access: confirmed

Evidence:
- `evidence/sts_caller_identity_20261011T142912Z.json`

---

## 2. EC2 — CORE

- Instance ID: `i-062a400b300f4f9e4`
- State: `running`
- Type: `m7i-flex.large`
- AZ: `eu-north-1a`
- Private IPv4: `172.31.17.217`
- Public IPv4: `REDACTED_FLEET_HOST`
- Subnet: `subnet-0f8d7698fde97f83b`
- VPC: `vpc-044a70ed680faff8b`
- Primary ENI: `eni-01b8030cd6c9e377d`
- ENI private IP: `172.31.17.217`
- ENI associated public IP: `REDACTED_FLEET_HOST`
- Source/dest check: enabled
- Attach time: `2026-10-08T17:13:13+00:00`
- Security group: `sg-03486d70769d21e4e` (`launch-wizard-3`)
- IMDSv2: `HttpTokens` not reported as enforced in this inventory call; SSM profile present
- Instance profile: `arn:aws:iam::REDACTED_ACCOUNT:instance-profile/RAGIN-SSM-ManagedProfile`
- Tags: `Name=RAGIN-CORE`

SSM:
- SSM managed instance: Online
- Last ping: `2026-10-11T17:46:35.523000+03:00`
- SSM command test: `CORE_SSM_OK`, hostname `ip-172-31-17-217`, user `root`

Live application inventory from SSM:
- Running: `python3 -m ragin.server_v2 --mode pipeline` (pid 21453)
- Listener: `tcp 172.31.17.217:8443`
- Runtime env bind: `RAGIN_BIND_HOST=172.31.17.217`, `PORT=8443`
- mTLS env: `RAGIN_MTLS_REQUIRED=1`, `RAGIN_MTLS_CERT_FILE=/run/ragin/tls/server.crt`, `RAGIN_MTLS_KEY_FILE=/run/ragin/tls/server.key`, `RAGIN_MTLS_CA_FILE=/run/ragin/tls/ca.crt`, `RAGIN_MTLS_ALLOWED_IDENTITIES=spiffe://ragin/edge`
- Auth env: `RAGIN_REQUIRE_AUTH=1`
- Max request bytes: `RAGIN_MAX_REQUEST_BYTES=1048576`
- Provider config: `RAGIN_LLM_BASE_URL=http://127.0.0.1:9`, `GATEWAY_URL=http://127.0.0.1:9`, `RAGIN_DON_MODEL=disabled-local-provider`, `RAGIN_HISOKA_MODEL=disabled-local-provider`, `OPENROUTER_API_KEY=` (empty)
- Field export dir: `RAGIN_FIELD_EXPORT_DIR=/app/data/field/ragin`
- Host fiction path: `/app/data/host_fiction.json`
- Host fiction policy: `per_session`

Config and TLS layout:
- `/etc/ragin/server.env`
- `/etc/ragin/tls/ca.crt`
- `/etc/ragin/tls/server.crt`
- `/etc/ragin/tls/server.key`
- Runtime TLS copy dir `/run/ragin/tls` not present in inventory call when queried separately

Installed crypto tooling:
- `openssl 3.5.5-1ubuntu3.7`
- `python3-openssl 25.3.0-1ubuntu1`
- `libssl3t64 3.5.5-1ubuntu3.7`

Evidence:
- `evidence/ssm_output_core_app_inventory_*.json`
- `evidence/ssm_output_core_listen_bind_*.json`
- `evidence/ssm_output_core_cert_inventory_*.json`
- `evidence/ssm_output_core_ssl_inventory_*.json`
- `evidence/ssm_output_core_runtime_cert_inventory_*.json`

---

## 3. EC2 — EDGE

- Instance ID: `i-05bc6aab0bd4260a7`
- State: `running`
- Type: `t3.micro`
- AZ: `eu-north-1b`
- Private IPv4: `172.31.35.203`
- Public IPv4: `REDACTED_FLEET_HOST`
- Subnet: `subnet-04d02e21747154d7a`
- VPC: `vpc-044a70ed680faff8b`
- Primary ENI: `eni-05e4944a0b96a8fa0`
- ENI private IP: `172.31.35.203`
- ENI associated public IP: `REDACTED_FLEET_HOST`
- Source/dest check: enabled
- Attach time: `2026-10-08T17:16:44+00:00`
- Security group: `sg-077b8f78668f4f646` (`launch-wizard-4`)
- Instance profile: `arn:aws:iam::REDACTED_ACCOUNT:instance-profile/RAGIN-SSM-ManagedProfile`
- Tags: none shown

SSM:
- SSM managed instance: Online
- Last ping: `2026-10-11T17:46:17.112000+03:00`
- SSM command test: `EDGE_SSM_OK`, hostname `ip-172-31-35-203`, user `root`

Live application inventory from SSM:
- Processes:
  - `twistd` running `/cowrie/cowrie-env/bin/python3 /cowrie/cowrie-env/bin/twistd ... cowrie`
  - `socat TCP-LISTEN:2222,bind=127.0.0.1,reuseaddr,fork TCP:172.29.0.2:2222`
  - `socat TCP-LISTEN:18083,bind=172.29.0.1,reuseaddr,fork OPENSSL:172.31.17.217:8443,cert=/etc/ragin/tls/edge.crt,key=/etc/ragin/tls/edge.key,cafile=/etc/ragin/tls/ca.crt,verify=1,commonname=172.31.17.217`
- Listeners:
  - `127.0.0.1:2222` socat
  - `172.29.0.1:18083` socat -> `OPENSSL:172.31.17.217:8443`
  - `0.0.0.0:22` sshd
- No `server_v2` process observed on EDGE

Config and TLS layout:
- `/etc/ragin/api.key`
- `/etc/ragin/cowrie.cfg`
- `/etc/ragin/tls/ca.crt`
- `/etc/ragin/tls/edge.crt`
- `/etc/ragin/tls/edge.key`

Cowrie config (redacted for secrets):
- `[honeypot]` hostname = `svr04`, backend = `llm`
- `[ssh]` version = `SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.4`, listen endpoints `tcp:2222:interface=0.0.0.0`
- `[llm]` host = `http://172.29.0.1:18083`, path = `/v1/chat/completions`, model = `ragin-pipeline`, debug = `false`
- `[output_jsonlog]` enabled = `true`, logfile = `/cowrie/cowrie-git/var/log/cowrie/cowrie.json`
- Sensitive lines redacted in evidence

api.key metadata (no value printed):
- path: `/etc/ragin/api.key`
- size: 65 bytes
- sha256: `0486a8b0fd516c2e4a10bf601aad534c7cb3e3c89cc65955b1f3cab3c8fa66dc`
- content length: 65 bytes
- head/tail hex sample preserved in evidence

EDGE certificate metadata (public only):
- CA: `CN=RAGIN Sprint Staging CA`, self-signed, AKI present, validity `Oct 8 20:13:49 2026 GMT` to `Oct 11 20:13:49 2026 GMT`
- EDGE leaf: `CN=RAGIN-EDGE`, issuer `CN=RAGIN Sprint Staging CA`, AKI present, EKU `TLS Web Client Authentication`, SAN `URI:spiffe://ragin/edge`, validity `Oct 8 20:13:50 2026 GMT` to `Oct 11 20:13:50 2026 GMT`
- Fingerprints and sizes preserved in evidence; no keys exported

Evidence:
- `evidence/ssm_output_edge_cert_inventory_*.json`
- `evidence/ssm_output_edge_apikey_meta_*.json`
- `evidence/ssm_output_edge_cowrie_cfg_*.json`
- `evidence/ssm_output_edge_cowrie_cfg_content_*.json`
- `evidence/ssm_output_edge_final_*.json`

---

## 4. VPC

- VPC: `vpc-044a70ed680faff8b`
- CIDR: `172.31.0.0/16`
- Default VPC: yes
- DHCP options: `dopt-0b2f43258c652793d`
- Tenancy: default

Subnets:
- `subnet-04d02e21747154d7a` — `172.31.32.0/20`, `eu-north-1b`, public (`MapPublicIpOnLaunch=true`), default-for-az=true
- `subnet-07fae34b3db734bb2` — `172.31.48.0/20`, `eu-north-1a`, private (`MapPublicIpOnLaunch=false`), default-for-az=false
- `subnet-0e83eebe69c0514a4` — `172.31.0.0/20`, `eu-north-1c`, public
- `subnet-0f8d7698fde97f83b` — `172.31.16.0/20`, `eu-north-1a`, public

Evidence:
- `evidence/vpc_*.txt`
- `evidence/subnets_*.txt`

---

## 5. Route tables and internet gateway

Route tables:
- `rtb-04bf376f929483d4c` — `RAGIN-CORE-PRIVATE-RT`
  - Associated: `subnet-07fae34b3db734bb2`
  - Route: `172.31.0.0/16 -> local`
  - No `0.0.0.0/0` route
  - Tags: `Project=RAGIN`, `Sprint=72h-2026-10-08`, `Name=RAGIN-CORE-PRIVATE-RT`, `Purpose=CORE-private-target`
- `rtb-0fb03d7badfcc25c6` — main route table
  - Associated: main
  - Routes:
    - `172.31.0.0/16 -> local`
    - `0.0.0.0/0 -> igw-0168696c5dc43baee`

Internet gateway:
- `igw-0168696c5dc43baee` attached to VPC

Interpretation:
- The private subnet exists and is associated with a local-only route table.
- CORE is still in the public subnet `subnet-0f8d7698fde97f83b`, which maps public IPs and uses the main route table with a direct IGW default route.
- The existing private subnet is suitable as the CORE private target subnet; the existing private route table is suitable as the CORE private route table.

Evidence:
- `evidence/route_tables_*.txt`

---

## 6. Network ACLs

- Default NACL: `acl-0f6784f313451212c`
- Rules: allow-all inbound and outbound (rule 100 allow, 32767 deny), egress and inbound, IPv4
- No custom restrictive NACL observed in this inventory

Evidence:
- `evidence/nacls_*.txt`
- `evidence/nacl_default_entries_*.txt`

---

## 7. Security groups

CORE SG `sg-03486d70769d21e4e` (`launch-wizard-3`):
- Inbound:
  - `tcp/22` from `sg-05f6e3f406f0c9be2` (description: `RAGIN EIC private management`)
  - `tcp/22` from `REDACTED_OPERATOR_HOST/32`
  - `tcp/8443` from `172.31.35.203/32` (description: `RAGIN-EDGE temporary mTLS staging`)
- Egress:
  - all protocols `-1` to `0.0.0.0/0`

EDGE SG `sg-077b8f78668f4f646` (`launch-wizard-4`):
- Inbound:
  - `tcp/22` from `sg-05f6e3f406f0c9be2` (description: `RAGIN EIC private management`)
  - `tcp/22` from `REDACTED_OPERATOR_HOST/32`
- Egress:
  - all protocols `-1` to `0.0.0.0/0`

EIC management SG `sg-05f6e3f406f0c9be2` (`RAGIN-EIC-MGMT-20261008`):
- Inbound: none
- Egress:
  - `tcp/22` to `sg-03486d70769d21e4e` (description: `RAGIN CORE SSH via EIC`)
  - `tcp/22` to `sg-077b8f78668f4f646` (description: `RAGIN EDGE SSH via EIC`)

Evidence:
- `evidence/security_groups_inbound_*.json`
- `evidence/security_groups_egress_*.json`
- `evidence/eic_management_sg_*.json`

---

## 8. EC2 Instance Connect Endpoint

- ID: `eice-023d2c69cb6690c48`
- State: `create-complete`
- VPC: `vpc-044a70ed680faff8b`
- Subnet: `subnet-07fae34b3db734bb2`
- AZ: `eu-north-1a`
- ENI: `eni-097341d0d05830cbe`
- Security groups: `sg-05f6e3f406f0c9be2`
- DNS name: `eice-023d2c69cb6690c48.e2e0f8c3.ec2-instance-connect-endpoint.eu-north-1.amazonaws.com`
- DnsSupport: true
- PreserveClientIp: false
- Created: `2026-10-08T20:20:45+00:00`
- Tags: `Project=RAGIN`, `Purpose=private-management`, `Sprint=72h-2026-10-08`, `Name=RAGIN-EIC-MGMT`

Interpretation:
- The endpoint exists and is in the private subnet with the private route table.
- It is an SSH/EC2 Instance Connect management path, not an inference transport.
- It does not by itself provide SSM or provider inference connectivity from CORE.

Evidence:
- `evidence/ec2-instance-connect-endpoint_*.json`
- `evidence/ec2-instance-connect-endpoint_eni_*.txt`

---

## 9. Storage

CORE root:
- Volume: `vol-0537ee06e67f63cc5`
- Size: 40 GiB
- Encrypted: `False`
- State: `in-use`
- Device: `/dev/sda1`
- KMS key: none reported

EDGE root:
- Volume: `vol-05925e722a36cd345`
- Size: 20 GiB
- Encrypted: `False`
- State: `in-use`
- Device: `/dev/sda1`
- KMS key: none reported

Evidence:
- `evidence/volumes_*.txt`

---

## 10. VPC endpoints, Flow Logs, Egress-Only IGW

- VPC endpoints: none observed in VPC
- Flow Logs: none observed for VPC
- Egress-only internet gateways: none observed in VPC

Evidence:
- `evidence/flow_logs_*.json`
- `evidence/eigw_*.txt`

---

## 11. Cost / billing

Cost Explorer:
- Daily unblended cost `0 USD` for 2026-09-28 through 2026-10-08
- 2026-10-09 and 2026-10-10: approximately `0.0000000058 USD` per day reported by Cost Explorer
- Estimated: true for returned rows

Notes:
- This is an observation, not a budget authorization.
- Marketplace catalog entitlement read was not usable in this session.
- AWS credits remaining were not confirmed by an authoritative read this session.

Evidence:
- `evidence/ce_get_cost_and_usage_*.json`

---

## 12. Current state conclusions

Verified current state:
- CORE and EDGE are running, SSM Online, reachable from the laptop via SSM.
- Private subnet and local-only route table already exist and are suitable for a private CORE placement.
- EIC endpoint already exists in that private subnet.
- CORE is still public: public IPv4, public subnet, main route table with IGW default route.
- CORE application listener exists and is bound to `172.31.17.217:8443` with mTLS required and allowed identity `spiffe://ragin/edge`.
- CORE currently runs with provider path disabled-local-provider.
- EDGE runs Cowrie + socat OpenSSL chain to CORE, using cert identity `CN=RAGIN-EDGE` / `URI:spiffe://ragin/edge`.
- Both root volumes remain unencrypted.
- Both security groups still have all-protocol egress to `0.0.0.0/0`.
- Temporary mTLS staging rule `tcp/8443 from 172.31.35.203/32` is present on the CORE security group.

Remaining concerns for cutover planning:
- The CORE SG temporary staging ingress rule is still present.
- SSM and provider connectivity from a no-public-IP CORE must be proven before cutover, not assumed.
- Private CORE placement still requires migration approval; it is not live today.
