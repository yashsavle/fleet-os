package ingest

import (
	"context"
	"errors"
	"io"
	"log/slog"
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	fleetosv1 "github.com/yashsavle/fleet-os/gen/go/fleetos/v1"
	"google.golang.org/protobuf/proto"
)

type fakeProducer struct {
	err         error
	robotID     string
	payload     []byte
	sourceTopic string
}

func (p *fakeProducer) Produce(_ context.Context, robotID string, payload []byte, sourceTopic string) error {
	p.robotID = robotID
	p.payload = payload
	p.sourceTopic = sourceTopic
	return p.err
}

func newTestHandler(producer Producer) *Handler {
	return NewHandler(
		producer,
		NewMetrics(prometheus.NewRegistry()),
		slog.New(slog.NewJSONHandler(io.Discard, nil)),
	)
}

func telemetryPayload(t *testing.T, robotID string) []byte {
	t.Helper()
	payload, err := proto.Marshal(&fleetosv1.RobotTelemetry{RobotId: robotID, Sequence: 7})
	if err != nil {
		t.Fatalf("proto.Marshal() error = %v", err)
	}
	return payload
}

func TestHandlePublishesValidTelemetryUnchanged(t *testing.T) {
	producer := &fakeProducer{}
	handler := newTestHandler(producer)
	payload := telemetryPayload(t, "robot-001")
	topic := "fleetos/v1/robots/robot-001/telemetry"

	if err := handler.Handle(context.Background(), topic, payload); err != nil {
		t.Fatalf("Handle() error = %v", err)
	}
	if producer.robotID != "robot-001" || producer.sourceTopic != topic {
		t.Fatalf("unexpected record metadata: %+v", producer)
	}
	if !proto.Equal(&fleetosv1.RobotTelemetry{RobotId: "robot-001", Sequence: 7}, mustDecode(t, producer.payload)) {
		t.Fatal("produced payload differs from input telemetry")
	}
}

func TestHandleRejectsInvalidMessages(t *testing.T) {
	tests := []struct {
		name    string
		topic   string
		payload []byte
		wantErr error
	}{
		{name: "bad topic", topic: "wrong", payload: telemetryPayload(t, "robot-001"), wantErr: ErrMalformedTopic},
		{name: "bad protobuf", topic: "fleetos/v1/robots/robot-001/telemetry", payload: []byte{0xff}, wantErr: nil},
		{name: "identity mismatch", topic: "fleetos/v1/robots/robot-001/telemetry", payload: telemetryPayload(t, "robot-002"), wantErr: ErrRobotMismatch},
		{name: "empty identity", topic: "fleetos/v1/robots/robot-001/telemetry", payload: telemetryPayload(t, ""), wantErr: ErrRobotMismatch},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			err := newTestHandler(&fakeProducer{}).Handle(context.Background(), test.topic, test.payload)
			if err == nil {
				t.Fatal("Handle() error = nil")
			}
			if test.wantErr != nil && !errors.Is(err, test.wantErr) {
				t.Fatalf("Handle() error = %v, want %v", err, test.wantErr)
			}
		})
	}
}

func TestHandleReturnsProducerFailure(t *testing.T) {
	wantErr := errors.New("redpanda unavailable")
	err := newTestHandler(&fakeProducer{err: wantErr}).Handle(
		context.Background(),
		"fleetos/v1/robots/robot-001/telemetry",
		telemetryPayload(t, "robot-001"),
	)
	if !errors.Is(err, wantErr) {
		t.Fatalf("Handle() error = %v, want wrapped %v", err, wantErr)
	}
}

func mustDecode(t *testing.T, payload []byte) *fleetosv1.RobotTelemetry {
	t.Helper()
	message := &fleetosv1.RobotTelemetry{}
	if err := proto.Unmarshal(payload, message); err != nil {
		t.Fatalf("proto.Unmarshal() error = %v", err)
	}
	return message
}
