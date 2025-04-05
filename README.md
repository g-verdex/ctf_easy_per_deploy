# Generic CTF Challenge Deployer

[Русская версия (Russian version)](README.ru.md)

A flexible containerized solution for deploying Capture The Flag (CTF) challenges with isolated instances for each participant.

## Overview

This system provides an easy way to deploy containerized CTF challenges for competitions, training, or educational purposes. Each participant gets their own isolated container instance with:

- Automatic time expiration
- Ability to extend session time
- Restart capability
- Independent instances to prevent interference between participants

## Components

The system consists of two main parts:

1. **Flask App (Deployer)**: A web interface for users to manage their challenge instances
2. **Challenge Container**: A Docker container with the actual CTF challenge (can be customized)

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/d1temnd/easy_per_deploy
   cd easy_per_deploy
   ```

2. Configure your challenge:
   - Update the challenge in `generic_ctf_task/` or create your own
   - Modify `.env` file with your settings
   
3. Build and start the deployer:
   ```bash
   docker-compose up --build
   ```

4. Access the deployer at `http://localhost:6664`

## How It Works

### Container Lifecycle

1. User requests a new instance through the web interface
2. System allocates a port and deploys an isolated Docker container
3. User accesses their challenge at the assigned port
4. Container automatically expires after the configured time (default: 30 minutes)
5. User can extend, restart, or manually stop their instance

### Security Features

- Each participant gets an isolated container
- Rate limiting prevents abuse (max containers per IP)
- Automatic cleanup of expired containers
- Session tracking using browser cookies

## Configuration

The main configuration is done through the `.env` file:

```
# Challenge configuration
LEAVE_TIME=1800            # Container lifetime in seconds (30 minutes)
ADD_TIME=600               # Extension time in seconds (10 minutes)
IMAGES_NAME=localhost/generic_ctf_task:latest  # Docker image for challenge
FLAG=CTF{your_flag_here}   # Flag for the challenge
PORT_IN_CONTAINER=80       # Port exposed by the challenge container
START_RANGE=9000           # Starting port range for mapping
STOP_RANGE=10000           # Ending port range for mapping
DB_PATH=./data/containers.db  # Database path

# Challenge details
CHALLENGE_TITLE=Your Challenge Title
CHALLENGE_DESCRIPTION=Brief description of your challenge
```

## Creating Your Own Challenge

To create a custom challenge:

1. Replace the contents of `generic_ctf_task/` with your challenge:
   - Customize the `Dockerfile` to build your challenge
   - Ensure your application listens on the port specified in `PORT_IN_CONTAINER`
   - Make sure your application reads the flag from the `FLAG` environment variable

2. Update the `.env` file with your challenge details:
   - Set a proper title and description
   - Configure the flag
   - Adjust time settings if needed

3. Rebuild the system:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

### Example Challenge Structure

The simplest challenge structure would be:

```
generic_ctf_task/
├── Dockerfile          # How to build your challenge
└── [challenge files]   # Your actual challenge files
```

The `Dockerfile` should:
1. Set up the environment for your challenge
2. Copy your challenge files into the container
3. Expose the correct port
4. Set the startup command

## Troubleshooting

### Common Issues

- **No available ports**: The system has reached the maximum number of concurrent containers
- **Rate limit exceeded**: A single IP has created too many instances
- **Container not starting**: Check Docker logs for errors
- **Cannot access challenge**: Ensure the challenge is running on the correct port

### Logs

To view logs:

```bash
# View deployer logs
docker-compose logs flask_app

# View logs of a specific challenge container
docker logs [container_id]
```

## Technical Details

- **Deployer**: Flask web application
- **Database**: SQLite (stored in the data directory)
- **Container Management**: Docker Python SDK
- **Frontend**: Bootstrap and vanilla JavaScript

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.