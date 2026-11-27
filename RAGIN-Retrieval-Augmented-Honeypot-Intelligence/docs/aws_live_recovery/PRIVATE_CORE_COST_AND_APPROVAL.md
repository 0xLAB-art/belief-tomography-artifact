# RAGIN AWS Live Recovery — Private CORE Cost and Approval

Status: approval packet prepared from live inventory. No migration executed.

---

## 1. Preferred target architecture

Reuse the infrastructure that already exists:
- Existing VPC: `vpc-044a70ed680faff8b`
- Existing private subnet: `subnet-07fae34b3db734bb2`
- Existing private route table: `rtb-04bf376f929483d4c`
- Existing EIC endpoint: `eice-023d2c69cb6690c48`
- Existing EIC management security group: `sg-05f6e3f406f0c9be2`

Target state for CORE:
- New or replacement instance placed in the private subnet
- No public IPv4
- Route table with only the VPC-local route
- Encrypted root storage
- mTLS listener bound to the private address
- Verified administrative access before data cutover
- Verified private EDGE-to-CORE service before production switchover
- Existing CORE retained for rollback through acceptance

---

## 2. What already exists and can be reused

Reused with no new resource:
- VPC
- Private subnet
- Private route table
- EIC endpoint and its ENI
- EIC management security group
- Operator SSH source identity `REDACTED_OPERATOR_HOST/32`
- SSM-managed role/profile already attached to both instances

Therefore Scenario A is strongly preferred.

---

## 3. Migration approach

1. Freeze writes; capture manifest and hashes of fiction state, audit state, configuration, and service artifacts.
2. Confirm or establish a private management path that survives loss of public routing. Candidates to evaluate before approval:
   - EIC endpoint for SSH management, plus private connectivity for SSM if SSM does not survive without internet routing in the private subnet; or
   - SSM interface endpoints for the required Systems Manager services, if SSM must remain the primary management path.
3. Build replacement CORE from a verified source:
   - preferred: an encrypted snapshot or encrypted AMI derived from the current verified CORE root, or
   - alternative: a new encrypted root launched from a verified base image with state restored from the frozen manifest.
4. Restore and hash-verify data; verify boot, SSM or chosen management path, SSH recovery via EIC, IMDSv2, host firewall, service certificates, and service identity.
5. Validate the private EDGE-to-CORE mTLS contract with the current authorized identity and negative cases before switching production traffic.
6. Cut over during a planned maintenance window; keep the old CORE and its volume intact through the rollback window.
7. Only after verified acceptance, make a separate retention/deletion decision for the old resources.

---

## 4. Cost scenarios

Pricing basis: official published AWS pricing for eu-north-1, checked at the time of this session from the configured AWS account’s Pricing API query and explicitly marked where not independently confirmed from a billable source.

Cost basis for this packet:
- `aws pricing get-products` was queried for EC2, EBS gp3, EBS snapshots, and the three Systems Manager interface endpoints in eu-north-1 from inside the RTX-enabled workspace.
- Items that returned usable pricing were recorded with price code, unit, term, and calculation.
- Items that did not return usable pricing were marked UNKNOWN rather than invented.
- No EC2 price quote, NAT Gateway quote, or private IPv4 quote was invented.

### Scenario A — minimum incremental cost using existing infrastructure

New or changed resources only:
- Replacement CORE instance: new EC2 usage for `m7i-flex.large` during overlap
- Encrypted root storage: new encrypted EBS gp3 for the replacement root
- Optional: encrypted snapshot or AMI storage for the migration source, if that path is chosen
- Temporary duplicate compute: overlap period where both old and new CORE exist
- Data transfer: in-VPC traffic between EDGE and new CORE; no internet transfer assumed in the private path

Verified pricing from `aws pricing get-products` in eu-north-1:
- `m7i-flex.large` On-Demand Linux usage, `EU-North-1-Linux` rate code:
  - Unit: `Hrs`
  - Base price: `0.0336` per hour
  - 6-hour overlap: `0.2016` USD
  - 24-hour overlap: `0.8064` USD
  - 72-hour overlap: `2.4192` USD
  - 30-day steady state: `24.192` USD
