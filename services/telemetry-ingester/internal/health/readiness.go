// Package health tracks external dependencies used by readiness checks.
package health

import "sync/atomic"

// Readiness is true only when MQTT and Kafka are both available.
type Readiness struct {
	mqtt  atomic.Bool
	kafka atomic.Bool
}

// SetMQTT updates MQTT connectivity.
func (r *Readiness) SetMQTT(ready bool) {
	r.mqtt.Store(ready)
}

// SetKafka updates Kafka connectivity.
func (r *Readiness) SetKafka(ready bool) {
	r.kafka.Store(ready)
}

// Ready reports whether all required dependencies are available.
func (r *Readiness) Ready() bool {
	return r.mqtt.Load() && r.kafka.Load()
}
