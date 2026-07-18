import asyncio

import pytest
from pydantic import ValidationError

from fleetos.v1 import common_pb2, telemetry_pb2
from fleetos_robot.agent.config import AgentSettings
from fleetos_robot.agent.publisher import PublishError
from fleetos_robot.agent.runtime import FleetAgent


class RecordingPublisher:
    def __init__(self, stop_event: asyncio.Event, *, fail_first: bool = False) -> None:
        self.stop_event = stop_event
        self.fail_first = fail_first
        self.started = False
        self.stopped = False
        self.attempts = 0
        self.messages: list[tuple[str, bytes]] = []

    async def start(self) -> None:
        self.started = True

    async def publish(self, topic: str, payload: bytes) -> None:
        self.attempts += 1
        if self.fail_first:
            self.fail_first = False
            raise PublishError("temporary disconnect")
        self.messages.append((topic, payload))
        if len(self.messages) >= 3:
            self.stop_event.set()

    async def stop(self) -> None:
        self.stopped = True


def test_settings_defaults_and_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FLEET_SIZE", "5")
    monkeypatch.setenv("PUBLISH_HZ", "10")

    settings = AgentSettings.from_env()

    assert settings.fleet_size == 5
    assert settings.publish_hz == 10.0
    assert settings.mqtt_host == "emqx"


@pytest.mark.parametrize(
    "values",
    [
        {"fleet_size": 0},
        {"publish_hz": 0},
        {"backend": "gazebo"},
        {"mqtt_port": 70000},
    ],
)
def test_settings_reject_invalid_values(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        AgentSettings.model_validate(values)


async def test_agent_serializes_three_robots_and_stops_cleanly() -> None:
    stop_event = asyncio.Event()
    publisher = RecordingPublisher(stop_event)
    settings = AgentSettings(fleet_size=3, publish_hz=100.0)

    await FleetAgent(settings, publisher).run(stop_event)

    assert publisher.started
    assert publisher.stopped
    assert len(publisher.messages) == 3
    robot_ids: set[str] = set()
    for topic, payload in publisher.messages:
        message = telemetry_pb2.RobotTelemetry.FromString(payload)
        robot_ids.add(message.robot_id)
        assert topic == f"fleetos/v1/robots/{message.robot_id}/telemetry"
        assert message.sequence == 1
        assert message.state == common_pb2.ROBOT_OPERATING_STATE_MOVING
        assert message.battery_percent < 100.0
    assert robot_ids == {"robot-001", "robot-002", "robot-003"}


async def test_agent_keeps_running_after_publish_failure() -> None:
    stop_event = asyncio.Event()
    publisher = RecordingPublisher(stop_event, fail_first=True)
    settings = AgentSettings(fleet_size=2, publish_hz=100.0)

    await FleetAgent(settings, publisher).run(stop_event)

    assert publisher.attempts >= 4
    assert publisher.stopped
    published_robot_ids = {
        telemetry_pb2.RobotTelemetry.FromString(item[1]).robot_id
        for item in publisher.messages
    }
    assert published_robot_ids == {
        "robot-001",
        "robot-002",
    }
