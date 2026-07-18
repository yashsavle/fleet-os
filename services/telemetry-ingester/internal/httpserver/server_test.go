package httpserver

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/yashsavle/fleet-os/services/telemetry-ingester/internal/health"
)

func TestHealthAndReadiness(t *testing.T) {
	readiness := &health.Readiness{}
	server := New(":0", readiness, prometheus.NewRegistry())
	handler := server.server.Handler

	request := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	response := httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("health status = %d", response.Code)
	}

	request = httptest.NewRequest(http.MethodGet, "/readyz", nil)
	response = httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusServiceUnavailable {
		t.Fatalf("unready status = %d", response.Code)
	}

	readiness.SetMQTT(true)
	readiness.SetKafka(true)
	request = httptest.NewRequest(http.MethodGet, "/readyz", nil)
	response = httptest.NewRecorder()
	handler.ServeHTTP(response, request)
	if response.Code != http.StatusOK {
		t.Fatalf("ready status = %d", response.Code)
	}
}
