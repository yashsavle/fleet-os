# ADR-0002: Use MQTT and Protobuf at the fleet boundary

- Status: Accepted
- Date: 2026-07-18

## Context

ROS 2 is appropriate inside a robot but is not a secure or evolvable browser/cloud boundary.
The platform needs typed messages, constrained connectivity, reconnect behavior, and contracts
that can later support physical robots without changing the control plane.

## Decision

The only robot-to-cloud boundary is Protobuf over MQTT. Contracts use the `fleetos.v1` package.
Telemetry is published at QoS 1 without retention on
`fleetos/v1/robots/{robot_id}/telemetry`; commands use
`fleetos/v1/robots/{robot_id}/commands`. The dashboard never connects to MQTT or ROS and will
communicate only with the API gateway.

Plaintext anonymous MQTT is permitted only inside the localhost-bound Compose development
stack. Cloud deployments require TLS, authenticated robot identities, and topic-level ACLs.

## Consequences

Schema evolution is reviewed and checked with Buf. Robot and platform implementations remain
transport-compatible across languages, at the cost of maintaining code generation and broker
security policy.

