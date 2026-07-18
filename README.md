# Fleet-OS

**A production-grade fleet operating system for autonomous mobile robots.**
Multi-robot simulation, typed telemetry pipeline, highly available control plane, OTA canary
deployments, and an AI diagnostics copilot, all deployed on Kubernetes with full CI/CD.

> Evolution of [aria-fleet-commander](https://github.com/yashsavle/aria-fleet-commander) (v1).
> v1 proved the concept: 6 AGVs in simulation with a live dashboard and LLM fault diagnosis.
> v2 re-architects it into the kind of platform that operates real robot fleets in production.

**Status:** Phase 1 telemetry ingestion in progress. MQTT telemetry now flows through the Go
ingester into Redpanda. See [Roadmap](#roadmap-and-phases).

## Development quick start

Prerequisite: Docker Desktop with Compose v2. The development path is containerized, so a
host Python, Go, or Buf installation is not required.

```bash
# Run contract, Python, and Go checks plus the live MQTT-to-Redpanda integration.
make lint test integration-lite

# Start EMQX, Redpanda, the Go ingester, and three lite robots at 5 Hz.
make dev

# Stop the local stack and remove its containers.
make down
```

The development broker binds MQTT to `127.0.0.1:1883`, the EMQX dashboard to
`http://127.0.0.1:18083`, Redpanda's Kafka API to `127.0.0.1:19092`, and ingester health and
metrics to `http://127.0.0.1:18080`. Anonymous plaintext MQTT is a local-only convenience.
Cloud deployments require TLS and authenticated robot identities.

---

## Table of Contents

- [Why v2: architecture analysis of v1](#why-v2-architecture-analysis-of-v1)
- [Target architecture](#target-architecture)
- [Simulation strategy (Gazebo vs Isaac Sim)](#simulation-strategy)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Deployment and free-tier hosting](#deployment-and-free-tier-hosting)
- [CI/CD](#cicd)
- [Roadmap and phases](#roadmap-and-phases)
- [Engineering practices](#engineering-practices)
- [Demo](#demo)

---

## Why v2: architecture analysis of v1

v1 worked, but every one of these was a deliberate shortcut that would fail in production.
v2 exists to fix them properly.

| # | v1 design | Problem | v2 design |
|---|-----------|---------|-----------|
| 1 | Telemetry as JSON blobs in `std_msgs/String` every 2 s | No schema, no typing, no evolution/compat story, unparseable by standard tooling, low rate | Typed ROS 2 messages on-robot; Protobuf over MQTT at the fleet boundary; schema registry and versioned contracts |
| 2 | One monolithic `fleet_manager.py` node | Single point of failure; dispatch, navigation, faults, and telemetry all coupled; untestable | Decomposed control-plane microservices (registry, scheduler, traffic, faults, OTA) with gRPC contracts |
| 3 | Browser connects directly to `rosbridge` on the VM | Couples UI to ROS transport; rosbridge exposed publicly is a serious security hole (`0.0.0.0/0` firewall rule) | Dashboard talks only to an API gateway (REST + WebSocket). ROS never leaves the robot/sim boundary |
| 4 | Single pet GCP VM, manual `Xvfb`/`x11vnc`/`gzserver` startup, IP changes every restart | Not reproducible, not recoverable, not scalable; "works on my VM" | Everything containerized; one-command local bring-up via Compose; k3s + Terraform + Helm for cloud; no GUI dependency (headless sim, web-rendered views) |
| 5 | Gazebo Classic 11 | EOL since January 2025; dead end | Pluggable sim backends: lite kinematic sim (default), modern Gazebo (gz-sim Harmonic), Isaac Sim (optional module). See [Simulation strategy](#simulation-strategy) |
| 6 | Fixed X-axis lanes for collision avoidance | Not navigation, a scheduling trick; robots can't replan | Nav2 with dynamic replanning (hi-fi mode) + a central traffic coordinator for intersection locks and deadlock prevention |
| 7 | No tests, no CI, no IaC, secrets in `.env` on laptop | No proof of engineering rigor | GitHub Actions (lint, unit, integration-in-sim, image build), Terraform-managed infra, sealed secrets |
| 8 | LLM agent answers from a prompt-stuffed fleet snapshot | Diagnoses can't cite evidence; no way to measure quality | Copilot with tool access to ClickHouse/Prometheus + a graded eval harness of injected fault scenarios |
| 9 | State lives in node memory | Restart = amnesia; no mission history, no fleet analytics | Postgres for control-plane state, ClickHouse for telemetry history, event log on Kafka-compatible stream |

**The core architectural shift:** v1 was *a simulation with a dashboard attached*.
v2 is *a control plane that happens to manage simulated robots*, with a hard, secure boundary
(MQTT + Protobuf) between the fleet and the platform. Swap the sim for real robots and the
platform doesn't change. That boundary is the whole point.

---

## Target architecture

```
┌─────────────────────────── ROBOT / EDGE LAYER (N robots, each a pod) ──────────────────────────┐
│  robot-agent container                                                                          │
│  ├─ mission executor (state machine: IDLE → ASSIGNED → NAVIGATING → EXECUTING → DONE/FAULT)     │
│  ├─ motion backend (pluggable): lite kinematic sim │ gz-sim bridge │ Isaac Sim bridge           │
│  ├─ health monitor (battery model, fault injection hooks, watchdogs)                            │
│  └─ edge bridge: typed state → Protobuf → MQTT (TLS)   ← commands ← MQTT                        │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        │  MQTT broker (EMQX)  ← the only fleet/cloud boundary
┌───────────────────────────────────────┴────────────────────────────────────────────────────────┐
│                                   CONTROL PLANE (k3s)                                          │
│                                                                                                │
│  ingestion:  telemetry-ingester (MQTT → Redpanda topics → ClickHouse sink)                     │
│                                                                                                │
│  services (gRPC between services, Postgres for state):                                          │
│  ├─ fleet-registry      robot identity, heartbeats, liveness, capability manifest              │
│  ├─ mission-scheduler   queueing, assignment (battery/position/queue-depth aware)              │
│  ├─ traffic-coordinator intersection locks, right-of-way, deadlock detection                   │
│  ├─ fault-manager       fault lifecycle, dedup, escalation → Alertmanager                      │
│  ├─ ota-orchestrator    canary rollout of robot images/config, health gates, auto-rollback     │
│  └─ api-gateway         REST + WebSocket for dashboard; authn; rate limits                     │
│                                                                                                │
│  fleet-os copilot: LLM agent with tools → ClickHouse SQL, PromQL, fault DB, runbooks           │
│                + eval harness (graded injected-fault scenarios, scored in CI)                  │
│                                                                                                │
│  data/observability: Postgres │ ClickHouse │ Redpanda │ Prometheus │ Grafana │ Alertmanager    │
└───────────────────────────────────────┬────────────────────────────────────────────────────────┘
                                        │  REST / WSS only
                              ┌─────────┴──────────┐
                              │  React dashboard   │  fleet map, missions, faults, OTA console,
                              │  (static hosting)  │  copilot chat, Grafana embeds
                              └────────────────────┘
```

Design rules that must hold everywhere:

1. **ROS 2 never crosses the fleet boundary.** MQTT + Protobuf is the only robot↔cloud contract.
2. **The dashboard never talks to robots or brokers.** API gateway only.
3. **Every service is stateless**; state lives in Postgres/ClickHouse so any pod can die.
4. **Robots are cattle.** A robot pod can be killed and rescheduled; it re-registers and resumes.
5. **Control plane survives node loss.** Demonstrated by a chaos test in CI, not claimed in prose.

---

## Simulation strategy

Honest engineering tradeoff, decided as [ADR-0003](docs/adr/0003-sim-backend.md):

| Backend | Fidelity | Scales to 20 robots | Runs on free cloud | Purpose |
|---|---|---|---|---|
| **lite** (built-in kinematic 2D sim) | Low | ✅ easily | ✅ | Default. Platform development, CI, chaos tests, fleet-scale demos |
| **Gazebo Harmonic (gz-sim)**, headless | Medium (physics) | ~6 robots | ⚠️ heavy but possible | Physics-true demos, Nav2 development |
| **NVIDIA Isaac Sim** | High (RTX, photoreal) | 1–3 robots | ❌ needs RTX GPU | Local-only optional module: one warehouse cell, one AMR + (stretch) manipulator, synthetic data |

Why not Isaac Sim as the primary backend: it requires an RTX-class GPU, cannot run on any free
cloud tier, and this project's differentiator is the **platform**, not render quality. The
`MotionBackend` interface makes the sim swappable, which is itself the senior-engineer signal:
the fleet OS does not care what generates odometry. Isaac Sim lives as `sim/isaac/` with its own
README and demo video, executed on a local RTX machine, giving legitimate resume surface area
(Isaac Sim, USD, Omniverse) without hostaging the whole project to a GPU.

Gazebo Classic 11 (v1) is EOL and is fully removed.

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Robot middleware | ROS 2 (Humble → Jazzy), Python + C++ nodes | Industry standard; C++ for the hot loop (motion), Python elsewhere |
| Robot↔cloud transport | MQTT (EMQX), TLS, Protobuf payloads | The pattern used by real AMR fleets; schema'd contracts |
| Stream backbone | Redpanda (Kafka API, single binary, ARM-friendly) | Kafka semantics without the JVM footprint; fits 24 GB free tier |
| Telemetry store | ClickHouse | Columnar, brutal ingest rates, powers copilot queries |
| Control-plane state | PostgreSQL | Boring and correct |
| Control-plane services | Go (registry, scheduler, OTA, gateway) + Python (fault-manager, copilot) | Go shows range beyond Python; gRPC contracts in `proto/` |
| Navigation (hi-fi mode) | Nav2 + custom traffic-coordinator | Real planning instead of lanes |
| Orchestration | k3s (prod), Docker Compose (dev), Helm charts | Lightweight k8s that fits free-tier VMs |
| IaC | Terraform (OCI provider) + cloud-init | Whole environment from zero with one apply |
| Observability | Prometheus, Grafana, Alertmanager, Loki | The stack the resume claims; now public proof |
| AI copilot | Claude API, tool-use, eval harness in pytest | Evidence-citing diagnosis; measured, not vibes |
| Dashboard | React 18 + Vite + TypeScript, deployed to Cloudflare Pages | Static, free, fast |
| CI/CD | GitHub Actions → GHCR (multi-arch amd64+arm64) → Argo CD or Actions-driven Helm deploy | Public, free for public repos |

---

## Repository layout

Monorepo. Every directory below is buildable and testable in isolation.

```
fleet-os/
├── proto/                     # Single source of truth: Protobuf + gRPC contracts, buf lint/breaking
├── robot/
│   ├── agent/                 # Robot-side stack (ROS 2 pkgs: executor, health, edge bridge)
│   └── backends/              # MotionBackend impls: lite/, gz/, isaac/ (isaac is local-only)
├── services/
│   ├── fleet-registry/        # Go
│   ├── mission-scheduler/     # Go
│   ├── traffic-coordinator/   # Go
│   ├── fault-manager/         # Python
│   ├── ota-orchestrator/      # Go
│   ├── telemetry-ingester/    # Go
│   └── api-gateway/           # Go
├── copilot/                   # Claude agent, tools, prompts, evals/ (graded fault scenarios)
├── dashboard/                 # React + TS
├── deploy/
│   ├── compose/               # Local dev: docker compose up = full system with lite sim
│   ├── helm/                  # One chart per service + umbrella chart
│   └── terraform/             # OCI free-tier: VCN, 2× A1 VMs, k3s bootstrap via cloud-init
├── sim/
│   ├── gz/                    # Gazebo Harmonic worlds + bridge
│   └── isaac/                 # Isaac Sim scene, extension scripts, its own README + video
├── tests/
│   ├── integration/           # Spin lite fleet in CI, run mission E2E assertions
│   └── chaos/                 # Kill control-plane node mid-mission; assert zero mission loss
├── docs/
│   ├── adr/                   # Architecture Decision Records (0001-monorepo.md, ...)
│   └── runbooks/              # Also consumed by the copilot as a tool
└── .github/workflows/         # ci.yml, images.yml, deploy.yml, evals.yml
```

---

## Deployment and free-tier hosting

Goal: the **entire system publicly reachable at $0/month**, provisioned by Terraform.

| Piece | Where | Free tier reality |
|---|---|---|
| k3s cluster (control plane + lite fleet) | **Oracle Cloud Always Free**: begin with one Ampere A1 VM sized to the tenancy's current free quota | Capacity and quotas vary by tenancy and region. The demo profile is resource constrained; ARM64 requires multi-arch images. Add a second node only when the available quota supports it. |
| Container registry | GitHub Container Registry (GHCR) | Free for public repos |
| CI | GitHub Actions | Free for public repos |
| Dashboard | Cloudflare Pages (or GitHub Pages) | Free, global CDN |
| TLS + DNS | Cloudflare (free) + cert-manager/Let's Encrypt | Free |
| Optional managed observability | Grafana Cloud free tier (10k series) | Offload if the VMs get tight |
| Gazebo demo mode | Run locally / short-lived GCP spot VM with $300 trial credits | Not kept running; recorded for the demo video |
| Isaac Sim | Local RTX machine only | Recorded demo, never "deployed" |

When the tenancy quota permits two A1 nodes, the **HA/chaos demo** drains or kills the node
running the scheduler mid-mission and asserts the fleet finishes every mission after failover.
The same test remains runnable locally with k3d when only a single cloud node is available.

Fallbacks if OCI capacity is unavailable in-region: (1) single 4-OCPU A1 VM + k3s with two
simulated "zones" via node taints, (2) GCP/AWS trial credits for the recorded HA demo.

---

## CI/CD

Public proof, not claims. Badges at the top of this README once live.

- **ci.yml** (every PR): ruff + mypy (Python), golangci-lint (Go), eslint + tsc (dashboard),
  `buf lint` + `buf breaking` (contracts), unit tests with coverage gates, then an
  **integration test that boots the full Compose stack with a 5-robot lite fleet and runs a
  mission end-to-end**, asserting telemetry lands in ClickHouse and the mission completes.
- **images.yml** (main): multi-arch (amd64+arm64) buildx builds → GHCR, SBOM + Trivy scan.
- **deploy.yml** (tag): Helm upgrade against the k3s cluster (or Argo CD sync).
- **evals.yml** (nightly + on copilot changes): runs the copilot eval suite against injected
  fault scenarios, publishes a scorecard artifact; regressions fail the build.
- **chaos.yml** (weekly): the node-kill test, recorded as evidence.

Branch protection on `main`, PR-only merges, conventional commits, release tags.

---

## Roadmap and phases

Each phase ships something demoable, has acceptance criteria, and produces a resume bullet.

**Phase 0 — Foundation (repo, contracts, CI skeleton)**
Monorepo scaffold, `proto/` contracts v1, lite MotionBackend, one robot-agent container
publishing typed Protobuf telemetry to MQTT locally, ci.yml green, ADRs 0001–0003.
*Done when:* `docker compose up` shows 3 lite robots heartbeating in `mosquitto_sub`.

**Phase 1 — Telemetry pipeline**
EMQX, telemetry-ingester, Redpanda, ClickHouse schema + sink, Prometheus + Grafana dashboards
(fleet + per-robot), load test to a measured msgs/sec figure.
*Done when:* Grafana shows live positions/battery/faults for 10 lite robots; ingest rate benchmarked and documented.

**Phase 2 — Control plane**
fleet-registry, mission-scheduler, api-gateway (REST+WS), Postgres schemas, dashboard v2 pointed
at the gateway (rosbridge dependency deleted), fault-manager + Alertmanager.
*Done when:* missions dispatched from the dashboard complete on a 10-robot lite fleet with full history in Postgres/ClickHouse.

**Phase 3 — Cloud, IaC, CD**
Terraform for OCI, k3s bootstrap, Helm charts, multi-arch images, TLS everywhere, public demo URL.
*Done when:* `terraform apply` → live public system from nothing; deploy.yml ships on tag.

**Phase 4 — OTA canary orchestrator** *(the crown jewel)*
Versioned robot images/config, rollout CRD-style spec (canary %, health gates on ClickHouse/Prom
metrics, bake time), automatic rollback on gate failure, OTA console in dashboard.
*Done when:* a deliberately bad robot image is caught by health gates and auto-rolled-back, on video.

**Phase 5 — Real autonomy (hi-fi mode)**
gz-sim Harmonic world, Nav2 bringup, traffic-coordinator intersection locks + deadlock test,
same platform managing 4 physics robots and N lite robots simultaneously (mixed fleet).
*Done when:* mixed-fleet demo video; deadlock scenario provably resolved.

**Phase 6 — HA, chaos, copilot evals, polish**
Two-node failover chaos test in CI, copilot tool-use against live ClickHouse/Prom with the
graded eval suite (≥ N scenarios, published scorecard), Isaac Sim local module, 3-minute
flagship demo video, architecture blog post.
*Done when:* chaos.yml green weekly; eval scorecard in README; video published.

---

## Engineering practices

- **ADRs** for every consequential decision (`docs/adr/`), starting with monorepo, transport
  choice, and sim strategy. Reviewers should be able to reconstruct *why*, not just *what*.
- **Contracts first.** No service PR without the `proto/` change reviewed; `buf breaking` gates it.
- **Tests are the spec.** Unit at boundaries, integration in CI with the lite fleet, chaos for HA.
- **No secrets in git.** Sealed-secrets/SOPS; `.env` files are local-only and gitignored (yes, venv too).
- **Conventional commits, small PRs, self-review.** The history is part of the portfolio.

## Demo

*(Placeholder: 3-minute video, live dashboard URL, Grafana snapshot links, eval scorecard.)*

## License

MIT
