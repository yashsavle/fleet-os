"""Pluggable robot motion backends."""

from fleetos_robot.backends.base import MotionBackend, RobotSnapshot
from fleetos_robot.backends.lite import BatteryModel, LiteMotionBackend

__all__ = ["BatteryModel", "LiteMotionBackend", "MotionBackend", "RobotSnapshot"]

