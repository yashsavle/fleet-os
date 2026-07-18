SHELL := /bin/sh

BUF_IMAGE := bufbuild/buf:1.47.2
COMPOSE_FILE := deploy/compose/dev.yml
TEST_IMAGE := fleetos-robot-agent:test

.PHONY: proto lint test integration-lite dev down test-image

proto:
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) generate

test-image:
	docker build --target test -t $(TEST_IMAGE) -f robot/agent/Dockerfile .

lint: test-image
	docker run --rm -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) format --diff --exit-code
	docker run --rm -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) lint
	docker run --rm $(TEST_IMAGE) python -m ruff check robot tests
	docker run --rm $(TEST_IMAGE) python -m mypy robot/src tests/unit

test: test-image
	docker run --rm $(TEST_IMAGE) python -m pytest tests/unit --cov=fleetos_robot --cov-branch --cov-fail-under=80

integration-lite:
	./tests/integration/run-lite.sh

dev:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down --remove-orphans
