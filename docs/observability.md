# Observability

This document describes the monitoring, logging, and tracing strategy for the OpenMythos API.

## Overview

OpenMythos provides observability through:

- **Metrics** exposed in Prometheus format
- **Structured JSON logging** for centralized log aggregation
- **Distributed tracing** via OpenTelemetry
- **Health check probes** for orchestration platforms
- **Alerting rules** for operational incidents

## Health Check Endpoints

The API provides health check endpoints for container orchestration and load balancer health probes.

### `/healthz` - Liveness Probe

Returns basic service health status.

**Response:**
```json
{
  "status": "ok"
}
```

**Usage:**
- **Kubernetes liveness probe** - restarts container if unhealthy
- **Load balancer health check** - removes instance from rotation if failing
- **Uptime monitoring** - external monitoring services

**Configuration:**
```yaml
# Kubernetes example
livenessProbe:
  httpGet:
    path: /healthz
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### `/readyz` - Readiness Probe

Returns detailed readiness status including dependency health.

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "storage": "ok"
  },
  "timestamp": "2026-04-23T05:36:08.980Z"
}
```

**Usage:**
- **Kubernetes readiness probe** - controls traffic routing
- **Pre-deployment validation** - ensures service is ready before cutover
- **Dependency verification** - validates external service availability

**Configuration:**
```yaml
# Kubernetes example
readinessProbe:
  httpGet:
    path: /readyz
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 3
```

## Metrics

### RED Metrics (Rate, Errors, Duration)

The API exposes the following **RED metrics** for all endpoints:

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `openmythos_http_requests_total` | Counter | Total HTTP requests | `method`, `endpoint`, `status_code` |
| `openmythos_http_request_duration_seconds` | Histogram | Request latency in seconds | `method`, `endpoint` |
| `openmythos_http_errors_total` | Counter | Total HTTP errors (4xx, 5xx) | `method`, `endpoint`, `status_code` |

### Training Job Metrics

Training-specific metrics for monitoring compute workloads:

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `openmythos_training_jobs_total` | Counter | Total training jobs created | `profile`, `status` |
| `openmythos_training_job_duration_seconds` | Histogram | Training job execution time | `profile` |
| `openmythos_training_job_cost_dollars` | Counter | Cumulative training cost | `profile`, `region` |
| `openmythos_training_job_queue_depth` | Gauge | Current jobs in queue | `profile` |
| `openmythos_training_checkpoints_total` | Counter | Checkpoints saved to S3 | `training_id` |
| `openmythos_training_failures_total` | Counter | Failed training jobs | `profile`, `failure_reason` |

### System Metrics

Infrastructure and runtime metrics:

| Metric | Type | Description | Labels |
|--------|------|-------------|--------|
| `openmythos_rate_limit_remaining` | Gauge | Remaining requests in rate limit window | `principal` |
| `openmythos_idempotency_cache_size` | Gauge | Number of cached idempotency keys | - |
| `openmythos_webhook_verifications_total` | Counter | Webhook signature verifications | `status` (verified/failed) |
| `openmythos_plugin_calls_total` | Counter | Plugin invocations | `capability`, `status` |

### `/metrics` Endpoint

Metrics are exposed at `GET /metrics` in Prometheus text exposition format.

**Example output:**
```
# HELP openmythos_http_requests_total Total HTTP requests
# TYPE openmythos_http_requests_total counter
openmythos_http_requests_total{method="POST",endpoint="/training/jobs",status_code="200"} 142
openmythos_http_requests_total{method="GET",endpoint="/healthz",status_code="200"} 8439

# HELP openmythos_training_jobs_total Total training jobs created
# TYPE openmythos_training_jobs_total counter
openmythos_training_jobs_total{profile="baseline-small",status="completed"} 37
openmythos_training_jobs_total{profile="baseline-medium",status="running"} 2
openmythos_training_jobs_total{profile="baseline-medium",status="failed"} 1

# HELP openmythos_training_job_cost_dollars Cumulative training cost
# TYPE openmythos_training_job_cost_dollars counter
openmythos_training_job_cost_dollars{profile="baseline-small",region="us-east-1"} 234.56
```

## Prometheus Configuration

### Scrape Configuration

