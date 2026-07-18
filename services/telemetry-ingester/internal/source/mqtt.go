// Package source consumes telemetry from the fleet MQTT boundary.
package source

import (
	"context"
	"fmt"
	"log/slog"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/health"
)

// Handler processes one MQTT message and returns nil only after durable publication.
type Handler interface {
	Handle(ctx context.Context, topic string, payload []byte) error
}

// MQTTSource consumes QoS 1 messages with manual acknowledgement.
type MQTTSource struct {
	client    mqtt.Client
	topic     string
	timeout   time.Duration
	readiness *health.Readiness
	logger    *slog.Logger
}

// NewMQTTSource creates a reconnecting persistent-session MQTT source.
func NewMQTTSource(
	brokerURL string,
	clientID string,
	topic string,
	timeout time.Duration,
	handler Handler,
	readiness *health.Readiness,
	logger *slog.Logger,
) *MQTTSource {
	options := mqtt.NewClientOptions().
		AddBroker(brokerURL).
		SetClientID(clientID).
		SetCleanSession(false).
		SetAutoReconnect(true).
		SetConnectRetry(true).
		SetConnectRetryInterval(time.Second).
		SetAutoAckDisabled(true).
		SetOrderMatters(false)

	options.OnConnectionLost = func(_ mqtt.Client, err error) {
		readiness.SetMQTT(false)
		logger.Warn("MQTT connection lost", "error", err)
	}
	options.OnConnect = func(client mqtt.Client) {
		token := client.Subscribe(topic, 1, func(_ mqtt.Client, message mqtt.Message) {
			if err := handler.Handle(context.Background(), message.Topic(), message.Payload()); err != nil {
				logger.Error("telemetry handling failed", "topic", message.Topic(), "error", err)
				return
			}
			message.Ack()
		})
		if !token.WaitTimeout(timeout) || token.Error() != nil {
			readiness.SetMQTT(false)
			logger.Error("MQTT subscribe failed", "topic", topic, "error", token.Error())
			return
		}
		readiness.SetMQTT(true)
		logger.Info("MQTT subscribed", "topic", topic)
	}

	return &MQTTSource{
		client:    mqtt.NewClient(options),
		topic:     topic,
		timeout:   timeout,
		readiness: readiness,
		logger:    logger,
	}
}

// Run connects and consumes until context cancellation.
func (s *MQTTSource) Run(ctx context.Context) error {
	token := s.client.Connect()
	if !token.WaitTimeout(s.timeout) {
		return fmt.Errorf("MQTT connect timed out after %s", s.timeout)
	}
	if err := token.Error(); err != nil {
		return fmt.Errorf("MQTT connect: %w", err)
	}

	<-ctx.Done()
	s.readiness.SetMQTT(false)
	if token := s.client.Unsubscribe(s.topic); token.WaitTimeout(s.timeout) && token.Error() != nil {
		s.logger.Warn("MQTT unsubscribe failed", "error", token.Error())
	}
	s.client.Disconnect(1000)
	return nil
}
