"""Consume Redpanda records and validate the MQTT-to-stream bridge."""

import os
import time

from kafka import KafkaConsumer

from fleetos.v1 import telemetry_pb2

EXPECTED_FLEET_SIZE = int(os.environ.get("EXPECTED_FLEET_SIZE", "3"))
KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "redpanda:9092").split(",")
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "fleetos.telemetry.v1")
TIMEOUT_MS = 8_000


def main() -> None:
    """Assert at least one correctly keyed Protobuf record for every robot."""
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKERS,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=TIMEOUT_MS,
        group_id=f"fleetos-integration-{time.time_ns()}",
    )
    robot_ids: set[str] = set()
    try:
        for record in consumer:
            telemetry = telemetry_pb2.RobotTelemetry.FromString(record.value)
            key = record.key.decode("utf-8")
            if key != telemetry.robot_id:
                raise AssertionError(f"record key {key!r} does not match {telemetry.robot_id!r}")
            if telemetry.sequence == 0 or not telemetry.HasField("observed_at"):
                raise AssertionError(f"incomplete telemetry for {telemetry.robot_id}")
            headers = dict(record.headers)
            expected_topic = f"fleetos/v1/robots/{telemetry.robot_id}/telemetry".encode()
            if headers.get("mqtt_topic") != expected_topic:
                raise AssertionError(f"missing MQTT source header for {telemetry.robot_id}")
            robot_ids.add(telemetry.robot_id)
            if len(robot_ids) == EXPECTED_FLEET_SIZE:
                break
    finally:
        consumer.close()

    expected = {f"robot-{index:03d}" for index in range(1, EXPECTED_FLEET_SIZE + 1)}
    if robot_ids != expected:
        raise AssertionError(
            f"expected Redpanda records for {sorted(expected)}, got {sorted(robot_ids)}"
        )
    print(f"validated Redpanda telemetry for {EXPECTED_FLEET_SIZE} robots")


if __name__ == "__main__":
    main()
