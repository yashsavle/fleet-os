"""Fleet simulation and telemetry publication loop."""

import asyncio
import time
from dataclasses import dataclass

import structlog
from google.protobuf.timestamp_pb2 import Timestamp

from fleetos.v1 import common_pb2, telemetry_pb2
from fleetos_robot.agent.config import AgentSettings
from fleetos_robot.agent.publisher import PublishError, TelemetryPublisher
from fleetos_robot.backends.base import MotionBackend, RobotSnapshot
from fleetos_robot.backends.lite import LiteMotionBackend

LOGGER = structlog.get_logger(__name__)


@dataclass(slots=True)
class SimulatedRobot:
    """Runtime state owned by one virtual robot."""

    robot_id: str
    backend: MotionBackend
    sequence: int = 0


class FleetAgent:
    """Runs a deterministic lite fleet and publishes typed observations."""

    def __init__(self, settings: AgentSettings, publisher: TelemetryPublisher) -> None:
        self._settings = settings
        self._publisher = publisher
        self._robots = [
            SimulatedRobot(
                robot_id=f"{settings.robot_id_prefix}-{index + 1:03d}",
                backend=LiteMotionBackend(),
            )
            for index in range(settings.fleet_size)
        ]
        for index, robot in enumerate(self._robots):
            direction = -1.0 if index % 2 else 1.0
            robot.backend.set_velocity(0.2 + index * 0.02, direction * 0.05)

    @staticmethod
    def _telemetry(robot: SimulatedRobot, state: RobotSnapshot) -> telemetry_pb2.RobotTelemetry:
        observed_at = Timestamp()
        observed_at.FromNanoseconds(time.time_ns())
        operating_state = (
            common_pb2.ROBOT_OPERATING_STATE_FAULT
            if state.faults
            else common_pb2.ROBOT_OPERATING_STATE_MOVING
        )
        return telemetry_pb2.RobotTelemetry(
            robot_id=robot.robot_id,
            sequence=robot.sequence,
            observed_at=observed_at,
            pose=common_pb2.Pose2D(
                x_m=state.x_m,
                y_m=state.y_m,
                heading_rad=state.heading_rad,
            ),
            velocity=common_pb2.Twist2D(
                linear_mps=state.linear_mps,
                angular_rps=state.angular_rps,
            ),
            battery_percent=state.battery_percent,
            state=operating_state,
            active_faults=[
                common_pb2.Fault(code=code, message=message) for code, message in state.faults
            ],
        )

    async def _publish_step(self, dt_s: float) -> None:
        for robot in self._robots:
            robot.sequence += 1
            state = robot.backend.step(dt_s)
            message = self._telemetry(robot, state)
            topic = f"fleetos/v1/robots/{robot.robot_id}/telemetry"
            try:
                await self._publisher.publish(topic, message.SerializeToString())
            except PublishError as error:
                LOGGER.warning(
                    "telemetry_publish_failed",
                    robot_id=robot.robot_id,
                    error=str(error),
                )

    async def run(self, stop_event: asyncio.Event) -> None:
        """Publish at the configured rate until shutdown is requested."""
        period_s = 1.0 / self._settings.publish_hz
        await self._publisher.start()
        LOGGER.info("fleet_agent_started", fleet_size=len(self._robots))
        try:
            deadline = asyncio.get_running_loop().time()
            while not stop_event.is_set():
                await self._publish_step(period_s)
                deadline += period_s
                wait_s = max(0.0, deadline - asyncio.get_running_loop().time())
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait_s)
                except TimeoutError:
                    pass
        finally:
            await self._publisher.stop()
            LOGGER.info("fleet_agent_stopped")
