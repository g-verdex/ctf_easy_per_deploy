# CTF Deployer Monitoring Guide

This document provides comprehensive information about the monitoring capabilities of the CTF Deployer system, including endpoint details, integration with Grafana stack, and service discovery options.

## 1. Current Implementation Status

The CTF Deployer includes the following monitoring capabilities:

| Feature | Status | Description |
|---------|--------|-------------|
| Prometheus Metrics Endpoint | ✅ Implemented | `/metrics` endpoint exposing Prometheus-compatible metrics |
| System Status & Health | ✅ Implemented | `/status`, `/admin/status` and `/health` endpoints |
| User Container Logs | ✅ Implemented | Access logs for user-created containers |
| Service Logs | ✅ Implemented | Access logs for core system services (Flask app, PostgreSQL, task service) |
| Combined Logs View | ✅ Implemented | Unified view of all system and container logs |
| Admin Dashboard UI | ✅ Implemented | Web-based interface for monitoring system health |
| Log Filtering | ✅ Implemented | Basic filtering by container/service and line count |
| Advanced Log Filtering | ⚠️ Planned | Filtering by log level, keyword search, and time range |
| Log Aggregation | ⚠️ Planned | Error counts, summaries, and statistics |

## 2. Monitoring Endpoints Reference

### 2.1. Health Endpoint

The health endpoint provides a simple status check for monitoring tools to verify the service is running.

```
GET /health
```

**Response Example:**
```json
{
  "status": "healthy"
}
```

**Notes:**
- Does not require authentication
- Returns HTTP 200 when service is operational
- Ideal for basic uptime monitoring and load balancer health checks

### 2.2. Status Endpoints

#### 2.2.1. Basic Status

```
GET /status
```

**Response Example:**
```json
{
  "challenge": "Button Clicker Challenge",
  "message": "For detailed status, use /admin/status endpoint with admin key",
  "service": "CTF Challenge Deployer",
  "status": "online"
}
```

**Notes:**
- Does not require authentication
- Returns basic service information
- Safe to expose publicly

#### 2.2.2. Admin Status

```
GET /admin/status?admin_key=YOUR_ADMIN_KEY
```

**Response Example:**
```json
{
  "challenge": "Button Clicker Challenge",
  "containers": [
    {
      "expiration_time": "2025-04-13 13:30:29",
      "full_id": "6a5f3b4a46ca7457a6c6917d900e9ef5b4add825165c905d4467a9b1a3546a4d",
      "id": "6a5f3b4a46ca...",
      "ip_address": "172.21.4.1",
      "port": 7000,
      "running": true,
      "start_time": "2025-04-13 13:00:29",
      "status": "running",
      "time_left": 1800,
      "user_uuid": "3bdc430e-99a1-41c3-8174-e85847f97b0e"
    }
  ],
  "database": {
    "connection_pool": {
      "free_connections": 18,
      "max_connections": 20,
      "min_connections": 5,
      "status": "active",
      "used_connections": 2
    },
    "host": "postgres",
    "name": "ctf_deployer"
  },
  "metrics": {
    "active_containers": 1,
    "available_ports": 999,
    "port_usage_percent": "0.1%",
    "total_containers_created": 4,
    "total_ports": 1000
  },
  "rate_limiting": {
    "max_containers_per_hour": 100,
    "window_seconds": 3600
  },
  "resources": {
    "containers": {
      "current": 1,
      "limit": 1000,
      "percent": "0.1%"
    },
    "cpu": {
      "current": "0.5%",
      "limit": "800%",
      "percent": "0.1%"
    },
    "last_updated": "2025-04-13 13:00:16",
    "memory": {
      "current": "0.05 GB",
      "limit": "32 GB",
      "percent": "0.2%"
    },
    "status": "active"
  },
  "service": "CTF Challenge Deployer",
  "status": "online",
  "version": "1.2"
}
```

**Notes:**
- Requires admin authentication (`admin_key` parameter)
- Returns detailed system information including:
  - Active containers with expiration time
  - Database connection pool status
  - Resource usage metrics (CPU, memory, containers)
  - Port allocation statistics
- Useful for integration with dashboards and monitoring systems
- Authentication is bypassed for requests from local networks (127.0.0.1, Docker networks)

### 2.3. Logs Endpoints

The logs endpoint provides access to logs from user containers and system services. It supports various filters and format options.

#### 2.3.1. All User Container Logs

```
GET /logs?admin_key=YOUR_ADMIN_KEY&format=[json|text]
```

