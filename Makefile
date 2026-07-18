SHELL := /bin/sh

BUF_IMAGE := bufbuild/buf:1.47.2@sha256:c14957e613e9b95c4bf462fa73afdee48e13a67b8014ed1f951e5615492d457d
COMPOSE_FILE := deploy/compose/dev.yml
GOLANGCI_IMAGE := golangci/golangci-lint:v1.64.8@sha256:2987913e27f4eca9c8a39129d2c7bc1e74fbcf77f181e01cea607be437aa5cb8
GO_IMAGE := golang:1.22.12-bookworm@sha256:3d699e4d15d0f8f13c9195c0632a16702b8cbdece2955af1c23b37ae5d55a253
TEST_IMAGE := fleetos-robot-agent:test

.PHONY: proto lint test go-lint go-test integration-lite dev down test-image

proto:
	docker run --rm --user "$$(id -u):$$(id -g)" -e BUF_CACHE_DIR=/tmp/buf-cache -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) generate

test-image:
	docker build --target test -t $(TEST_IMAGE) -f robot/agent/Dockerfile .

lint: test-image
	docker run --rm -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) format --diff --exit-code
	docker run --rm -v "$(CURDIR):/workspace" -w /workspace $(BUF_IMAGE) lint
	docker run --rm $(TEST_IMAGE) python -m ruff check robot tests
	docker run --rm $(TEST_IMAGE) python -m mypy robot/src tests/unit
	$(MAKE) go-lint

go-lint:
	docker run --rm --user "$$(id -u):$$(id -g)" -e GOCACHE=/tmp/go-cache -e GOLANGCI_LINT_CACHE=/tmp/golangci-cache -e GOMODCACHE=/tmp/go-mod -v "$(CURDIR):/workspace" -w /workspace $(GOLANGCI_IMAGE) golangci-lint run ./services/telemetry-ingester/...

test: test-image
	docker run --rm $(TEST_IMAGE) python -m pytest tests/unit --cov=fleetos_robot --cov-branch --cov-fail-under=80
	$(MAKE) go-test

go-test:
	docker run --rm --user "$$(id -u):$$(id -g)" -e GOCACHE=/tmp/go-cache -e GOMODCACHE=/tmp/go-mod -v "$(CURDIR):/workspace" -w /workspace $(GO_IMAGE) go test -race ./services/telemetry-ingester/...

integration-lite:
	./tests/integration/run-lite.sh

dev:
	docker compose -f $(COMPOSE_FILE) up --build

down:
	docker compose -f $(COMPOSE_FILE) down --remove-orphans
