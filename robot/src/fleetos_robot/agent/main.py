"""Robot-agent process entry point."""

import asyncio
import signal

import structlog

from fleetos_robot.agent.config import AgentSettings
from fleetos_robot.agent.publisher import MqttTelemetryPublisher
from fleetos_robot.agent.runtime import FleetAgent


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ]
    )


async def _run() -> None:
    settings = AgentSettings.from_env()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for process_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(process_signal, stop_event.set)
    publisher = MqttTelemetryPublisher(settings)
    await FleetAgent(settings, publisher).run(stop_event)


def main() -> None:
    """Configure logging and run the asynchronous agent."""
    _configure_logging()
    asyncio.run(_run())


if __name__ == "__main__":
    main()

