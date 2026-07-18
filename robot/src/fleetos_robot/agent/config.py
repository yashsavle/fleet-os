"""Environment-backed configuration for the robot agent."""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentSettings(BaseModel):
    """Validated robot-agent configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fleet_size: int = Field(default=3, ge=1, le=1000)
    backend: Literal["lite"] = "lite"
    publish_hz: float = Field(default=5.0, gt=0.0, le=100.0)
    mqtt_host: str = Field(default="emqx", min_length=1)
    mqtt_port: int = Field(default=1883, ge=1, le=65535)
    mqtt_keepalive_s: int = Field(default=30, ge=5, le=3600)
    mqtt_connect_timeout_s: float = Field(default=15.0, gt=0.0, le=300.0)
    robot_id_prefix: str = Field(default="robot", min_length=1, max_length=32)

    @classmethod
    def from_env(cls) -> "AgentSettings":
        """Load known settings from environment variables and validate them."""
        names = {
            "fleet_size": "FLEET_SIZE",
            "backend": "BACKEND",
            "publish_hz": "PUBLISH_HZ",
            "mqtt_host": "MQTT_HOST",
            "mqtt_port": "MQTT_PORT",
            "mqtt_keepalive_s": "MQTT_KEEPALIVE_S",
            "mqtt_connect_timeout_s": "MQTT_CONNECT_TIMEOUT_S",
            "robot_id_prefix": "ROBOT_ID_PREFIX",
        }
        values: dict[str, object] = {
            field: os.environ[environment]
            for field, environment in names.items()
            if environment in os.environ
        }
        return cls.model_validate(values)

