import math

import pytest

from fleetos_robot.backends.lite import BatteryModel, LiteMotionBackend


def test_straight_motion_is_deterministic() -> None:
    backend = LiteMotionBackend()
    backend.set_velocity(0.5, 0.0)

    state = backend.step(2.0)

    assert state.x_m == pytest.approx(1.0)
    assert state.y_m == pytest.approx(0.0)
    assert state.heading_rad == pytest.approx(0.0)
    assert state.linear_mps == pytest.approx(0.5)


def test_rotation_and_heading_wrap() -> None:
    backend = LiteMotionBackend(max_wheel_angular_rps=100.0)
    backend.set_velocity(0.0, math.pi)

    state = backend.step(1.5)

    assert state.x_m == pytest.approx(0.0)
    assert state.y_m == pytest.approx(0.0)
    assert state.heading_rad == pytest.approx(-math.pi / 2.0)


def test_curved_motion_uses_differential_drive_arc() -> None:
    backend = LiteMotionBackend(max_wheel_angular_rps=100.0)
    backend.set_velocity(1.0, 1.0)

    state = backend.step(math.pi / 2.0)

    assert state.x_m == pytest.approx(1.0)
    assert state.y_m == pytest.approx(1.0)
    assert state.heading_rad == pytest.approx(math.pi / 2.0)


def test_wheel_speed_is_limited() -> None:
    backend = LiteMotionBackend(max_wheel_angular_rps=1.0)
    backend.set_velocity(100.0, 0.0)

    assert backend.snapshot().linear_mps == pytest.approx(0.1)


def test_battery_drain_and_zero_clamp() -> None:
    battery = BatteryModel(
        capacity_wh=1.0,
        idle_power_w=3600.0,
        linear_power_w_per_mps=0.0,
        angular_power_w_per_rps=0.0,
        charge_percent=50.0,
    )

    assert battery.step(1.0, 0.0, 0.0) == pytest.approx(0.0)
    assert battery.step(60.0, 0.0, 0.0) == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"capacity_wh": 0.0}, "capacity_wh"),
        ({"idle_power_w": -1.0}, "power coefficients"),
        ({"charge_percent": 101.0}, "charge_percent"),
    ],
)
def test_battery_rejects_invalid_configuration(kwargs: dict[str, float], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BatteryModel(**kwargs)


def test_backend_rejects_invalid_geometry_and_time() -> None:
    with pytest.raises(ValueError, match="geometry"):
        LiteMotionBackend(wheel_radius_m=0.0)

    with pytest.raises(ValueError, match="dt_s"):
        LiteMotionBackend().step(-0.1)

    with pytest.raises(ValueError, match="dt_s"):
        BatteryModel().step(-0.1, 0.0, 0.0)

