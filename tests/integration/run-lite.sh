#!/bin/sh
set -eu

compose_file="deploy/compose/dev.yml"

cleanup() {
  docker compose -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
}

dump_logs() {
  docker compose -f "$compose_file" logs --no-color >integration.log
  cat integration.log
}

trap cleanup EXIT INT TERM

docker compose -f "$compose_file" build robot-agent telemetry-ingester telemetry-probe redpanda-probe
if ! docker compose -f "$compose_file" up -d --wait emqx redpanda telemetry-ingester robot-agent; then
  dump_logs
  exit 1
fi

curl --fail --silent http://127.0.0.1:18080/healthz >/dev/null
curl --fail --silent http://127.0.0.1:18080/readyz >/dev/null

if ! docker compose -f "$compose_file" run --rm telemetry-probe; then
  dump_logs
  exit 1
fi

if ! docker compose -f "$compose_file" run --rm redpanda-probe; then
  dump_logs
  exit 1
fi

docker compose -f "$compose_file" restart emqx
docker compose -f "$compose_file" up -d --wait emqx

if ! docker compose -f "$compose_file" run --rm telemetry-probe; then
  dump_logs
  exit 1
fi

if ! docker compose -f "$compose_file" run --rm redpanda-probe; then
  dump_logs
  exit 1
fi

agent_container="$(docker compose -f "$compose_file" ps -q robot-agent)"
ingester_container="$(docker compose -f "$compose_file" ps -q telemetry-ingester)"
docker compose -f "$compose_file" stop --timeout 10 robot-agent
docker compose -f "$compose_file" stop --timeout 10 telemetry-ingester
exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$agent_container")"
if [ "$exit_code" -ne 0 ]; then
  dump_logs
  echo "robot agent exited with status $exit_code" >&2
  exit 1
fi

exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$ingester_container")"
if [ "$exit_code" -ne 0 ]; then
  dump_logs
  echo "telemetry ingester exited with status $exit_code" >&2
  exit 1
fi

echo "lite integration passed: MQTT, Redpanda, reconnect, readiness, and graceful shutdown"
