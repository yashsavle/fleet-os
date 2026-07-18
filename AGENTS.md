# AGENTS.md — Build guidelines for coding agents (Claude Code / Codex)

You are building **Fleet-OS**. Read `README.md` first; it is the source of truth for
architecture, phases, and acceptance criteria. This file tells you *how* to work in this repo.

## Prime directives

1. **Never violate the boundary rules:** ROS 2 stays inside `robot/`; the only robot↔cloud
   contract is Protobuf over MQTT; the dashboard talks only to `api-gateway`. If a task seems to
   require breaking these, stop and flag it instead of working around it.
2. **Contracts first.** Any change to messages or RPCs starts in `proto/`, passes
   `buf lint` and `buf breaking`, and regenerates code via `make proto`. Never hand-edit
   generated code.
3. **Small, reviewable increments.** One logical change per commit, conventional commit
   messages (`feat(scheduler): ...`, `fix(ingester): ...`, `docs(adr): ...`). Do not squash a
   day of work into one commit. The git history is part of this project's portfolio value.
4. **Everything runs in Compose.** After any change, `docker compose -f deploy/compose/dev.yml up`
   must still bring up a working system with 3 lite robots. If your change breaks dev bring-up,
   fix it before moving on.
5. **No secrets, no junk.** Never commit `.env`, credentials, `venv/`, `node_modules/`,
   build artifacts, or datasets. Check `.gitignore` covers new artifact types you introduce.
6. **CI must stay green.** Run the same checks locally before finishing a task:
   `make lint test integration-lite`.

## Definition of done (every task)

- [ ] Code + unit tests (new logic ≥ 80% branch coverage in the touched package)
- [ ] Contracts updated in `proto/` if messages changed; codegen committed
- [ ] Compose dev stack boots and the 5-robot lite integration test passes
- [ ] Lint clean: ruff+mypy (py), golangci-lint (go), eslint+tsc (ts)
- [ ] Docs updated: service README, and an ADR if you made an architectural choice
- [ ] Conventional commits; PR description explains what/why/how-tested

## Language and style rules

**Go services** (`services/*`): Go 1.22+, standard layout (`cmd/`, `internal/`), gRPC via
generated stubs, `slog` structured logging with `robot_id`/`mission_id` fields, config via env
with defaults in code, graceful shutdown on SIGTERM, `/healthz` and `/readyz` on every service,
Prometheus metrics on `/metrics` (use consistent metric naming: `fleetos_<service>_<thing>_total`).
Table-driven tests. No global state.

**Python** (`robot/`, `services/fault-manager`, `copilot/`): 3.11+, `uv` for deps, ruff + mypy
strict, pydantic v2 models at IO boundaries, structlog, pytest + pytest-asyncio. ROS 2 nodes:
one node per file, parameters declared, no `time.sleep` in callbacks, lifecycle nodes where it
matters.

**TypeScript dashboard**: React 18 + Vite, strict TS, TanStack Query for REST, a single
WebSocket hook for live state, no direct fetch calls in components, component tests with
vitest + testing-library. Talks to `api-gateway` only; the base URL is injected at build time.

**Protobuf**: `buf` managed. Packages versioned `fleetos.v1.*`. Fields never renumbered; deprecate,
don't delete. Every message has a comment.

**Containers**: multi-stage Dockerfiles, non-root user, pinned base images, multi-arch
(amd64+arm64) buildable via buildx. Images must run on ARM64 (Oracle A1 is the prod target).

## Testing strategy

- `tests/integration/`: boots the Compose stack with `FLEET_SIZE=5 BACKEND=lite`, dispatches a
  mission through the real api-gateway, asserts: mission completes, telemetry rows exist in
  ClickHouse for all 5 robots, no fault events, heartbeats never gapped > 5 s.
- `tests/chaos/`: only meaningful on k3s; scripts kill the scheduler pod / drain a node
  mid-mission and assert zero mission loss after failover. Keep runnable via `make chaos` with
  kubeconfig pointed at the cluster.
- `copilot/evals/`: each scenario = fault injection spec + gold diagnosis + rubric. The harness
  injects the fault into a lite fleet, lets the copilot investigate via its real tools, and
  grades the answer. Add a scenario with every new fault type.

## Task workflow

1. Pick the next unchecked item in the current phase of `docs/PLAN.md` (create it from the
   README roadmap if missing, as checklists per phase).
2. Restate the task, list files you'll touch, note contract changes. If ambiguous, choose the
   simplest option consistent with the README and record it in the PR description (or an ADR if
   architectural).
3. Implement in slices; commit each slice.
4. Run `make lint test integration-lite`; fix everything.
5. Update `docs/PLAN.md` checkbox, service README, ADR if needed.
6. Summarize: what changed, how verified, what's next.

## Things you must never do

- Reintroduce rosbridge-to-browser, JSON-on-`std_msgs/String`, or any direct dashboard→broker path
- Expose MQTT/Redpanda/ClickHouse/Postgres publicly in Terraform or Helm (only api-gateway and
  Grafana behind auth are public)
- Add a heavyweight dependency (service mesh, JVM Kafka, cloud-managed anything paid) without an ADR
- Write to `main` directly; skip tests "temporarily"; leave TODOs without an issue reference

## Phase kickoff prompts (use these to start each phase)

- **P0:** "Scaffold the monorepo per README repo layout: Makefile, buf setup with fleetos.v1
  telemetry+command protos, lite MotionBackend with a differential-drive kinematic model and
  battery model, robot-agent that runs N simulated robots publishing Protobuf telemetry to a
  Compose-local EMQX at 5 Hz, ci.yml with lint+unit jobs, ADRs 0001 (monorepo), 0002 (MQTT+
  Protobuf boundary), 0003 (sim backend strategy)."
- **P1:** "Build telemetry-ingester (MQTT→Redpanda), ClickHouse schema + materialized views for
  fleet state, Kafka→ClickHouse sink, Prometheus exporters on all services, Grafana provisioned
  dashboards (fleet overview + robot detail), and a k6/locust load test documenting max ingest."
- **P2:** "Implement fleet-registry and mission-scheduler in Go with gRPC + Postgres,
  api-gateway with REST+WS, port the dashboard to the gateway, add fault-manager consuming the
  fault topic with Alertmanager routing, and the 5-robot E2E integration test in CI."
- **P3:** "Write Terraform for OCI Always Free (VCN, 2× A1 VMs, cloud-init k3s), Helm charts +
  umbrella chart, images.yml multi-arch to GHCR, deploy.yml on tags, cert-manager + Cloudflare
  DNS for TLS, and a runbook for cluster rebuild from zero."
- **P4:** "Build ota-orchestrator: rollout spec (target version, canary count, health gates as
  PromQL/ClickHouse queries, bake time), state machine with auto-rollback, gateway endpoints +
  dashboard OTA console, and an integration test where a bad image is caught and rolled back."
- **P5:** "Add sim/gz Harmonic world + gz-ROS2 bridge as a MotionBackend, Nav2 bringup for 4
  robots, traffic-coordinator with intersection resource locks + deadlock detection test, and
  mixed-fleet support (gz + lite robots under one scheduler)."
- **P6:** "Chaos suite (pod kill + node drain during missions), copilot tools (ClickHouse SQL,
  PromQL, fault DB, runbooks) with the eval harness and CI scorecard, docs polish, demo script."
