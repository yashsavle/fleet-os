// Command telemetry-ingester bridges MQTT telemetry into Redpanda.
package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/config"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/health"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/httpserver"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/ingest"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/source"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/stream"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	cfg, err := config.Load()
	if err != nil {
		logger.Error("invalid configuration", "error", err)
		os.Exit(2)
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	readiness := &health.Readiness{}
	producer, err := stream.NewKafkaProducer(cfg.KafkaBrokers, cfg.KafkaTopic, readiness)
	if err != nil {
		logger.Error("create Kafka producer", "error", err)
		os.Exit(1)
	}
	defer producer.Close()

	connectCtx, cancel := context.WithTimeout(ctx, cfg.ConnectTimeout)
	if err := producer.Ping(connectCtx); err != nil {
		cancel()
		logger.Error("connect to Redpanda", "error", err)
		os.Exit(1)
	}
	cancel()

	registry := prometheus.NewRegistry()
	handler := ingest.NewHandler(producer, ingest.NewMetrics(registry), logger)
	mqttSource := source.NewMQTTSource(
		cfg.MQTTURL,
		cfg.MQTTClientID,
		cfg.MQTTTopic,
		cfg.ConnectTimeout,
		handler,
		readiness,
		logger,
	)
	server := httpserver.New(cfg.HTTPAddress, readiness, registry)

	serverErrors := make(chan error, 1)
	go func() { serverErrors <- server.Run(ctx) }()
	sourceErrors := make(chan error, 1)
	go func() { sourceErrors <- mqttSource.Run(ctx) }()

	select {
	case err := <-serverErrors:
		if err != nil {
			logger.Error("HTTP server stopped", "error", err)
		}
	case err := <-sourceErrors:
		if err != nil {
			logger.Error("MQTT source stopped", "error", err)
		}
	case <-ctx.Done():
	}
	stop()
	logger.Info("telemetry ingester stopped")
}
