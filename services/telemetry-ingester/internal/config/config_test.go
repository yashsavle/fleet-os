package config

import (
	"testing"
	"time"
)

func TestLoadDefaults(t *testing.T) {
	t.Setenv("MQTT_URL", defaultMQTTURL)

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.MQTTURL != defaultMQTTURL || cfg.MQTTTopic != defaultMQTTTopic {
		t.Fatalf("unexpected MQTT defaults: %+v", cfg)
	}
	if len(cfg.KafkaBrokers) != 1 || cfg.KafkaBrokers[0] != defaultKafkaBrokers {
		t.Fatalf("unexpected Kafka brokers: %v", cfg.KafkaBrokers)
	}
	if cfg.ConnectTimeout != defaultConnectWait {
		t.Fatalf("ConnectTimeout = %v, want %v", cfg.ConnectTimeout, defaultConnectWait)
	}
}

func TestLoadOverrides(t *testing.T) {
	t.Setenv("MQTT_URL", "tcp://broker:1883")
	t.Setenv("MQTT_CLIENT_ID", "ingester-test")
	t.Setenv("KAFKA_BROKERS", "one:9092, two:9092")
	t.Setenv("CONNECT_TIMEOUT", "2.5")

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}
	if cfg.MQTTClientID != "ingester-test" {
		t.Fatalf("MQTTClientID = %q", cfg.MQTTClientID)
	}
	if len(cfg.KafkaBrokers) != 2 || cfg.KafkaBrokers[1] != "two:9092" {
		t.Fatalf("KafkaBrokers = %v", cfg.KafkaBrokers)
	}
	if cfg.ConnectTimeout != 2500*time.Millisecond {
		t.Fatalf("ConnectTimeout = %v", cfg.ConnectTimeout)
	}
}

func TestLoadRejectsInvalidValues(t *testing.T) {
	tests := []struct {
		name  string
		key   string
		value string
	}{
		{name: "empty MQTT URL", key: "MQTT_URL", value: " "},
		{name: "empty brokers", key: "KAFKA_BROKERS", value: " , "},
		{name: "bad timeout", key: "CONNECT_TIMEOUT", value: "nope"},
		{name: "negative timeout", key: "CONNECT_TIMEOUT", value: "-1"},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Setenv(test.key, test.value)
			if _, err := Load(); err == nil {
				t.Fatal("Load() error = nil, want validation error")
			}
		})
	}
}