- gp3 root storage (40 GiB), `EU-North-1-VolumeUsage.gp3` rate code:
  - Unit: `GB-Mo`
  - Base price: `0.08` per GB-month
  - 40 GiB:
    - 6-hour overlap: `0.00584` USD
    - 24-hour overlap: `0.02304` USD
    - 72-hour overlap: `0.06912` USD
    - 30-day steady state: `3.20` USD
- gp2 root storage (40 GiB), `EU-North-1-VolumeUsage.gp2` rate code:
  - Unit: `GB-Mo`
  - Base price: `0.10` per GB-month
  - 40 GiB 30-day steady state: `4.00` USD

Calculated Scenario A items:
- EC2 `m7i-flex.large` On-Demand overlap calc: 6 hours = `0.202` USD, 24 hours = `0.806` USD, 72 hours = `2.419` USD.
- gp3 40 GiB overlap calc is negligible relative to the EC2 overlap: 6 hours ≈ `0.006` USD, 24 hours ≈ `0.023` USD, 72 hours ≈ `0.069` USD.
- gp3 steady-state monthly storage for the replacement root alone is `3.20` USD.
- gp2 steady-state monthly storage for the same 40 GiB would be `4.00` USD.

Approximate magnitude — Scenario A:
- These are order-of-magnitude planning figures including verified EC2 price and verified gp3 unit/gp3 base price, plus reconciliation notes for items that are NOT independently confirmed.
- For a short overlap plus replacement storage, the likely impact is a small one-time plus small recurring change.
- The dominant Scenario A number with verified pricing is the EC2 On-Demand overlap: `0.202` USD at 6 hours, `0.806` USD at 24 hours, `2.419` USD at 72 hours.

Scenario A items that remain UNKNOWN in this packet:
- AWS prices are region/currency-sensitive and can include taxes, credits, or pricing exclusions not captured here.
- EBS snapshot/AMI storage delta depends on the chosen migration source path.
- In-VPC data transfer cost basis is not itemized here.
- Any private IPv4, data-transfer, billing-credit, or tax impact is not quantified here.

Recurring cost decomposition — Scenario A:
- One-time migration expenses: primarily the overlap compute.
- Additional temporary costs: the overlap window plus whatever optional source snapshot/AMI storage is chosen.
- Steady-state monthly costs: replacement EC2 On-Demand plus encrypted root storage.
- Costs already being incurred: the current public CORE instance and its current storage are not removed in this packet; this is incremental to existing spend.

### Scenario B — additional managed connectivity only if required

Only if SSM or other management must remain available without internet routing:
- SSM interface endpoints for: `com.amazonaws.eu-north-1.ssm`, `com.amazonaws.eu-north-1.ssmmessages`, `com.amazonaws.eu-north-1.ec2messages`
- Endpoint charges: hourly per endpoint/AZ plus data processing; these are recurring and should be cost-checked before creation
- Endpoint security groups restricted to the management path

Verified pricing from `aws pricing get-products` in eu-north-1:
- SSM interface endpoint, `EU-North-1-InterfaceEndpoint` rate code:
  - Unit: `Hrs`
  - Base price: `0.01` per hour
  - Per endpoint per 30 days: `7.30` USD
- SSM messages endpoint, `EU-North-1-InterfaceEndpointMessages` rate code:
  - Unit: `Hrs`
  - Base price: `0.01` per hour
  - Per endpoint per 30 days: `7.30` USD
- EC2 Messages endpoint, `EU-North-1-InterfaceEndpointEc2Messages` rate code:
  - Unit: `Hrs`
  - Base price: `0.01` per hour
  - Per endpoint per 30 days: `7.30` USD
- Each endpoint is hourly per AZ, so three-endpoint single-AZ monthly cost is approximately `21.90` USD.

Calculated Scenario B items:
- If SSM must remain the primary management path in a no-public-route CORE, the recurring cost of the three Systems Manager interface endpoints in eu-north-1 is approximately `21.90` USD/month total for one AZ.
- This is the lowest realistic recurring estimate for that path; additional AZ redundancy or data-processing would increase it.

