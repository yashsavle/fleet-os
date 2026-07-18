// Package config loads and validates telemetry-ingester configuration.
package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	defaultMQTTURL      = "tcp://emqx:1883"
	defaultMQTTTopic    = "fleetos/v1/robots/+/telemetry"
	defaultKafkaBrokers = "redpanda:9092"
	defaultKafkaTopic   = "fleetos.telemetry.v1"
	defaultHTTPAddress  = ":8080"
	defaultConnectWait  = 15 * time.Second
)

// Config contains all process configuration.
type Config struct {
	MQTTURL        string
	MQTTClientID   string
	MQTTTopic      string
	KafkaBrokers   []string
	KafkaTopic     string
	HTTPAddress    string
	ConnectTimeout time.Duration
}

// Load reads configuration from environment variables and applies safe defaults.
func Load() (Config, error) {
	timeout, err := durationEnv("CONNECT_TIMEOUT", defaultConnectWait)
	if err != nil {
		return Config{}, err
	}

	cfg := Config{
		MQTTURL:        stringEnv("MQTT_URL", defaultMQTTURL),
		MQTTClientID:   stringEnv("MQTT_CLIENT_ID", "fleetos-telemetry-ingester"),
		MQTTTopic:      stringEnv("MQTT_TOPIC", defaultMQTTTopic),
		KafkaBrokers:   splitNonEmpty(stringEnv("KAFKA_BROKERS", defaultKafkaBrokers)),
		KafkaTopic:     stringEnv("KAFKA_TOPIC", defaultKafkaTopic),
		HTTPAddress:    stringEnv("HTTP_ADDRESS", defaultHTTPAddress),
		ConnectTimeout: timeout,
	}

	if cfg.MQTTURL == "" || cfg.MQTTClientID == "" || cfg.MQTTTopic == "" {
		return Config{}, fmt.Errorf("MQTT URL, client ID, and topic must be non-empty")
	}
	if len(cfg.KafkaBrokers) == 0 || cfg.KafkaTopic == "" {
		return Config{}, fmt.Errorf("Kafka brokers and topic must be non-empty")
	}
	if cfg.HTTPAddress == "" {
		return Config{}, fmt.Errorf("HTTP address must be non-empty")
	}

	return cfg, nil
}

func stringEnv(name, fallback string) string {
	value, ok := os.LookupEnv(name)
	if !ok {
		return fallback
	}
	return strings.TrimSpace(value)
}

func durationEnv(name string, fallback time.Duration) (time.Duration, error) {
	value, ok := os.LookupEnv(name)
	if !ok {
		return fallback, nil
	}
	seconds, err := strconv.ParseFloat(strings.TrimSpace(value), 64)
	if err != nil || seconds <= 0 {
		return 0, fmt.Errorf("%s must be a positive number of seconds", name)
	}
	return time.Duration(seconds * float64(time.Second)), nil
}

func splitNonEmpty(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}
