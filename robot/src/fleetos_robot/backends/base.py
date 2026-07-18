"""Backend interface shared by lite and future simulator integrations."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RobotSnapshot:
    """Immutable robot state returned after a deterministic simulation step."""

    x_m: float
    y_m: float
    heading_rad: float
    linear_mps: float
    angular_rps: float
    battery_percent: float
    faults: tuple[tuple[str, str], ...] = ()


class MotionBackend(Protocol):
    """Contract implemented by every source of robot motion and odometry."""

    def set_velocity(self, linear_mps: float, angular_rps: float) -> None:
        """Set the desired planar velocity."""

    def step(self, dt_s: float) -> RobotSnapshot:
        """Advance the backend by exactly ``dt_s`` seconds."""

    def snapshot(self) -> RobotSnapshot:
        """Return current state without advancing time."""

