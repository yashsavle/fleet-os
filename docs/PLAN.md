# Fleet-OS delivery plan

This checklist tracks shipped, verified work. An item is checked only after its acceptance
criteria pass locally or in CI.

## Phase 0 — Foundation

- [x] Establish the Fleet-OS name and `fleetos.v1` technical namespace.
- [x] Scaffold repository tooling, contracts, lite backend, and robot agent.
- [x] Publish Protobuf telemetry from three lite robots to Compose-local EMQX at 5 Hz.
- [x] Pass contract lint, Python lint/type checks, unit tests, and the lite integration test.
- [x] Record ADRs 0001–0003.

## Phase 1 — Telemetry platform

- [x] Ingest MQTT telemetry into Redpanda.
- [ ] Persist telemetry and fleet-state views in ClickHouse.
- [ ] Add Prometheus metrics, Grafana dashboards, and a documented load test.

## Phase 2 — Control plane and dashboard

- [ ] Build fleet registry, mission scheduler, API gateway, and Postgres schemas.
- [ ] Connect the React dashboard exclusively to the API gateway.
- [ ] Add fault manager, Alertmanager, and the five-robot mission E2E test.

## Phase 3 — Cloud and delivery

- [ ] Provision an OCI k3s demo environment with Terraform.
- [ ] Package services with Helm and publish multi-architecture images to GHCR.
- [ ] Deploy protected release tags and host the dashboard on Cloudflare Pages.

## Phase 4 — OTA orchestration

- [ ] Implement canary rollouts, health gates, bake time, and automatic rollback.
- [ ] Add gateway endpoints, an OTA console, and a bad-image rollback test.

## Phase 5 — High-fidelity autonomy

- [ ] Add Gazebo Harmonic, Nav2, traffic coordination, and mixed-fleet support.
- [ ] Prove intersection deadlock detection and recovery.

## Phase 6 — Resilience and copilot

- [ ] Add pod/node chaos tests and publish the CI scorecard.
- [ ] Add evidence-based copilot tools, graded fault scenarios, and runbooks.
- [ ] Publish the flagship demo and architecture write-up.
