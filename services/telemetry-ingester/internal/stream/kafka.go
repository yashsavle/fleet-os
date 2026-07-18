// Package stream publishes validated telemetry to Redpanda through its Kafka API.
package stream

import (
	"context"

	"github.com/twmb/franz-go/pkg/kgo"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/health"
)

// KafkaProducer writes keyed telemetry records to one Kafka topic.
type KafkaProducer struct {
	client    *kgo.Client
	topic     string
	readiness *health.Readiness
}

// NewKafkaProducer creates a producer configured for all in-sync replica acknowledgements.
func NewKafkaProducer(brokers []string, topic string, readiness *health.Readiness) (*KafkaProducer, error) {
	client, err := kgo.NewClient(
		kgo.SeedBrokers(brokers...),
		kgo.DefaultProduceTopic(topic),
		kgo.RequiredAcks(kgo.AllISRAcks()),
		kgo.ProducerBatchCompression(kgo.NoCompression()),
	)
	if err != nil {
		return nil, err
	}
	return &KafkaProducer{client: client, topic: topic, readiness: readiness}, nil
}

// Ping verifies that Redpanda is reachable.
func (p *KafkaProducer) Ping(ctx context.Context) error {
	if err := p.client.Ping(ctx); err != nil {
		p.readiness.SetKafka(false)
		return err
	}
	p.readiness.SetKafka(true)
	return nil
}

// Produce writes the original Protobuf payload keyed by robot ID.
func (p *KafkaProducer) Produce(ctx context.Context, robotID string, payload []byte, sourceTopic string) error {
	err := p.client.ProduceSync(ctx, &kgo.Record{
		Topic: p.topic,
		Key:   []byte(robotID),
		Value: payload,
		Headers: []kgo.RecordHeader{
			{Key: "mqtt_topic", Value: []byte(sourceTopic)},
		},
	}).FirstErr()
	if err != nil {
		p.readiness.SetKafka(false)
		return err
	}
	p.readiness.SetKafka(true)
	return nil
}

// Close flushes pending records and releases network resources.
func (p *KafkaProducer) Close() {
	p.client.Close()
	p.readiness.SetKafka(false)
}
