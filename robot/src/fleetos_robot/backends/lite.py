"""Deterministic differential-drive simulation for local and CI fleets."""

import math
from dataclasses import dataclass

from fleetos_robot.backends.base import RobotSnapshot


def _normalize_heading(angle_rad: float) -> float:
    """Normalize an angle to the half-open interval [-pi, pi)."""
    return (angle_rad + math.pi) % (2.0 * math.pi) - math.pi


@dataclass(slots=True)
class BatteryModel:
    """Simple energy model driven by idle, translation, and turning power."""

    capacity_wh: float = 500.0
    idle_power_w: float = 20.0
    linear_power_w_per_mps: float = 80.0
    angular_power_w_per_rps: float = 25.0
    charge_percent: float = 100.0

    def __post_init__(self) -> None:
        if self.capacity_wh <= 0.0:
            raise ValueError("capacity_wh must be positive")
        if min(self.idle_power_w, self.linear_power_w_per_mps, self.angular_power_w_per_rps) < 0:
            raise ValueError("power coefficients cannot be negative")
        if not 0.0 <= self.charge_percent <= 100.0:
            raise ValueError("charge_percent must be between 0 and 100")

    def step(self, dt_s: float, linear_mps: float, angular_rps: float) -> float:
        """Consume energy for one time step and return remaining charge percent."""
        if dt_s < 0.0:
            raise ValueError("dt_s cannot be negative")
        draw_w = (
            self.idle_power_w
            + abs(linear_mps) * self.linear_power_w_per_mps
            + abs(angular_rps) * self.angular_power_w_per_rps
        )
        used_wh = draw_w * dt_s / 3600.0
        used_percent = used_wh / self.capacity_wh * 100.0
        self.charge_percent = max(0.0, self.charge_percent - used_percent)
        return self.charge_percent


class LiteMotionBackend:
    """Low-cost differential-drive model with wheel-speed limiting."""

    def __init__(
        self,
        *,
        wheel_radius_m: float = 0.1,
        wheel_base_m: float = 0.5,
        max_wheel_angular_rps: float = 10.0,
        battery: BatteryModel | None = None,
    ) -> None:
        if wheel_radius_m <= 0.0 or wheel_base_m <= 0.0 or max_wheel_angular_rps <= 0.0:
            raise ValueError("wheel geometry and speed limits must be positive")
        self._wheel_radius_m = wheel_radius_m
        self._wheel_base_m = wheel_base_m
        self._max_wheel_angular_rps = max_wheel_angular_rps
        self._battery = battery or BatteryModel()
        self._x_m = 0.0
        self._y_m = 0.0
        self._heading_rad = 0.0
        self._linear_mps = 0.0
        self._angular_rps = 0.0

    def set_velocity(self, linear_mps: float, angular_rps: float) -> None:
        """Set velocity after independently limiting left and right wheel speeds."""
        half_base = self._wheel_base_m / 2.0
        left_rps = (linear_mps - angular_rps * half_base) / self._wheel_radius_m
        right_rps = (linear_mps + angular_rps * half_base) / self._wheel_radius_m
        left_rps = max(-self._max_wheel_angular_rps, min(self._max_wheel_angular_rps, left_rps))
        right_rps = max(
            -self._max_wheel_angular_rps,
            min(self._max_wheel_angular_rps, right_rps),
        )
        self._linear_mps = self._wheel_radius_m * (left_rps + right_rps) / 2.0
        self._angular_rps = (
            self._wheel_radius_m * (right_rps - left_rps) / self._wheel_base_m
        )

    def step(self, dt_s: float) -> RobotSnapshot:
        """Advance pose and battery state using exact constant-twist integration."""
        if dt_s < 0.0:
            raise ValueError("dt_s cannot be negative")
        next_heading = self._heading_rad + self._angular_rps * dt_s
        if math.isclose(self._angular_rps, 0.0, abs_tol=1e-12):
            self._x_m += self._linear_mps * math.cos(self._heading_rad) * dt_s
            self._y_m += self._linear_mps * math.sin(self._heading_rad) * dt_s
        else:
            radius_m = self._linear_mps / self._angular_rps
            self._x_m += radius_m * (math.sin(next_heading) - math.sin(self._heading_rad))
            self._y_m -= radius_m * (math.cos(next_heading) - math.cos(self._heading_rad))
        self._heading_rad = _normalize_heading(next_heading)
        self._battery.step(dt_s, self._linear_mps, self._angular_rps)
        return self.snapshot()

    def snapshot(self) -> RobotSnapshot:
        """Return current simulated state."""
        return RobotSnapshot(
            x_m=self._x_m,
            y_m=self._y_m,
            heading_rad=self._heading_rad,
            linear_mps=self._linear_mps,
            angular_rps=self._angular_rps,
            battery_percent=self._battery.charge_percent,
        )

