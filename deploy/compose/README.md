# Local development stack

Run `make dev` to start EMQX, Redpanda, the telemetry ingester, and three lite robots. MQTT,
Kafka, service health, and the EMQX dashboard bind only to localhost. Anonymous plaintext MQTT
is accepted solely inside this development stack; cloud deployments require TLS and per-robot
authentication.

Run `make integration-lite` for automated MQTT, Redpanda ingestion, reconnect, readiness, and
shutdown checks.
