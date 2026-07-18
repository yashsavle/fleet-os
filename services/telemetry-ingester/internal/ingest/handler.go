// Package ingest validates telemetry and writes it to the stream backbone.
package ingest

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"strings"

	"github.com/prometheus/client_golang/prometheus"
	fleetosv1 "github.com/yashsavle/fleet-os/gen/go/fleetos/v1"
	"google.golang.org/protobuf/proto"
)

var (
	// ErrMalformedTopic indicates a telemetry message arrived on an unexpected MQTT topic.
	ErrMalformedTopic = errors.New("malformed telemetry topic")
	// ErrRobotMismatch indicates that topic and payload robot identities disagree.
	ErrRobotMismatch = errors.New("topic and payload robot IDs do not match")
)

// Producer writes one validated telemetry record to the stream backbone.
type Producer interface {
	Produce(ctx context.Context, robotID string, payload []byte, sourceTopic string) error
}

// Metrics contains telemetry-ingester Prometheus counters.
type Metrics struct {
	received  prometheus.Counter
	published prometheus.Counter
	invalid   prometheus.Counter
	errors    prometheus.Counter
}

// NewMetrics creates and registers telemetry-ingester metrics.
func NewMetrics(registerer prometheus.Registerer) *Metrics {
	metrics := &Metrics{
		received: prometheus.NewCounter(prometheus.CounterOpts{
			Name: "fleetos_telemetry_ingester_messages_received_total",
			Help: "Total MQTT telemetry messages received.",
		}),
		published: prometheus.NewCounter(prometheus.CounterOpts{
			Name: "fleetos_telemetry_ingester_messages_published_total",
			Help: "Total telemetry records published to Redpanda.",
		}),
		invalid: prometheus.NewCounter(prometheus.CounterOpts{
			Name: "fleetos_telemetry_ingester_messages_invalid_total",
			Help: "Total telemetry messages rejected as invalid.",
		}),
		errors: prometheus.NewCounter(prometheus.CounterOpts{
			Name: "fleetos_telemetry_ingester_publish_errors_total",
			Help: "Total Redpanda publish failures.",
		}),
	}
	registerer.MustRegister(metrics.received, metrics.published, metrics.invalid, metrics.errors)
	return metrics
}

// Handler validates MQTT telemetry before producing the unchanged Protobuf payload.
type Handler struct {
	producer Producer
	metrics  *Metrics
	logger   *slog.Logger
}

// NewHandler constructs a telemetry handler.
func NewHandler(producer Producer, metrics *Metrics, logger *slog.Logger) *Handler {
	return &Handler{producer: producer, metrics: metrics, logger: logger}
}

// Handle validates identity and wire format, then publishes one record.
func (h *Handler) Handle(ctx context.Context, topic string, payload []byte) error {
	h.metrics.received.Inc()
	robotID, err := robotIDFromTopic(topic)
	if err != nil {
		h.metrics.invalid.Inc()
		return err
	}

	telemetry := &fleetosv1.RobotTelemetry{}
	if err := proto.Unmarshal(payload, telemetry); err != nil {
		h.metrics.invalid.Inc()
		return fmt.Errorf("decode telemetry: %w", err)
	}
	if telemetry.GetRobotId() == "" || telemetry.GetRobotId() != robotID {
		h.metrics.invalid.Inc()
		return fmt.Errorf("%w: topic=%q payload=%q", ErrRobotMismatch, robotID, telemetry.GetRobotId())
	}

	if err := h.producer.Produce(ctx, robotID, payload, topic); err != nil {
		h.metrics.errors.Inc()
		return fmt.Errorf("publish telemetry: %w", err)
	}
	h.metrics.published.Inc()
	h.logger.Debug("telemetry published", "robot_id", robotID, "sequence", telemetry.GetSequence())
	return nil
}

func robotIDFromTopic(topic string) (string, error) {
	parts := strings.Split(topic, "/")
	if len(parts) != 5 || parts[0] != "fleetos" || parts[1] != "v1" || parts[2] != "robots" || parts[4] != "telemetry" || parts[3] == "" {
		return "", fmt.Errorf("%w: %q", ErrMalformedTopic, topic)
	}
	return parts[3], nil
}
