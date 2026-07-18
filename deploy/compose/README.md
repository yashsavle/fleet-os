# Local development stack

Run `make dev` to start EMQX and three lite robots. MQTT and the EMQX dashboard bind only to
localhost. Anonymous plaintext MQTT is accepted solely inside this development stack; cloud
deployments require TLS and per-robot authentication.

Run `make integration-lite` for the automated telemetry, reconnect, and shutdown checks.