**Parameters:**
- `format`: Output format, either `json` or `text` (default: `json`)
- `tail`: Number of log lines to retrieve per container (default: `100`)
- `since`: Unix timestamp to fetch logs since (in seconds)

**Response Example (Text Format):**
```
===== Container: 6a5f3b4a46ca7457a6c6917d900e9ef5b4add825165c905d4467a9b1a3546a4d =====
2025-04-13T13:00:29.989362894Z  * Serving Flask app 'task'
2025-04-13T13:00:29.989406516Z  * Debug mode: off
2025-04-13T13:00:29.991495318Z WARNING: This is a development server. Do not use it in a production deployment.
...
```

#### 2.3.2. Specific Service Logs

```
GET /logs?admin_key=YOUR_ADMIN_KEY&container_id=SERVICE_NAME&format=[json|text]
```

**Supported Service Names:**
- `deployer`: Flask application logs
- `database`: PostgreSQL database logs
- `task_service`: Task service container logs
- `all_services`: All service logs combined
- `all`: All logs (services + user containers)

**Parameters:**
- `container_id`: Service name or container ID
- `format`: Output format, either `json` or `text` (default: `json`)
- `tail`: Number of log lines to retrieve (default: `100`)
- `since`: Unix timestamp to fetch logs since (in seconds)

**Response Example (Database Logs):**
```
2025-04-13T13:00:00.708033317Z 
2025-04-13T13:00:00.708070748Z PostgreSQL Database directory appears to contain a database; Skipping initialization
2025-04-13T13:00:00.708073663Z 
2025-04-13T13:00:00.735922934Z 2025-04-13 13:00:00.735 UTC [1] LOG:  starting PostgreSQL 15.12...
```

**Notes:**
- Requires admin authentication (`admin_key` parameter)
- Authentication is bypassed for requests from local networks
- Returns 404 if the specified container/service is not found
- Text format is better for human reading, JSON format better for programmatic access
- The `all` option provides a complete view of the entire system

### 2.4. Prometheus Metrics Endpoint

```
GET /metrics?admin_key=YOUR_ADMIN_KEY
```

**Response Example:**
```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 1143.0
...
# HELP ctf_deployer_info Information about the CTF Deployer instance
# TYPE ctf_deployer_info gauge
ctf_deployer_info{challenge="Button Clicker Challenge",hostname="deployer1",start_time="1744548006",version="1.2"} 1.0
...
# HELP ctf_resource_usage_percent Current resource usage as percentage of limit
# TYPE ctf_resource_usage_percent gauge
ctf_resource_usage_percent{resource_type="containers"} 0.1
ctf_resource_usage_percent{resource_type="cpu"} 0.1
ctf_resource_usage_percent{resource_type="memory"} 0.2
...
```

**Notes:**
- Requires admin authentication (`admin_key` parameter)
- Authentication is bypassed for requests from local networks
- Returns standard Prometheus exposition format
- Includes both Python-specific metrics and custom CTF Deployer metrics
- Ideal for integration with Prometheus and Grafana

## 3. Setting Up the Monitoring Stack

### 3.1. Prerequisites

To set up monitoring for CTF Deployer instances, you'll need:

- A server or VM to host the monitoring stack (can be the same host as deployers)
- Docker and Docker Compose
- Basic understanding of Prometheus, Grafana, and Loki
- Access to the CTF Deployer instances (network connectivity)

### 3.2. Components

The recommended monitoring stack consists of:

1. **Prometheus**: For metrics collection and storage
2. **Grafana**: For visualization and dashboards
3. **Loki**: For log aggregation and searching
4. **Promtail**: For log collection
5. **Alertmanager** (optional): For alerts and notifications

### 3.3. Directory Structure

Create a new project with the following structure:

```
ctf-monitoring/
├── docker-compose.yml
├── prometheus/
│   ├── prometheus.yml
│   └── ctf_deployers.json
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   └── dashboards/
│   └── dashboards/
├── loki/
│   └── local-config.yaml
└── promtail/
    └── config.yml
```

### 3.4. Docker Compose Configuration

Create a `docker-compose.yml` file with the following content:

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

volumes:
  prometheus-data:
  grafana-data:
  loki-data:
```

### 3.5. Prometheus Configuration

Create a `prometheus/prometheus.yml` file:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'ctf_deployers'
    metrics_path: '/metrics'
    params:
      admin_key: ['YOUR_ADMIN_KEY_HERE']  # Replace with your actual admin key
    file_sd_configs:
      - files:
        - '/etc/prometheus/ctf_deployers.json'
        refresh_interval: 5m
```

