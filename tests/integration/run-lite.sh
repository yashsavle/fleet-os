#!/bin/sh
set -eu

compose_file="deploy/compose/dev.yml"

cleanup() {
  docker compose -f "$compose_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

docker compose -f "$compose_file" build robot-agent telemetry-probe
docker compose -f "$compose_file" up -d --wait emqx robot-agent

if ! docker compose -f "$compose_file" run --rm telemetry-probe; then
  docker compose -f "$compose_file" logs --no-color
  exit 1
fi

docker compose -f "$compose_file" restart emqx
docker compose -f "$compose_file" up -d --wait emqx

if ! docker compose -f "$compose_file" run --rm telemetry-probe; then
  docker compose -f "$compose_file" logs --no-color
  exit 1
fi

agent_container="$(docker compose -f "$compose_file" ps -q robot-agent)"
docker compose -f "$compose_file" stop --timeout 10 robot-agent
exit_code="$(docker inspect --format '{{.State.ExitCode}}' "$agent_container")"
if [ "$exit_code" -ne 0 ]; then
  docker compose -f "$compose_file" logs --no-color robot-agent
  echo "robot agent exited with status $exit_code" >&2
  exit 1
fi

echo "lite integration passed: telemetry, reconnect, and graceful shutdown"

