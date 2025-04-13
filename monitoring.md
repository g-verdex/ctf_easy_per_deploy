# Monitoring the CTF Deployer

This document describes the monitoring capabilities of the CTF Deployer and provides guidance on setting up external monitoring systems.

## Overview

The CTF Deployer includes built-in monitoring endpoints that expose metrics and status information. These endpoints are designed to be consumed by external monitoring systems like Prometheus and Grafana, which should be set up as a separate project.

## Current Implementation Status

- ✅ Prometheus metrics endpoint
- ✅ Status and resource information endpoints
- ✅ Admin dashboard UI
- ✅ User container logs endpoint
- ❌ PostgreSQL database logs (planned)
- ❌ Deployer application logs (planned)

## Built-in Monitoring Endpoints

### 1. Metrics Endpoint

The CTF Deployer exposes Prometheus-compatible metrics through a `/metrics` endpoint. These metrics can be collected by Prometheus and visualized in Grafana dashboards.

```
GET /metrics?admin_key=your_admin_key
```

**Security**: Access to the metrics endpoint is restricted to:
- Requests from localhost (127.0.0.1, ::1)
- Requests from the local network
- Requests with a valid admin key

**Available Metrics**:

- **System Information**
  - `ctf_deployer_info`: Basic information about the deployer instance

- **Resource Usage**
  - `ctf_resource_usage_percent`: Current resource usage as percentage of limit
  - `ctf_resource_current`: Current resource usage in absolute units
  - `ctf_resource_limit`: Resource usage limit in absolute units

- **Container Metrics**
  - `ctf_active_containers`: Number of currently active containers
  - `ctf_container_deployments_total`: Total number of container deployments
  - `ctf_container_deployment_duration_seconds`: Time taken to deploy a container
  - `ctf_container_lifetime_seconds`: Lifetime of containers

- **Rate Limiting**
  - `ctf_rate_limit_checks_total`: Total number of rate limit checks
  - `ctf_rate_limit_rejections_total`: Total number of rejected requests due to rate limiting

- **Resource Quotas**
  - `ctf_resource_quota_checks_total`: Total number of resource quota checks
  - `ctf_resource_quota_rejections_total`: Total number of rejected requests due to resource quotas

- **Error Tracking**
  - `ctf_errors_total`: Total number of errors by type

- **Database Metrics**
  - `ctf_database_operations_total`: Total number of database operations
  - `ctf_database_operation_duration_seconds`: Time taken for database operations
  - `ctf_database_connection_pool`: Database connection pool statistics

- **Port Allocation**
  - `ctf_port_pool`: Port pool statistics
  - `ctf_port_allocation_failures_total`: Total number of port allocation failures

### 2. Status Endpoint

The CTF Deployer provides a detailed status endpoint with information about the system:

```
GET /admin/status?admin_key=your_admin_key
```

**Security**: Same as metrics endpoint.

**Response**: JSON object with information about:
- System status
- Active containers
- Database connection pool
- Resource usage
- Port allocation

### 3. Logs Endpoint

The CTF Deployer provides access to container logs through the `/logs` endpoint:

```
GET /logs?admin_key=your_admin_key
```

**Parameters**:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `container_id` | Optional container ID to get logs for | All containers |
| `tail` | Number of log lines to retrieve | 100 |
| `since` | Unix timestamp to fetch logs from | None |
| `format` | Output format (`json` or `text`) | `json` |

**Security**: Same as other monitoring endpoints.

## Admin Dashboard

The CTF Deployer includes a built-in admin dashboard UI for quick monitoring and management:

```
GET /admin
```

The admin dashboard provides a user-friendly interface for:
- Viewing system status
- Monitoring resource usage
- Managing containers
- Viewing container logs
- Accessing Prometheus metrics

## External Monitoring Setup (Separate Project)

For comprehensive monitoring across multiple CTF challenges, it's recommended to set up Prometheus, Grafana, and Loki as a separate project. The following documentation describes how to set up these systems, but **implementation is not part of this project**.

### Recommended Monitoring Stack

1. **Prometheus**: For metrics collection and storage
2. **Grafana**: For visualization
3. **Loki**: For log aggregation
4. **Node Exporter**: For host system metrics
5. **cAdvisor**: For container metrics

### Example Docker Compose Configuration

This example shows how you would configure these services in a separate monitoring project:

```yaml
version: '3'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - loki-data:/loki
    restart: unless-stopped

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    ports:
      - "9100:9100"
    restart: unless-stopped

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
  loki-data:
```

### Example Prometheus Configuration

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'ctf-deployers'
    metrics_path: '/metrics'
    params:
      admin_key: ['your_admin_key_here']
    file_sd_configs:
      - files:
        - '/etc/prometheus/ctf_deployers.json'
        refresh_interval: 5m
```

With a `ctf_deployers.json` file:

```json
[
  {
    "targets": ["host.docker.internal:2169"],
    "labels": {
      "challenge": "button_clicker"
    }
  },
  {
    "targets": ["host.docker.internal:2170"],
    "labels": {
      "challenge": "another_challenge"
    }
  }
]
```

### Example Promtail Configuration

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 5s
        filters:
          - name: label
            values: ["COMPOSE_PROJECT_NAME=.*_ctf_.*"]
    
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_log_stream']
        target_label: 'stream'
      - source_labels: ['__meta_docker_container_label_COMPOSE_PROJECT_NAME']
        target_label: 'challenge'
```

## Recommended Grafana Dashboards

When setting up Grafana, create dashboards for:

1. **Overview Dashboard**:
   - Active containers across all challenges
   - Resource usage trends
   - Deployment success rates

2. **Challenge-Specific Dashboard**:
   - Container activity for a specific challenge
   - User engagement metrics
   - Error rates and types

3. **Logs Dashboard**:
   - Log viewer with challenge/container filters
   - Error log highlighting
   - Correlation between events and metrics

4. **Security Dashboard**:
   - Rate limiting effectiveness
   - CAPTCHA validations
   - Resource quota enforcements

## Future Improvements

The following improvements are planned for future releases:

1. **PostgreSQL Database Logs**: 
   - Access to database logs through the logs endpoint
   - Integration with admin dashboard

2. **Deployer Application Logs**:
   - Access to deployer application logs through the logs endpoint
   - Integration with admin dashboard

3. **Enhanced Log Filtering**:
   - Filtering by log level
   - Searching in logs
   - Custom time ranges

## Setting Environment Variables

To enable monitoring, add these variables to your `.env` file:

```
# Security settings for monitoring endpoints
ADMIN_KEY=change_this_to_a_secure_random_value  # Required for non-localhost access
ENABLE_METRICS_AUTH=true                        # Whether to require authentication for /metrics
ENABLE_RESOURCE_QUOTAS=true                     # Enable resource usage monitoring
```

## Security Considerations

- Always use a strong, randomly generated `ADMIN_KEY`
- Consider using a reverse proxy with TLS for production deployments
- Limit access to monitoring endpoints to trusted networks
- Regularly review access logs for unauthorized access attempts
