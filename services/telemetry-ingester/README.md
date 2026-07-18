# Telemetry ingester

The telemetry ingester is a stateless Go service that subscribes to
`fleetos/v1/robots/+/telemetry`, validates each Protobuf payload and robot identity, and writes
the unchanged payload to the `fleetos.telemetry.v1` Redpanda topic keyed by `robot_id`.

MQTT QoS 1 messages use manual acknowledgement: the ingester acknowledges only after Redpanda
accepts the record. Redelivery can therefore create duplicates, which downstream consumers must
deduplicate with `(robot_id, sequence)`.

Endpoints:

- `GET /healthz` — process liveness
- `GET /readyz` — MQTT and Redpanda readiness
- `GET /metrics` — Prometheus metrics

Configuration is supplied by `MQTT_URL`, `MQTT_CLIENT_ID`, `MQTT_TOPIC`, `KAFKA_BROKERS`,
`KAFKA_TOPIC`, `HTTP_ADDRESS`, and `CONNECT_TIMEOUT` (seconds).