Add this job to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'openmythos-api'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    scheme: https
    tls_config:
      insecure_skip_verify: false
    static_configs:
      - targets:
          - 'api.openmythos.example.com:443'
    metric_relabel_configs:
      - source_labels: [__name__]
        regex: 'openmythos_.*'
        action: keep
```

### Service Discovery (Kubernetes)

For Kubernetes deployments, use pod annotations for auto-discovery:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: openmythos-api
  annotations:
    prometheus.io/scrape: "true"
    prometheus.io/port: "8000"
    prometheus.io/path: "/metrics"
spec:
  containers:
    - name: api
      image: openmythos/api:latest
      ports:
        - containerPort: 8000
          name: http
```

**Prometheus ServiceMonitor (Prometheus Operator):**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: openmythos-api
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: openmythos-api
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

## Grafana Dashboards

### Training Jobs Dashboard

A comprehensive dashboard for monitoring training workloads is available at:
`config/grafana/training-jobs-dashboard.json`

**Key panels:**

1. **Training Job Success Rate**
   - Metric: `rate(openmythos_training_jobs_total{status="completed"}[5m]) / rate(openmythos_training_jobs_total[5m])`
   - Threshold: Alert if < 95%

2. **Training Cost by Profile**
   - Metric: `increase(openmythos_training_job_cost_dollars[1d])`
   - Grouped by: `profile`, `region`

3. **Queue Depth Over Time**
   - Metric: `openmythos_training_job_queue_depth`
   - Alert if > 10 for > 5 minutes

4. **P95 Job Duration**
   - Metric: `histogram_quantile(0.95, rate(openmythos_training_job_duration_seconds_bucket[5m]))`
   - Grouped by: `profile`

5. **Training Failures by Reason**
   - Metric: `increase(openmythos_training_failures_total[1h])`
   - Grouped by: `failure_reason`

### API Performance Dashboard

Monitor API-level performance metrics:
`config/grafana/api-performance-dashboard.json`

**Key panels:**

1. **Request Rate (QPS)**
   - Metric: `sum(rate(openmythos_http_requests_total[1m])) by (endpoint)`

2. **Error Rate**
   - Metric: `sum(rate(openmythos_http_errors_total[5m])) / sum(rate(openmythos_http_requests_total[5m]))`
   - Alert if > 1%

3. **P95 Latency by Endpoint**
   - Metric: `histogram_quantile(0.95, rate(openmythos_http_request_duration_seconds_bucket[5m])) by (endpoint)`

4. **Rate Limit Pressure**
   - Metric: `openmythos_rate_limit_remaining`
   - Alert if any principal has < 10 remaining requests

## Logging

### Structured JSON Logs

All logs are emitted in structured JSON format for centralized aggregation.

**Log format:**
```json
{
  "timestamp": "2026-04-23T05:36:08.980Z",
  "level": "INFO",
  "service": "openmythos-api",
  "version": "1.3.0",
  "request_id": "req_abc123def456",
  "principal": "user_xyz789",
  "endpoint": "/training/jobs",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 342,
  "message": "Training job created",
  "training_id": "train_9a8b7c6d5e",
  "profile": "baseline-medium"
}
```

**Log levels:**

| Level | Usage |
|-------|-------|
| **DEBUG** | Detailed diagnostic information (disabled in production) |
| **INFO** | Normal operational events (job created, checkpoint saved) |
| **WARN** | Degraded state or approaching limits (queue depth high, budget threshold) |
| **ERROR** | Operation failure requiring attention (job failed, webhook verification failed) |
| **CRITICAL** | Service-level failure requiring immediate action (database down, rate limit exhausted) |

### Log Aggregation

**Recommended stack:** ELK (Elasticsearch, Logstash, Kibana) or Loki (Grafana Loki)

**CloudWatch Logs (AWS):**
```python
# Configure CloudWatch handler
import watchtower
import logging

logger = logging.getLogger(__name__)
logger.addHandler(watchtower.CloudWatchLogHandler(
    log_group="/openmythos/api",
    stream_name="{machine_name}/{strftime:%Y-%m-%d}"
))
```

**Log retention policy:**
- **INFO/DEBUG:** 7 days
- **WARN:** 30 days
- **ERROR/CRITICAL:** 90 days

### Indexed Fields

Ensure these fields are indexed for efficient querying:

