# AWS Cost Ledger

Observed 2026-10-08 UTC. Amounts below are evidence boundaries, not a spending guarantee.

| Item | State | Cost note |
|---|---|---|
| Existing CORE and EDGE EC2 | running | Existing baseline; exact current credit balance is not exposed by the used CLI queries. |
| Prepared private subnet/route table | created earlier | No hourly service charge expected for these resource types. |
| EIC endpoint `eice-023d2c69cb6690c48` | created and `create-complete` | AWS documentation states no additional charge for the endpoint itself; cross-AZ data transfer may still apply. |
| EIC SG `sg-05f6e3f406f0c9be2` | created | Dedicated RAGIN resource; no standalone SG charge. |
| Docker/Cowrie staging | host-local | Uses existing EC2 capacity; image/package bandwidth and existing instance usage remain possible costs. |
| NAT, paid interface endpoint, LB, DB, replacement EC2, snapshot, extra volume | not created | No approval or budget allocation consumed. |

Cost Explorer returned `0 USD` daily unblended cost for the inspected 2026-10-01 through 2026-10-08 range. This does not prove remaining credit balance, delayed usage, or future cost is zero. Credit balance remains unverified.

The EIC endpoint is in CORE's AZ to avoid CORE management cross-AZ transfer. Testing EDGE through the same endpoint would cross AZs and was not required for the current acceptance. The bounded provider experiments used the reported free plan, consumed 13,300 provider tokens at the latest readback, and reported zero top-up remaining; this is provider-account usage, not an AWS-credit guarantee. No new AWS resource was created in this phase.

The 2026-10-09 refresh observed no additional RAGIN EC2, NAT Gateway, paid interface endpoint, load balancer, snapshot, or replacement volume. The local OpenCode/Cowrie test used no AWS resource and no AWS charge; its temporary workstation firewall rule and containers were removed. VPC Flow Logs were not observed. Both dedicated RAGIN security groups still have unrestricted outbound rules; narrowing them remains a separate controlled change because DNS, SSM, updates, application transport, and Docker forwarding must be tested together.

The corrected Cost Explorer query for 2026-10-02 through 2026-10-09 returned `0 USD` unblended cost for every day. This is a historical usage observation, not proof of remaining credits, delayed billing, or future zero cost.

The OpenCode provider benchmark and its temporary loopback bridge created no
AWS resource and no AWS charge. The benchmark was limited to one case per
suite and remains local staging evidence.
