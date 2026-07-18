from typing import Any

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import MQTTErrorCode

from fleetos_robot.agent.config import AgentSettings
from fleetos_robot.agent.publisher import MqttTelemetryPublisher, PublishError


class FakeReasonCode:
    def __init__(self, *, is_failure: bool = False) -> None:
        self.is_failure = is_failure

    def __str__(self) -> str:
        return "failure" if self.is_failure else "success"


class FakeMessageInfo:
    def __init__(self, rc: MQTTErrorCode) -> None:
        self.rc = rc


class FakeMqttClient:
    def __init__(self, *, connection_fails: bool = False) -> None:
        self.connection_fails = connection_fails
        self.publish_rc = mqtt.MQTT_ERR_SUCCESS
        self.on_connect: Any = None
        self.on_disconnect: Any = None
        self.loop_started = False
        self.loop_stopped = False
        self.disconnected = False
        self.published: list[tuple[str, bytes, int, bool]] = []

    def reconnect_delay_set(self, *, min_delay: int, max_delay: int) -> None:
        assert (min_delay, max_delay) == (1, 10)

    def connect_async(self, host: str, port: int, keepalive: int) -> None:
        assert host == "broker"
        assert (port, keepalive) == (1883, 30)

    def loop_start(self) -> None:
        self.loop_started = True
        self.on_connect(
            self,
            None,
            None,
            FakeReasonCode(is_failure=self.connection_fails),
            None,
        )

    def publish(self, topic: str, payload: bytes, *, qos: int, retain: bool) -> FakeMessageInfo:
        self.published.append((topic, payload, qos, retain))
        return FakeMessageInfo(self.publish_rc)

    def disconnect(self) -> None:
        self.disconnected = True

    def loop_stop(self) -> None:
        self.loop_stopped = True


def make_publisher(
    monkeypatch: pytest.MonkeyPatch,
    *,
    connection_fails: bool = False,
) -> tuple[MqttTelemetryPublisher, FakeMqttClient]:
    fake = FakeMqttClient(connection_fails=connection_fails)
    monkeypatch.setattr(mqtt, "Client", lambda **_kwargs: fake)
    settings = AgentSettings(mqtt_host="broker", mqtt_connect_timeout_s=0.01)
    return MqttTelemetryPublisher(settings), fake


async def test_mqtt_publisher_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, client = make_publisher(monkeypatch)

    await publisher.start()
    await publisher.publish("fleetos/v1/robots/robot-001/telemetry", b"payload")
    await publisher.stop()

    assert client.loop_started
    assert client.published == [
        ("fleetos/v1/robots/robot-001/telemetry", b"payload", 1, False)
    ]
    assert client.disconnected
    assert client.loop_stopped


async def test_mqtt_publisher_rejects_publish_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, client = make_publisher(monkeypatch)

    with pytest.raises(PublishError, match="disconnected"):
        await publisher.publish("topic", b"payload")

    await publisher.start()
    client.publish_rc = mqtt.MQTT_ERR_QUEUE_SIZE
    with pytest.raises(PublishError, match="publish failed"):
        await publisher.publish("topic", b"payload")
    await publisher.stop()


async def test_mqtt_publisher_times_out_after_rejection(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, client = make_publisher(monkeypatch, connection_fails=True)

    with pytest.raises(PublishError, match="did not become ready"):
        await publisher.start()

    assert client.loop_stopped


def test_disconnect_callback_marks_publisher_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    publisher, client = make_publisher(monkeypatch)
    publisher._connected.set()

    client.on_disconnect(client, None, None, FakeReasonCode(), None)

    assert not publisher._connected.is_set()
