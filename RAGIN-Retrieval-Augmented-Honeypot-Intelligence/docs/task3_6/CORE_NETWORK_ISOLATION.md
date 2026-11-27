# RAGIN Task 3.6: CORE Network Isolation

## Current verified state

CORE remains in `subnet-0f8d7698fde97f83b` (`172.31.16.0/20`) with public-address mapping, public IPv4 `REDACTED_FLEET_HOST`, and the main route table's `0.0.0.0/0` route to the IGW. It is not private.

The dedicated CORE SG `sg-03486d70769d21e4e` permits only operator TCP/22 from `REDACTED_OPERATOR_HOST/32`; it has no application ingress. UFW also denies host incoming traffic except that SSH rule. Host listeners show only Ubuntu SSH and local resolver/time services; no RAGIN application listener was deployed.

## Interim boundary result

The public CORE attack surface is narrowed at AWS SG and host-firewall layers, but public-subnet placement and the public address remain P0 residual risks. A restrictive SG must not be described as private networking.

## Migration blocker

An EC2 primary ENI is subnet-bound. Moving CORE privately requires a staged replacement/restore or another disruptive cutover. This task did not create a subnet, route table, replacement instance, NAT gateway, endpoint, snapshot, or new storage. The existing CORE remains the rollback anchor.

## Required next branch

Verify or create a dedicated private subnet without an IGW default route, prepare encrypted state restore and authenticated EDGE-to-CORE transport, prove independent SSM/operator access, then cut over in an approved window. Do not remove CORE's public address or stop/replace the current instance until recovery is independently demonstrated.
