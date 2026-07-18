"""Subscribe to the live MQTT stream and validate the Fleet-OS wire contract."""

import os
import statistics
import threading
import time
from collections import defaultdict
from typing import Any

import paho.mqtt.client as mqtt

from fleetos.v1 import telemetry_pb2

EXPECTED_FLEET_SIZE = int(os.environ.get("EXPECTED_FLEET_SIZE", "3"))
MQTT_HOST = os.environ.get("MQTT_HOST", "emqx")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MIN_MESSAGES_PER_ROBOT = 5
TIMEOUT_S = 5.0


def main() -> None:
    """Collect, decode, and validate telemetry from every expected robot."""
    connected = threading.Event()
    complete = threading.Event()
    observations: dict[str, list[tuple[float, int]]] = defaultdict(list)
    failures: list[str] = []

    def on_connect(
        client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if reason_code.is_failure:
            failures.append(f"connection rejected: {reason_code}")
            complete.set()
            return
        client.subscribe("fleetos/v1/robots/+/telemetry", qos=1)
        connected.set()

    def on_message(_client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        try:
            telemetry = telemetry_pb2.RobotTelemetry.FromString(message.payload)
            expected_topic = f"fleetos/v1/robots/{telemetry.robot_id}/telemetry"
            if message.topic != expected_topic:
                failures.append(f"unexpected topic {message.topic!r}")
            elif not 0.0 <= telemetry.battery_percent <= 100.0:
                failures.append(f"invalid battery for {telemetry.robot_id}")
            elif not telemetry.HasField("observed_at") or not telemetry.HasField("pose"):
                failures.append(f"missing structured fields for {telemetry.robot_id}")
            else:
                observations[telemetry.robot_id].append((time.monotonic(), telemetry.sequence))
            if failures or (
                len(observations) == EXPECTED_FLEET_SIZE
                and all(len(items) >= MIN_MESSAGES_PER_ROBOT for items in observations.values())
            ):
                complete.set()
        except Exception as error:  # noqa: BLE001 - surface malformed wire data in the probe
            failures.append(f"protobuf decode failed: {error}")
            complete.set()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"fleetos-integration-{time.time_ns()}",
        protocol=mqtt.MQTTv5,
    )
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    client.loop_start()
    try:
        if not connected.wait(timeout=TIMEOUT_S):
            raise AssertionError("MQTT probe did not connect within five seconds")
        if not complete.wait(timeout=TIMEOUT_S):
            counts = {robot_id: len(items) for robot_id, items in observations.items()}
            raise AssertionError(f"telemetry deadline exceeded; counts={counts}")
        if failures:
            raise AssertionError("; ".join(failures))
        if len(observations) != EXPECTED_FLEET_SIZE:
            message = f"expected {EXPECTED_FLEET_SIZE} robots, got {sorted(observations)}"
            raise AssertionError(message)
        for robot_id, items in observations.items():
            sequences = [sequence for _, sequence in items]
            if sequences != sorted(sequences) or len(set(sequences)) != len(sequences):
                raise AssertionError(f"non-increasing sequence for {robot_id}: {sequences}")
            intervals = [current[0] - previous[0] for previous, current in zip(items, items[1:])]
            median_interval = statistics.median(intervals)
            if not 0.1 <= median_interval <= 0.4:
                raise AssertionError(
                    f"{robot_id} publish interval {median_interval:.3f}s is outside 5 Hz tolerance"
                )
        print(f"validated {EXPECTED_FLEET_SIZE} robots at approximately 5 Hz")
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