- `timestamp`
- `level`
- `request_id`
- `principal`
- `endpoint`
- `status_code`
- `training_id`
- `failure_reason`

## Tracing

### OpenTelemetry Integration

OpenMythos supports distributed tracing via **OpenTelemetry**.

**Configuration:**
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure tracer provider
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to collector
otlp_exporter = OTLPSpanExporter(
    endpoint="http://otel-collector:4317",
    insecure=True
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(otlp_exporter)
)

# Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)
```

**Environment variables:**
```bash
OTEL_SERVICE_NAME=openmythos-api
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1  # Sample 10% of traces
```

### Trace Context Propagation

Traces are propagated using **W3C Trace Context** headers:

```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
tracestate: openmythos=req_abc123def456
```

### Custom Spans

Add custom spans for critical operations:

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@app.post("/training/jobs")
async def create_training_job(payload: dict):
    with tracer.start_as_current_span("create_training_job") as span:
        span.set_attribute("training.profile", payload.get("profile"))
        span.set_attribute("training.region", payload.get("region"))

        # Business logic
        training_id = await submit_to_sagemaker(payload)

        span.set_attribute("training.id", training_id)
        span.add_event("job_submitted", {"provider": "sagemaker"})

        return {"trainingId": training_id, "status": "queued"}
```

### Trace Sampling Strategy

**Head-based sampling (production):**
- Sample 10% of all requests
- Always sample errors (status_code >= 400)
- Always sample slow requests (duration > 5s)

**Tail-based sampling (Jaeger configuration):**
```yaml
# jaeger-sampling-config.json
{
  "service_strategies": [
    {
      "service": "openmythos-api",
      "type": "probabilistic",
      "param": 0.1,
      "operation_strategies": [
        {
          "operation": "/training/jobs",
          "type": "probabilistic",
          "param": 1.0
        }
      ]
    }
  ],
  "default_strategy": {
    "type": "probabilistic",
    "param": 0.01
  }
}
```

## Alerting Rules

### Prometheus Alert Rules

Add to `prometheus-rules.yml`:

```yaml
groups:
  - name: openmythos_api
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(openmythos_http_errors_total[5m])) / sum(rate(openmythos_http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
          service: openmythos-api
        annotations:
          summary: "High error rate detected"
          description: "API error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, rate(openmythos_http_request_duration_seconds_bucket[5m])) > 2.0
        for: 10m
        labels:
          severity: warning
          service: openmythos-api
        annotations:
          summary: "High API latency"
          description: "P95 latency is {{ $value }}s (threshold: 2s)"

      # Training job failure rate
      - alert: TrainingJobFailureRate
        expr: |
          sum(rate(openmythos_training_jobs_total{status="failed"}[15m])) / sum(rate(openmythos_training_jobs_total[15m])) > 0.10
        for: 15m
        labels:
          severity: warning
          service: openmythos-training
        annotations:
          summary: "High training job failure rate"
          description: "{{ $value | humanizePercentage }} of training jobs are failing"

      # Budget approaching limit
      - alert: TrainingBudgetThreshold
        expr: |
          sum(increase(openmythos_training_job_cost_dollars[1d])) > 1100
        labels:
          severity: warning
          service: openmythos-training
        annotations:
          summary: "Training budget approaching soft limit"
          description: "Daily training cost is ${{ $value }} (soft limit: $1100)"

      # Budget hard limit exceeded
      - alert: TrainingBudgetExceeded
        expr: |
          sum(increase(openmythos_training_job_cost_dollars[1d])) > 1500
        labels:
          severity: critical
          service: openmythos-training
        annotations:
          summary: "Training budget EXCEEDED"
          description: "Daily training cost is ${{ $value }} (hard limit: $1500) - IMMEDIATE ACTION REQUIRED"

      # Training queue depth
      - alert: TrainingQueueDepthHigh
        expr: openmythos_training_job_queue_depth > 10
        for: 5m
        labels:
          severity: warning
          service: openmythos-training
        annotations:
          summary: "Training job queue depth is high"
          description: "{{ $value }} jobs are queued (threshold: 10)"

      # Service down
      - alert: ServiceDown
        expr: up{job="openmythos-api"} == 0
        for: 1m
        labels:
          severity: critical
          service: openmythos-api
        annotations:
          summary: "OpenMythos API is down"
          description: "Service has been down for more than 1 minute"
```

