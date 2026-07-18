FROM python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system --gid 10001 fleetos \
    && useradd --system --uid 10001 --gid fleetos --home-dir /app fleetos

COPY pyproject.toml ./
COPY robot/src ./robot/src
COPY gen/python ./gen/python

RUN python -m pip install --no-cache-dir .

USER 10001:10001

CMD ["python", "-m", "fleetos_robot.agent.main"]

FROM runtime AS test

USER root
COPY tests ./tests
RUN python -m pip install --no-cache-dir ".[dev]"
USER 10001:10001
