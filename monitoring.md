# Monitoring the CTF Deployer

This document describes how to monitor the CTF Deployer using Prometheus and Grafana.

## Overview

The CTF Deployer exposes Prometheus-compatible metrics through a `/metrics` endpoint. These metrics can be collected by Prometheus and visualized in Grafana dashboards.

## Metrics Endpoint

Each CTF Deployer instance exposes metrics at:

```
http://deployer-host:port/metrics
```

## Available Metrics

### System Information
- `ctf_deployer_info`: Basic information about the deployer instance (challenge name, version, etc.)

### Resource Usage
- `ctf_resource_usage_percent`: Current resource usage as percentage of limit (by resource type)
- `ctf_resource_current`: Current resource usage in absolute units (by resource type)
- `ctf_resource_limit`: Resource usage limit in absolute units (by resource type)

### Container Metrics
- `ctf_active_containers`: Number of currently active challenge containers
- `ctf_container_deployments_total`: Total number of container deployments
- `ctf_container_deployment_duration_seconds`: Time taken to deploy a container (histogram)
- `ctf_container_lifetime_seconds`: Lifetime of containers (histogram)
- `ctf_container_restarts_total`: Total number of container restarts
- `ctf_container_lifetime_extensions_total`: Total number of container lifetime extensions

### Rate Limiting
- `ctf_rate_limit_checks_total`: Total number of rate limit checks
- `ctf_rate_limit_rejections_total`: Total number of rejected requests due to rate limiting

### Resource Quotas
- `ctf_resource_quota_checks_total`: Total number of resource quota checks
- `ctf_resource_quota_rejections_total`: Total number of rejected requests due to resource quotas (by resource type)

### Error Tracking
- `ctf_errors_total`: Total number of errors (by error type)

### Database Metrics
- `ctf_database_operations_total`: Total number of database operations (by operation type)
- `ctf_database_operation_duration_seconds`: Time taken for database operations (histogram)
- `ctf_database_connection_pool`: Database connection pool statistics (by state)

### Port Allocation
- `ctf_port_pool`: Port pool statistics (by state)
- `ctf_port_allocation_failures_total`: Total number of port allocation failures

## Setting up Prometheus and Grafana

For centralized monitoring, we recommend setting up Prometheus and Grafana in a separate repository. Here's a basic setup:

### 1. Create a monitoring repository

```bash
mkdir ctf-monitoring
cd ctf-monitoring
```

### 2. Create a docker-compose.yml file

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin  # Change this!
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    restart: unless-stopped
    depends_on:
      - prometheus

  node-exporter:
    image: prom/node-exporter:latest
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
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
  prometheus_data:
  grafana_data:
```

### 3. Create a Prometheus configuration file

```bash
mkdir -p prometheus
cat > prometheus/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'ctf-deployers'
    static_configs:
      - targets:
        - 'host.docker.internal:6664'  # Replace with actual hosts and ports
        - 'host.docker.internal:6665'  # of your CTF deployers
EOF
```

### 4. Create initial Grafana dashboards

```bash
mkdir -p grafana/provisioning/dashboards
mkdir -p grafana/provisioning/datasources
```

Create a datasource configuration:

```bash
cat > grafana/provisioning/datasources/datasource.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
```

### 5. Launch the monitoring stack

```bash
docker-compose up -d
```

Access Grafana at http://localhost:3000 (default credentials: admin/admin).

## Service Discovery for Multiple CTF Deployers

For environments with multiple CTF challenges, consider using Prometheus service discovery to automatically find CTF Deployers:

1. DNS-based service discovery
2. File-based service discovery
3. Consul or another service registry

## Example Prometheus Configuration with File-based Discovery

```yaml
scrape_configs:
  # ... other jobs ...

  - job_name: 'ctf-deployers'
    file_sd_configs:
      - files:
        - '/etc/prometheus/file_sd/ctf_deployers.json'
        refresh_interval: 5m
```

Then create a file `/etc/prometheus/file_sd/ctf_deployers.json`:

```json
[
  {
    "targets": ["ctf-server1:6664", "ctf-server1:6665"],
    "labels": {
      "challenge": "web-challenge"
    }
  },
  {
    "targets": ["ctf-server2:6664"],
    "labels": {
      "challenge": "crypto-challenge"
    }
  }
]
```

## Alerting

Configure Prometheus alerting rules to be notified about resource quota issues or other problems.

Example alert rules (`prometheus/alert_rules.yml`):

```yaml
groups:
- name: ctf-deployer
  rules:
  - alert: HighResourceUsage
    expr: ctf_resource_usage_percent{resource_type="containers"} > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High container usage ({{ $value }}%)"
      description: "Container usage for {{ $labels.instance }} is high ({{ $value }}%)."

  - alert: ResourceQuotaExceeded
    expr: sum(increase(ctf_resource_quota_rejections_total[15m])) > 10
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Resource quota exceeded frequently"
      description: "Resource quota rejections occurring frequently. Consider increasing limits."
```

Update your Prometheus configuration to include these rules:

```yaml
global:
  # ... other settings ...
  
rule_files:
  - "alert_rules.yml"

# ... rest of configuration ...
```