### Alerting Channels

**Recommended notification channels:**

1. **PagerDuty** - for critical alerts requiring immediate action
2. **Slack** - for warning-level alerts and team visibility
3. **Email** - for budget alerts and daily summaries

**Alertmanager configuration:**
```yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'slack-general'
  routes:
    - match:
        severity: critical
      receiver: 'pagerduty-oncall'
      continue: true
    - match:
        severity: critical
      receiver: 'slack-alerts'
    - match:
        severity: warning
      receiver: 'slack-warnings'

receivers:
  - name: 'pagerduty-oncall'
    pagerduty_configs:
      - service_key: '<PAGERDUTY_SERVICE_KEY>'
        description: '{{ .GroupLabels.alertname }}: {{ .CommonAnnotations.summary }}'

  - name: 'slack-alerts'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK_URL>'
        channel: '#openmythos-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'

  - name: 'slack-warnings'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK_URL>'
        channel: '#openmythos-warnings'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.description }}'

  - name: 'slack-general'
    slack_configs:
      - api_url: '<SLACK_WEBHOOK_URL>'
        channel: '#openmythos-general'
```

## AWS CloudWatch Integration

For AWS deployments, integrate with CloudWatch for metrics and alarms.

### CloudWatch Metrics

**Push metrics to CloudWatch:**
```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def put_training_cost_metric(cost: float, profile: str, region: str):
    cloudwatch.put_metric_data(
        Namespace='OpenMythos/Training',
        MetricData=[
            {
                'MetricName': 'TrainingCost',
                'Value': cost,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'Profile', 'Value': profile},
                    {'Name': 'Region', 'Value': region}
                ]
            }
        ]
    )
```

### CloudWatch Alarms

**Budget alarm (from training-compute-strategy.md):**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name openmythos-training-budget-warning \
  --alarm-description "Training budget soft limit" \
  --metric-name TrainingCost \
  --namespace OpenMythos/Training \
  --statistic Sum \
  --period 86400 \
  --evaluation-periods 1 \
  --threshold 1100 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:123456789012:openmythos-alerts
```

## Observability Plugin

The `observability_exporter` plugin provides Prometheus format conversion.

**Usage:**
```bash
python3 plugins/registry.py find --capability=observability.export.prometheus
```

**Plugin invocation:**
```python
from plugins.observability_exporter.entrypoint import export

payload = {
    "service": "openmythos-api",
    "metrics": {
        "http-requests-total": 8439,
        "training-jobs-completed": 37
    }
}

result = export(payload)
# Returns Prometheus text format:
# openmythos_http_requests_total{service="openmythos-api"} 8439
# openmythos_training_jobs_completed{service="openmythos-api"} 37
```

## Implementation Checklist

- [x] Health check endpoint (`/healthz`) implemented
- [ ] Readiness probe endpoint (`/readyz`) with dependency checks
- [ ] Metrics endpoint (`/metrics`) in Prometheus format
- [ ] RED metrics instrumentation (requests, errors, duration)
- [ ] Training job metrics instrumentation
- [ ] Structured JSON logging
- [ ] OpenTelemetry tracer configuration
- [ ] Custom span instrumentation for critical paths
- [ ] Prometheus scrape configuration documented
- [ ] Grafana dashboards created
- [ ] Alert rules defined
- [ ] CloudWatch integration (for AWS deployments)
- [ ] Log aggregation configured
- [ ] Trace collector deployed

## Testing Observability

**Verify health checks:**
```bash
curl https://api.openmythos.example.com/healthz
curl https://api.openmythos.example.com/readyz
```

**Verify metrics endpoint:**
```bash
curl https://api.openmythos.example.com/metrics
```

**Verify Prometheus scraping:**
```bash
# Check if target is UP in Prometheus
curl http://prometheus:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="openmythos-api")'
```

**Verify tracing:**
```bash
# Check Jaeger for traces
curl http://jaeger:16686/api/traces?service=openmythos-api&limit=10
```

## References

- [RED Method (Tom Wilkie)](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [OpenTelemetry Python SDK](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- Training Compute Strategy: `docs/training-compute-strategy.md`
