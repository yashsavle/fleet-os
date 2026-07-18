package health

import "testing"

func TestReadinessRequiresBothDependencies(t *testing.T) {
	var readiness Readiness
	if readiness.Ready() {
		t.Fatal("Ready() = true before dependencies are ready")
	}
	readiness.SetMQTT(true)
	if readiness.Ready() {
		t.Fatal("Ready() = true with Kafka unavailable")
	}
	readiness.SetKafka(true)
	if !readiness.Ready() {
		t.Fatal("Ready() = false with both dependencies ready")
	}
	readiness.SetMQTT(false)
	if readiness.Ready() {
		t.Fatal("Ready() = true after MQTT disconnect")
	}
}