Create a `prometheus/ctf_deployers.json` file:

```json
[
  {
    "targets": ["host.docker.internal:2169"],
    "labels": {
      "challenge": "button_clicker",
      "instance": "button_clicker_1"
    }
  }
]
```

### 3.6. Loki Configuration

Create a `loki/local-config.yaml` file (basic configuration):

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    cache_ttl: 24h
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

compactor:
  working_directory: /loki/compactor
  shared_store: filesystem
```

### 3.7. Promtail Configuration

Create a `promtail/config.yml` file:

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  # Direct API scraping for CTF Deployer logs
  - job_name: ctf_deployer_logs
    http_sd_configs:
      - url: http://host.docker.internal:2169/admin/status?admin_key=YOUR_ADMIN_KEY
        refresh_interval: 60s
        
    relabel_configs:
      - source_labels: ['__address__']
        target_label: 'instance'
        
    http:
      url: http://host.docker.internal:2169/logs?container_id=all&format=text&admin_key=YOUR_ADMIN_KEY

    # Extract timestamps, service info, and log levels
    pipeline_stages:
      - regex:
          expression: '===== (Service|Container): ([^ ]+) ====='
          stages:
            - labels:
                service: 2
                type: 1
      - regex:
          expression: '(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z) (.+)'
          stages:
            - timestamp:
                source: 1
                format: RFC3339Nano
            - output:
                source: 2
      - regex:
          expression: '(?i)(INFO|ERROR|WARN|WARNING|DEBUG)'
          stages:
            - labels:
                level: 1
```

## 4. Service Discovery

For environments with multiple CTF Deployer instances, service discovery is crucial for efficient monitoring. Here are several approaches:

### 4.1. File-Based Service Discovery

#### How it works:
1. Create a JSON file listing all your CTF Deployer instances
2. Prometheus reads this file to discover targets
3. Update the file manually or via automation when deploying new instances

#### Implementation:

Create a script to automatically generate the `ctf_deployers.json` file by scanning for deployer instances:

```bash
#!/bin/bash
# Script: generate_targets.sh
# Usage: ./generate_targets.sh /path/to/ctf_deployers_dir > prometheus/ctf_deployers.json

DEPLOYERS_DIR="$1"
TARGETS=()

# Find all .env files in subdirectories
for ENV_FILE in $(find "$DEPLOYERS_DIR" -name ".env"); do
    DIR=$(dirname "$ENV_FILE")
    INSTANCE_NAME=$(basename "$DIR")
    
    # Extract required values from .env file
    FLASK_APP_PORT=$(grep "FLASK_APP_PORT=" "$ENV_FILE" | cut -d= -f2)
    CHALLENGE_TITLE=$(grep "CHALLENGE_TITLE=" "$ENV_FILE" | cut -d= -f2 | tr -d '"')
    ADMIN_KEY=$(grep "ADMIN_KEY=" "$ENV_FILE" | cut -d= -f2)
    
    # Create a target entry
    TARGETS+=("{\"targets\":[\"localhost:$FLASK_APP_PORT\"],\"labels\":{\"instance\":\"$INSTANCE_NAME\",\"challenge\":\"$CHALLENGE_TITLE\",\"admin_key\":\"$ADMIN_KEY\"}}")
done

# Output JSON array
echo "["
for ((i=0; i<${#TARGETS[@]}; i++)); do
    echo "  ${TARGETS[$i]}"
    if [ $i -lt $((${#TARGETS[@]}-1)) ]; then
        echo ","
    fi
done
echo "]"
```

Make it executable and run periodically via cron:

```
*/5 * * * * /path/to/generate_targets.sh /path/to/deployers > /path/to/prometheus/ctf_deployers.json
```

### 4.2. Docker Socket Service Discovery

#### How it works:
1. Mount the Docker socket to Prometheus
2. Configure Prometheus to discover containers with specific labels
3. Tag CTF Deployer containers appropriately

#### Implementation:

Add the Docker socket to Prometheus in `docker-compose.yml`:

```yaml
services:
  prometheus:
    # ...
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      # ...
```

Update Prometheus configuration to discover CTF Deployer containers:

```yaml
scrape_configs:
  - job_name: 'ctf_deployers_docker'
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 15s
        filters:
          - name: label
            values: ["COMPOSE_PROJECT_NAME=.*_ctf_.*"]
    
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_label_COMPOSE_PROJECT_NAME']
        target_label: 'challenge'
      - source_labels: ['__meta_docker_container_port_private']
        regex: '5000'
        action: keep
      - source_labels: ['__meta_docker_container_network_ip']
        target_label: '__address__'
        replacement: '${1}:5000'
      - source_labels: ['__address__']
        regex: '(.*)'
        target_label: '__param_target'
        replacement: '${1}'
      - source_labels: ['__param_target']
        regex: '(.*)'
        target_label: 'instance'
      # Add admin key to metrics endpoint
      - target_label: '__param_admin_key'
        replacement: 'change_this_to_a_secure_random_value'
```

### A complete environment-aware service discovery solution

For a complete solution that adapts to the CTF Deployer environment:

```python
#!/usr/bin/env python3
# Script: discover_deployers.py

import os
import json
import glob
import re
from dotenv import load_dotenv

def find_deployers(base_path="/opt/ctf-deployers"):
    """Find all CTF Deployer instances by scanning for .env files"""
    targets = []
    
    # Find all .env files
    env_files = glob.glob(f"{base_path}/*/.env")
    
    for env_file in env_files:
        directory = os.path.dirname(env_file)
        instance_name = os.path.basename(directory)
        
        # Load .env file
        env_vars = {}
        load_dotenv(env_file, stream=env_vars)
        
        # Extract required values
        flask_port = env_vars.get("FLASK_APP_PORT", "")
        challenge_title = env_vars.get("CHALLENGE_TITLE", "")
        admin_key = env_vars.get("ADMIN_KEY", "")
        compose_name = env_vars.get("COMPOSE_PROJECT_NAME", "")
        
        if flask_port and compose_name:
            # Create target entry
            target = {
                "targets": [f"localhost:{flask_port}"],
                "labels": {
                    "instance": instance_name,
                    "challenge": compose_name,
                    "title": challenge_title
                }
            }
            targets.append(target)
    
    return targets

def generate_prometheus_config(targets):
    """Generate Prometheus configuration"""
    config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "scrape_configs": []
    }
    
    # Add targets for metrics
    metrics_job = {
        "job_name": "ctf_deployers",
        "metrics_path": "/metrics",
        "params": {
            "admin_key": ["change_this_to_a_secure_random_value"]  # Default, will be overridden
        },
        "static_configs": []
    }
    
    for target in targets:
        # Add admin_key as a param if available in the .env
        if "admin_key" in target.get("labels", {}):
            metrics_job["params"]["admin_key"] = [target["labels"]["admin_key"]]
        
        metrics_job["static_configs"].append(target)
    
    config["scrape_configs"].append(metrics_job)
    
    # Add job for probing endpoints
    probe_job = {
        "job_name": "ctf_deployers_health",
        "metrics_path": "/probe",
        "params": {
            "module": ["http_2xx"]
        },
        "static_configs": [],
        "relabel_configs": [
            {
                "source_labels": ["__address__"],
                "target_label": "__param_target",
                "replacement": "http://${1}/health"
            },
            {
                "source_labels": ["__param_target"],
                "target_label": "instance"
            }
        ]
    }
    
    for target in targets:
        probe_job["static_configs"].append(target)
    
    config["scrape_configs"].append(probe_job)
    
    return config

def generate_loki_config(targets):
    """Generate Promtail configuration for log collection"""
    config = {
        "server": {
            "http_listen_port": 9080
        },
        "positions": {
            "filename": "/tmp/positions.yaml"
        },
        "clients": [
            {
                "url": "http://loki:3100/loki/api/v1/push"
            }
        ],
        "scrape_configs": []
    }
    
    # Add job for each CTF Deployer
    for target in targets:
        instance = target["labels"]["instance"]
        address = target["targets"][0]
        admin_key = target["labels"].get("admin_key", "change_this_to_a_secure_random_value")
        
        job = {
            "job_name": f"ctf_deployer_{instance}",
            "http": {
                "url": f"http://{address}/logs?container_id=all&format=text&admin_key={admin_key}"
            },
            "scrape_interval": "30s",
            "labels": {
                "job": "ctf_deployer_logs",
                "instance": instance,
                "challenge": target["labels"].get("challenge", "unknown")
            },
            "pipeline_stages": [
                {
                    "regex": {
                        "expression": "===== (Service|Container): ([^ ]+) =====",
                        "stages": [
                            {
                                "labels": {
                                    "service": "2",
                                    "type": "1"
                                }
                            }
                        ]
                    }
                },
                {
                    "regex": {
                        "expression": "(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d+Z) (.+)",
                        "stages": [
                            {
                                "timestamp": {
                                    "source": "1",
                                    "format": "RFC3339Nano"
                                }
                            },
                            {
                                "output": {
                                    "source": "2"
                                }
                            }
                        ]
                    }
                },
                {
                    "regex": {
                        "expression": "(?i)(INFO|ERROR|WARN|WARNING|DEBUG)",
                        "stages": [
                            {
                                "labels": {
                                    "level": "1"
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        config["scrape_configs"].append(job)
    
    return config

if __name__ == "__main__":
    # Find all deployers
    targets = find_deployers()
    
    # Generate and save Prometheus targets file
    with open("/etc/prometheus/ctf_deployers.json", "w") as f:
        json.dump(targets, f, indent=2)
    
    # Generate and save Prometheus config
    prometheus_config = generate_prometheus_config(targets)
    with open("/etc/prometheus/prometheus.yml", "w") as f:
        json.dump(prometheus_config, f, indent=2)
    
    # Generate and save Promtail config
    promtail_config = generate_loki_config(targets)
    with open("/etc/promtail/config.yml", "w") as f:
        json.dump(promtail_config, f, indent=2)
    
    print(f"Discovery complete. Found {len(targets)} CTF Deployer instances.")
```