Approximate magnitude — Scenario B:
- If approved, Scenario B adds a recurring cost that is materially larger than Scenario A’s compute/storage baseline, because three endpoint-hours are charged every hour.
- Treat `21.90` USD/month as the verified endpoint-hours estimate only, not as a complete management cost.

Scenario B items that remain UNKNOWN in this packet:
- Interface endpoint data processing unit price and usage were not itemized here.
- Multi-AZ endpoint placement would multiply the hourly cost.

Why not default:
- SSM interface endpoints add recurring charges and are only justified if the chosen management path requires them.
- If SSH via EIC plus a separate verified SSM egress design is acceptable, Scenario A can be used without endpoints.

NAT Gateway:
- Do not use a NAT Gateway as the default.
- NAT Gateway adds hourly plus data-processing charges and is a poor fit for a credit-constrained account unless explicitly approved.
- This packet did not obtain a verified NAT Gateway price quote, so any NAT Gateway estimate is UNKNOWN and must not be presented as a number.

---

## 5. Management path analysis

Critical issue:
- The private route table has only the VPC-local route.
- That route alone does not provide internet access and does not guarantee SSM or provider connectivity.

EIC endpoint:
- Provides SSH/EC2 Instance Connect management into a private instance from the operator path.
- Is the strongest existing private management path already in place.
- Is not an inference transport and does not replace provider connectivity design.

SSM:
- Currently Online because both instances currently have public-SG-based reachability and the main route table’s IGW route.
- If CORE is moved to the private subnet with only the local route, SSM reachability may be lost unless private connectivity exists.

Recommended verification before any cutover:
- Prove private-side SSM reachability in a no-public-IP test configuration, or
- Prove that EIC SSH is sufficient and acceptable as the primary management path for the replacement, or
- Approve SSM interface endpoints if SSM must be the primary path.

Do not assume SSM survives private placement.

---

## 6. Provider inference connectivity analysis

Current deployment shows:
- CORE env: `RAGIN_LLM_BASE_URL=http://127.0.0.1:9`, `GATEWAY_URL=http://127.0.0.1:9`, `RAGIN_DON_MODEL=disabled-local-provider`, `RAGIN_HISOKA_MODEL=disabled-local-provider`
- This indicates CORE is currently provider-disabled-local in this session’s view, not provider-backed live generation.

Migration implication:
- Moving CORE to a private subnet does not solve provider connectivity by itself.
- If future production wants provider-backed generation, a separate private provider-transport design is required and must be approved separately.
- This cutover should not be treated as providing provider connectivity.

---

## 7. Downtime and rollback

Downtime estimate after prerequisites are ready:
- Approximately 30 to 90 minutes of maintenance-window work for cutover and validation, subject to restore and validation time.
- Endpoint, image, and management-path preparation are additional lead time before cutover.

Rollback:
- Keep the existing CORE instance and its current root volume intact through the rollback acceptance window.
- If health, data hashes, SSM/EIC management, mTLS, or application startup checks fail, stop the cutover and direct operations back to the existing CORE.
- Termination is not part of the first rollback window.

---

## 8. Approval requirements

Approval is required before any of the following:
1. Creating a replacement CORE instance in the private subnet without a public IPv4.
2. Creating encrypted replacement storage, an encrypted snapshot, or an encrypted AMI for migration.
3. Establishing or proving the chosen private management path, including SSM interface endpoints if selected.
4. Changing the EDGE-to-CORE service rule to the replacement private identity/address.
5. Executing the cutover maintenance window.
6. Any later deletion of the old CORE or its volume.
7. Any later provider-transport or public-deception changes.

Approval is NOT required for this document, for read-only inventory, or for bounded non-destructive SSM probes.

---

## 9. Smallest exact approval packet

Ask the approver for explicit yes/no on:
- Reuse of existing VPC, private subnet, private route table, and EIC endpoint for the replacement.
- Choice of private management path:
  - EIC SSH only, or
  - SSM interface endpoints, or
  - another approved private management design.
- Replacement instance type and root storage size/encryption.
- Migration source: encrypted snapshot/AMI from current verified CORE root, or new encrypted root with manifest restore.
- Maintenance window duration and rollback acceptance criteria.
- Whether provider-backed generation is in scope now or later.

Do not proceed without that explicit approval.
