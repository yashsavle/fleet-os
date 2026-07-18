# Fleet-OS robot stack

The Phase 0 robot stack is deliberately independent of ROS 2. It provides the lite motion
backend and MQTT edge agent used in CI. Later ROS 2 and high-fidelity backends must remain
inside this directory and preserve the Protobuf-over-MQTT fleet boundary.
