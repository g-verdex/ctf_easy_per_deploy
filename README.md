# 🚀 CTF Challenge Deployer

![Version](https://img.shields.io/badge/version-1.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A flexible, containerized solution for deploying Capture The Flag (CTF) challenges with isolated instances for each participant.

## 📋 Overview

This system provides an easy way to deploy containerized CTF challenges for competitions, training, or educational purposes. Each participant gets their own isolated container instance with:

- ⏱️ Automatic expiration 
- ⌛ Session extension capability
- 🔄 Container restart functionality
- 🛡️ Isolated environments to prevent interference between participants

## ✨ Features

- **🔒 Isolated Environments**: Each user receives a dedicated containerized challenge instance
- **⚙️ Highly Configurable**: All settings configurable through a single `.env` file
- **🌐 Web Interface**: Simple UI for container management
- **🤖 CAPTCHA Protection**: Prevents automated abuse
- **🔄 Auto-cleanup**: Automatically removes expired containers
- **📊 Resource Limiting**: Control CPU, memory, and process limits
- **🛡️ Security Options**: Customizable security settings for containers
- **📈 Rate Limiting**: Prevents abuse by limiting containers per IP address
- **🌍 Network Isolation**: Dedicated network for challenge instances

## 🏛️ Architecture

The system consists of two main components:

1. **Flask Application (Deployer)**: Web interface for managing challenge instances
2. **Challenge Container**: Docker container with the actual CTF challenge

```
                ┌───────────────┐
                │    User Web   │
                │    Browser    │
                └───────┬───────┘
                        │
                        ▼
┌──────────────────────────────────────┐
│            Flask Deployer            │
│                                      │
│  ┌─────────────┐    ┌─────────────┐  │
│  │Web Interface│◄───┤ Docker API  │  │
│  └─────────────┘    └──────┬──────┘  │
└──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────┐
│           Docker Network             │
│                                      │
│    ┌─────────┐  ┌─────────┐          │
│    │Container│  │Container│   ...    │
│    │    1    │  │    2    │          │
│    └─────────┘  └─────────┘          │
└──────────────────────────────────────┘
```

## 📥 Installation

### Requirements

- Docker and Docker Compose
- Git (for cloning the repository)

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/g-verdex/ctf-deployer.git
   cd ctf-deployer
   ```

2. Configure your environment:
   ```bash
   # Create or modify the .env file as needed
   nano .env
   ```

3. Run the deployment script with root privileges:
   ```bash
   chmod +x deploy.sh
   sudo ./deploy.sh
   ```

4. Access the deployer:
   ```
   http://localhost:6664 (or your configured FLASK_APP_PORT)
   ```

## ⚙️ Configuration

All configuration is done through the `.env` file. The system validates all required variables during startup to ensure proper operation.

### Complete Environment Variable Reference

#### Container Identification

| Variable | Description | Required |
|----------|-------------|----------|
| `COMPOSE_PROJECT_NAME` | Name prefix for Docker containers | Yes |
| `IMAGES_NAME` | Docker image name for the challenge | Yes |
| `FLAG` | CTF flag value to be passed to containers | Optional* |

> *Note: `FLAG` can be left as an empty string (`FLAG=""`) if you prefer to embed the flag directly in your challenge rather than passing it as an environment variable. Do not comment out this variable even if you leave it empty.

#### Time Settings

| Variable | Description | Required |
|----------|-------------|----------|
| `LEAVE_TIME` | Default container lifetime in seconds (e.g., 1800 for 30 minutes) | Yes |
| `ADD_TIME` | Additional time when extending container life in seconds (e.g., 600 for 10 minutes) | Yes |

#### Port Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `PORT_IN_CONTAINER` | Port the challenge service runs on inside container | Yes |
| `START_RANGE` | Start of port range for container mapping (e.g., 9000) | Yes |
| `STOP_RANGE` | End of port range for container mapping (e.g., 10000) | Yes |
| `FLASK_APP_PORT` | Port where the flask deployer app will be accessible | Yes |
| `DIRECT_TEST_PORT` | Port for directly testing the challenge (bypassing deployer) | Yes |

#### Network Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `NETWORK_NAME` | Docker network name for challenge containers | Yes |
| `NETWORK_SUBNET` | Subnet for the Docker network (e.g., 172.28.16.0/22) | Yes |

#### Database Settings

| Variable | Description | Required |
|----------|-------------|----------|
| `DB_PATH` | Path to SQLite database file (e.g., ./data/containers.db) | Yes |

#### Challenge Display

| Variable | Description | Required |
|----------|-------------|----------|
| `CHALLENGE_TITLE` | Title displayed to users in the web interface | Yes |
| `CHALLENGE_DESCRIPTION` | Challenge description shown to users | Yes |

#### Resource Limits

| Variable | Description | Required |
|----------|-------------|----------|
| `CONTAINER_MEMORY_LIMIT` | Maximum memory per container (e.g., 512M) | Yes |
| `CONTAINER_SWAP_LIMIT` | Maximum swap memory per container (e.g., 512M) | Yes |
| `CONTAINER_CPU_LIMIT` | CPU cores allocated per container (e.g., 0.5 for half a core) | Yes |
| `CONTAINER_PIDS_LIMIT` | Maximum process IDs per container (e.g., 100) | Yes |

#### Security Options

| Variable | Description | Required |
|----------|-------------|----------|
| `ENABLE_NO_NEW_PRIVILEGES` | Prevent privilege escalation (true/false) | Yes |
| `ENABLE_READ_ONLY` | Make container filesystem read-only (true/false) | Yes |
| `ENABLE_TMPFS` | Enable temporary filesystem (true/false) | Yes |
| `TMPFS_SIZE` | Size of tmpfs if enabled (e.g., 64M) | Yes |

#### Container Capabilities

| Variable | Description | Required |
|----------|-------------|----------|
| `DROP_ALL_CAPABILITIES` | Whether to drop all capabilities by default (true/false) | Yes |
| `CAP_NET_BIND_SERVICE` | Allow binding to privileged ports <1024 (true/false) | Yes |
| `CAP_CHOWN` | Allow changing file ownership (true/false) | Yes |

#### Rate Limiting

| Variable | Description | Required |
|----------|-------------|----------|
| `MAX_CONTAINERS_PER_HOUR` | Maximum containers per IP address per hour | Yes |
| `RATE_LIMIT_WINDOW` | Rate limit time window in seconds (typically 3600) | Yes |


## 🔧 Creating Custom Challenges

To create a custom challenge:

1. Modify the challenge in `generic_ctf_task/`:
   - Update the `Dockerfile` to build your challenge
   - Ensure your application listens on the port specified in `PORT_IN_CONTAINER`
   - Make sure your application reads the flag from the `FLAG` environment variable (or embed it directly)

2. Update the `.env` file with your challenge details:
   - Set an appropriate title and description
   - Configure the flag (or leave as empty string if embedded)
   - Adjust time and resource settings as needed

3. Rebuild and deploy:
   ```bash
   sudo ./deploy.sh
   ```

### Example Challenge Structure

```
generic_ctf_task/
├── Dockerfile          # How to build your challenge
└── [challenge files]   # Your challenge files
```

## 🔒 Security Considerations

- Containers run with configurable isolation and resource limits
- User instances are isolated in separate containers
- Rate limiting prevents abuse
- Auto-expiration ensures resources are freed
- Network isolation prevents cross-container interference

## 🔍 Troubleshooting

### Common Issues

#### Environment Variable Issues

If you encounter errors during deployment related to missing or invalid environment variables, check the error messages from `deploy.sh` which will indicate exactly which variables need attention.

#### Port Range Issues

The system needs a range of available ports for container allocation. If you see errors like:
```
Error getting free port: name 'PORT_RANGE' is not defined
```
This typically means there's an issue with the port range configuration. Make sure:
- `START_RANGE` and `STOP_RANGE` are defined in your `.env` file
- `START_RANGE` is less than `STOP_RANGE`
- The range doesn't conflict with other services

#### Rate Limiting

If users are receiving "rate limit exceeded" errors too frequently, you can adjust:
- `MAX_CONTAINERS_PER_HOUR`: Increase this value in the `.env` file
- `RATE_LIMIT_WINDOW`: Adjust the time window for rate limiting

#### Docker Connection Issues

If the system cannot connect to Docker, ensure:
- Docker is running: `sudo systemctl status docker`
- The Flask app container has access to the Docker socket
- You're running `deploy.sh` with appropriate permissions (sudo)

### Advanced Debugging

For more detailed diagnostics:

```bash
# View all container logs
docker-compose logs -f

# View just flask_app logs
docker-compose logs -f flask_app

# View logs for a specific challenge container
docker logs [container_id]
```

## 🛠️ Maintenance

### Cleaning Up

The deployment script automatically cleans up stale networks and containers. To manually clean up:

```bash
# Stop all containers and remove networks
sudo ./deploy.sh down

# Remove all unused networks
docker network prune
```

### Updating

```bash
git pull
sudo ./deploy.sh
```

## 📄 License

[MIT License](LICENSE)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
