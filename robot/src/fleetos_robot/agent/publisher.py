"""MQTT telemetry publisher with reconnect support."""

import asyncio
import socket
import threading
from typing import Any, Protocol

import paho.mqtt.client as mqtt
import structlog
from paho.mqtt.enums import CallbackAPIVersion

from fleetos_robot.agent.config import AgentSettings

LOGGER = structlog.get_logger(__name__)


class PublishError(RuntimeError):
    """Raised when the MQTT client rejects a telemetry message."""


class TelemetryPublisher(Protocol):
    """Lifecycle and publish interface used by the agent runtime."""

    async def start(self) -> None:
        """Start the publisher and establish its initial connection."""

    async def publish(self, topic: str, payload: bytes) -> None:
        """Publish one telemetry payload."""

    async def stop(self) -> None:
        """Stop background work and release resources."""


class MqttTelemetryPublisher:
    """Paho adapter that reconnects in its network thread after disconnects."""

    def __init__(self, settings: AgentSettings) -> None:
        client_id = f"fleetos-agent-{socket.gethostname()}"
        self._settings = settings
        self._connected = threading.Event()
        self._client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv5,
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=10)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        if reason_code.is_failure:
            LOGGER.error("mqtt_connection_rejected", reason_code=str(reason_code))
            return
        self._connected.set()
        LOGGER.info("mqtt_connected", host=self._settings.mqtt_host)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: Any,
        reason_code: Any,
        _properties: Any,
    ) -> None:
        self._connected.clear()
        LOGGER.warning("mqtt_disconnected", reason_code=str(reason_code))

    async def start(self) -> None:
        """Start Paho's reconnecting network loop and await the first connection."""
        self._client.connect_async(
            self._settings.mqtt_host,
            self._settings.mqtt_port,
            self._settings.mqtt_keepalive_s,
        )
        self._client.loop_start()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._settings.mqtt_connect_timeout_s
        while not self._connected.is_set():
            remaining_s = deadline - loop.time()
            if remaining_s <= 0.0:
                await asyncio.to_thread(self._client.loop_stop)
                raise PublishError("MQTT connection did not become ready")
            await asyncio.sleep(min(0.05, remaining_s))

    async def publish(self, topic: str, payload: bytes) -> None:
        """Queue a non-retained QoS 1 telemetry message."""
        if not self._connected.is_set():
            raise PublishError("MQTT publisher is disconnected")
        info = self._client.publish(topic, payload, qos=1, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise PublishError(f"MQTT publish failed with code {info.rc}")

    async def stop(self) -> None:
        """Disconnect and stop Paho's network thread."""
        self._client.disconnect()
        await asyncio.to_thread(self._client.loop_stop)
        self._connected.clear()
