// =====================================================================
// Agent-Bastion v2.0 — Production Baseline Load Testing Script (`Task 8.4`)
// Evaluates API Gateway throughput and asserts P99 latency < 200ms
//
// Usage:
//   k6 run src/tests/load_test/baseline.js
// =====================================================================

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

export let errorRate = new Rate('errors');
export let healthLatency = new Trend('health_check_duration');
export let authLatency = new Trend('auth_token_duration');

export let options = {
  stages: [
    { duration: '15s', target: 20 },  // Ramp up to 20 virtual users
    { duration: '30s', target: 50 },  // Sustained load at 50 VUs
    { duration: '15s', target: 0 },   // Cool down
  ],
  thresholds: {
    // Zero high/critical error threshold
    errors: ['rate<0.01'],
    // Establish baseline: P99 latency across all key endpoints < 200ms (`Task 8.4`)
    http_req_duration: ['p(95)<150', 'p(99)<200'],
    health_check_duration: ['p(99)<100'],
  },
};

const BASE_URL = __ENV.AGENT_BASTION_BASE_URL || 'http://localhost:8000';

export default function () {
  // 1. System Health Endpoint Check
  let resHealth = http.get(`${BASE_URL}/health`, {
    headers: { 'Accept': 'application/json' },
  });
  healthLatency.add(resHealth.timings.duration);
  let healthSuccess = check(resHealth, {
    'health status is 200': (r) => r.status === 200,
    'health returns valid json': (r) => r.json('status') !== undefined,
  });
  errorRate.add(!healthSuccess);

  sleep(0.5);

  // 2. Overview Observability / Metrics Check
  let resMetrics = http.get(`${BASE_URL}/api/v1/observability/health`, {
    headers: { 'Accept': 'application/json' },
  });
  let metricsSuccess = check(resMetrics, {
    'metrics status is 200': (r) => r.status === 200,
  });
  errorRate.add(!metricsSuccess);

  sleep(0.5);
}