## 5. Grafana Dashboard Examples

Once your monitoring stack is set up, create dashboards for:

### 5.1. System Overview Dashboard

- Active containers count over time
- Resource usage (CPU, Memory) per deployer
- Port pool usage
- Database connection pool status

### 5.2. CTF Challenge Activity Dashboard

- Container creation rate
- Average container lifetime
- User engagement metrics
- Challenge success rate (if available)

### 5.3. Logs Explorer Dashboard

- Log volume by service
- Error rate by service
- Top error messages
- Interactive log search

### 5.4. Alert Dashboard

- Resource usage warnings
- Error rate thresholds
- Service outages
- Database connection issues

## 6. Best Practices

### 6.1. Security Considerations

- Change the default `ADMIN_KEY` in all `.env` files to a strong, unique value
- Use network segmentation to restrict access to monitoring endpoints
- Consider using HTTPS for all monitoring traffic
- Limit access to the Grafana UI with authentication

### 6.2. Performance Considerations

- Adjust scrape intervals based on system load
- Use log rotation to manage disk space
- Set appropriate retention periods for metrics and logs
- Consider using federation for large deployments

### 6.3. Operational Tips

- Set up alerting for critical conditions
- Create runbooks for common issues
- Document your monitoring setup
- Regularly review and update dashboards

## 7. Future Enhancements

The following enhancements would improve the monitoring capabilities:

### 7.1. Log API Improvements

- Add filtering by log level
- Implement keyword search functionality
- Add time range filtering
- Support for streaming logs (WebSocket)

### 7.2. Metrics Enhancements

- Per-container resource usage metrics
- Challenge-specific performance metrics
- User experience metrics (deployment time, etc.)
- Health score calculation

### 7.3. Integration Enhancements

- OpenTelemetry integration
- Trace context propagation
- Distributed tracing
- APM integration

## 8. Troubleshooting

### 8.1. Common Issues

- **Authentication failures**: Verify that the correct admin key is used in all configurations
- **Connection refused**: Check that the CTF Deployer service is running and port is accessible
- **Missing metrics**: Ensure the CTF Deployer has the metrics endpoint enabled
- **Empty logs**: Check the tail parameter and verify that logs exist for the specified container/service

### 8.2. Diagnostic Commands

Check CTF Deployer status:
```bash
curl http://localhost:2169/health
```

Test metrics endpoint:
```bash
curl http://localhost:2169/metrics?admin_key=YOUR_ADMIN_KEY
```

Test logs endpoint:
```bash
curl http://localhost:2169/logs?admin_key=YOUR_ADMIN_KEY&container_id=deployer&format=text&tail=10
```

Verify Prometheus targets:
```bash
curl http://localhost:9090/api/v1/targets
```

## 9. Conclusion

The CTF Deployer includes comprehensive monitoring capabilities that can be easily integrated with the Grafana stack. By following this guide, you can set up a complete monitoring solution for multiple CTF Deployer instances, providing visibility into system health, performance, and user activity. The service discovery options allow for automatic detection and monitoring of new instances, making it easy to scale your CTF infrastructure.
