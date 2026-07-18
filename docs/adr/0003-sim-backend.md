# ADR-0003: Provide pluggable simulation backends

- Status: Accepted
- Date: 2026-07-18

## Context

Fleet-scale CI needs deterministic, inexpensive simulation, while autonomy demonstrations need
physics and navigation fidelity. Making the platform depend directly on a heavyweight simulator
would make routine development slow and exclude free cloud infrastructure.

## Decision

Define a small `MotionBackend` interface for commanded velocity, deterministic stepping, and
state snapshots. Use the built-in differential-drive lite backend for development, CI, load,
and chaos tests. Add Gazebo Harmonic and optional local Isaac Sim adapters later without changing
the MQTT/Protobuf platform boundary.

The Phase 0 agent intentionally has no ROS dependency. ROS 2 integrations remain under `robot/`
and adapt their state to the same backend and edge contracts.

## Consequences

Most platform behavior can be tested quickly and deterministically. Lite simulation does not
claim physics fidelity, so navigation and traffic claims require the later Gazebo/Nav2 tests.

