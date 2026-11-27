# Generator transport results — decision and contract

## Objective

Design and validate the smallest secure and reliable transport that permanently connects AWS CORE generation to the approved provider-backed generator, without adding permanent paid AWS infrastructure or weakening hardened security boundaries.

## Current limitation

- The OpenCode CLI bridge works on the local workstation.
- AWS CORE is not permanently connected to it.
- A live permanent private path is therefore a deployment task, not yet a completed live system from this host moment.

This document records the decision and the adapter contract so deployment can proceed once the access and approval gates are satisfied.

## Constraints

- No EC2 Instance Connect Endpoint used as a model-inference transport.
- No EDGE made into a general-purpose unrestricted proxy.
- No public exposure of the local OpenCode bridge.
- No weakening of hardened SSH forwarding rules merely to make a tunnel work.
- No attacker-facing Cowrie access to the operator workstation.
- No permanent paid AWS infrastructure unless explicitly approved.
- Least-privilege, authenticated, TLS-identity-constrained transport.
- Provider secrets do not leak into research reports, response bodies, or audit exports.

## Options considered

### 1. Authenticated private overlay over an existing permitted network path

- Best fit if a stable private path already exists and can carry the needed traffic with acceptable latency and failure handling.
- Requires working private reachability from AWS CORE to the generator side.
- Authentication and TLS identity still required on top of the network path.

### 2. Dedicated narrowly scoped application-level relay

- Acceptable if the network path cannot carry the overlay directly but an approved relay host/endpoint can.
- Must be narrowly scoped to the generator completion API only.
- Must not become a general forwarder.

### 3. Provider runtime colocated on existing authorized compute

- Attractive if a compatible runtime can be placed on existing authorized compute without new billable resources and without unsafe secret handling.
- Only valid if the runtime can meet latency, timeout, failure handling, and isolation requirements.

### 4. Other cost-neutral encrypted transport

- Viable only if it satisfies the same constraints above without introducing unacceptable trust-boundary change or new cost.

## Decision posture

The intended default is the smallest authenticated private path that can be placed between AWS CORE and the approved generator without new permanent billed resources and without breaking the existing hardened boundaries.

If no secure permanent path can be completed without a new billed resource or an unacceptable trust-boundary change, that branch must stop for approval rather than being forced through.

## Adapter contract

The generator transport layer is modeled as an explicit adapter with bounded, checkable behavior.

### Inputs

- bounded completion request
- allowed model from the free-model allowlist
- optional session/request identifiers for provenance

### Outputs

- accepted candidate text or
- structured failure:
  - provider unavailable
  - timeout
  - invalid provider response
  - oversized/unstructured response

### Non-negotiable behaviors

- The transport must not bypass the deterministic verifier.
- The transport must not emit provider secrets.
- The transport must enforce request/prompt bound checks before forwarding.
- The transport must enforce model allowlist checks.
- The transport must support bounded retries and timeouts.
- The transport must preserve provenance:
  - provider and model identity
  - request and session correlation
  - candidate digest
  - timing and failure reason

### Rejection rules

- Non-allowlisted model: reject
- Oversized request: reject
- Missing or unusable provider: controlled failure
- Invalid/empty provider response: controlled failure
- Any path that would require weakening SSH or exposing the bridge publicly: rejected design, not implemented

## Security boundary note

The generator transport is a private internal path. It is not an attacker-facing service and must not be exposed as one.

## Local validation status

- Source contract for the generator bridge exists in `scripts/opencode_proxy.py` and `scripts/opencode_cli_bridge_safe_config.json`.
- Local unit/integration selection suite for the proxy exists.
- Permanent AWS CORE connectivity is not validated live here yet.

## Evidence to capture when live

When the transport is deployed and exercised, capture:

- connection direction and authenticator used
- TLS identity setup
- provider-secret placement method
- latency and timeout behavior
- failure handling and retry behavior
- replay/session-isolation behavior
- cost and any new resource created

## Approval gate

If the chosen path requires any billable AWS resource, any instance/volume mutation, or any boundary change that the authorization rules do not permit autonomously, this branch must stop here for explicit approval with estimated cost, downtime, and rollback details.

## Relationship to other phases

- This is a permanent private connectivity goal, not the same as the local bridge used for local-only tests.
- A2 SSH-wire proof can still be worked by other authorized means if a live path is reachable.
- A5 CORE private cutover readiness is adjacent but separate.
