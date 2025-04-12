#!/bin/bash

# Terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory for lock files
LOCK_DIR="/var/lock/ctf_deployer"

# Command and options
COMMAND=""
VERBOSE_MODE=false

# Print styled messages based on level
log_info() {
    if [ "$VERBOSE_MODE" = true ]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    if [ "$VERBOSE_MODE" = true ]; then
        echo -e "${GREEN}[SUCCESS]${NC} $1"
    fi
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_debug() {
    if [ "$VERBOSE_MODE" = true ]; then
        echo -e "${YELLOW}[DEBUG]${NC} $1"
    fi
}

# Function to display usage information
show_usage() {
    echo -e "${BLUE}======== CTF CHALLENGE DEPLOYER ========${NC}"
    echo -e "Usage: sudo $0 [up|down] [options]"
    echo -e ""
    echo -e "Commands:"
    echo -e "  up     Start the CTF challenge deployment service"
    echo -e "  down   Stop all services and clean up resources"
    echo -e ""
    echo -e "Options:"
    echo -e "  -v, --verbose   Enable verbose logging output"
    echo -e "  -h, --help      Show this help message"
    echo -e ""
    echo -e "Example:"
    echo -e "  sudo $0 up               # Start the service"
    echo -e "  sudo $0 up --verbose     # Start the service with verbose logging"
    echo -e "  sudo $0 down             # Stop the service"
    exit 1
}

# Parse command line arguments
parse_args() {
    # No arguments provided
    if [ $# -eq 0 ]; then
        log_error "Missing required argument: 'up' or 'down'"
        show_usage
    fi

    # First argument should be the command
    case "$1" in
        up|down)
            COMMAND="$1"
            shift
            ;;
        *)
            log_error "Invalid command: $1"
            show_usage
            ;;
    esac

    # Process options
    while [ $# -gt 0 ]; do
        case "$1" in
            -v|--verbose)
                VERBOSE_MODE=true
                log_debug "Verbose mode enabled"
                ;;
            -h|--help)
                show_usage
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                ;;
        esac
        shift
    done
}

# Function to check for required environment variables
check_required_env_vars() {
    log_info "Checking required environment variables..."
    
    # Load .env file if it exists
    if [ ! -f .env ]; then
        log_error ".env file not found. Deployment cannot continue."
        exit 1
    fi
    
    # Source the .env file to get variables
    source .env
    
    # Define required variables (in groups for readability)
    # Container time settings
    REQUIRED_VARS=(
        # Container time settings
        "LEAVE_TIME" "ADD_TIME"
        
        # Container image and identification
        "IMAGES_NAME" "FLAG"
        
        # Port configuration
        "PORT_IN_CONTAINER" "START_RANGE" "STOP_RANGE" "FLASK_APP_PORT" "DIRECT_TEST_PORT"
        
        # Network configuration
        "NETWORK_NAME" "NETWORK_SUBNET"
        
        # Database settings
        "DB_PATH"
        
        # Challenge details
        "CHALLENGE_TITLE" "CHALLENGE_DESCRIPTION"
        
        # Resource limits
        "CONTAINER_MEMORY_LIMIT" "CONTAINER_SWAP_LIMIT" "CONTAINER_CPU_LIMIT" "CONTAINER_PIDS_LIMIT"
        
        # Security options
        "ENABLE_NO_NEW_PRIVILEGES" "ENABLE_READ_ONLY" "ENABLE_TMPFS" "TMPFS_SIZE"
        
        # Container capabilities
        "DROP_ALL_CAPABILITIES" "CAP_NET_BIND_SERVICE" "CAP_CHOWN"
        
        # Rate limiting
        "MAX_CONTAINERS_PER_HOUR" "RATE_LIMIT_WINDOW"

        # Debug option for flask_app
        "DEBUG_MODE" "BYPASS_CAPTCHA"
    )
    
    # Check each required variable
    MISSING_VARS=()
    for var in "${REQUIRED_VARS[@]}"; do
        # Check if variable is empty
        if [ -z "${!var}" ]; then
            MISSING_VARS+=("$var")
        fi
    done
    
    # If any variables are missing, print error and exit
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        log_error "The following required environment variables are missing or empty:"
        for var in "${MISSING_VARS[@]}"; do
            log_error "  - $var"
        done
        log_error "Please add these variables to your .env file and try again."
        exit 1
    fi
    
    # Validate numeric values
    if ! [[ "$START_RANGE" =~ ^[0-9]+$ ]]; then
        log_error "START_RANGE must be a number"
        exit 1
    fi
    
    if ! [[ "$STOP_RANGE" =~ ^[0-9]+$ ]]; then
        log_error "STOP_RANGE must be a number"
        exit 1
    fi
    
    if [ "$START_RANGE" -ge "$STOP_RANGE" ]; then
        log_error "START_RANGE (${START_RANGE}) must be less than STOP_RANGE (${STOP_RANGE})"
        exit 1
    fi
    
    if ! [[ "$LEAVE_TIME" =~ ^[0-9]+$ ]]; then
        log_error "LEAVE_TIME must be a number"
        exit 1
    fi
    
    if ! [[ "$ADD_TIME" =~ ^[0-9]+$ ]]; then
        log_error "ADD_TIME must be a number"
        exit 1
    fi
    
    # Validate boolean values (convert to lowercase for comparison)
    ENABLE_NO_NEW_PRIVILEGES_LC=$(echo "$ENABLE_NO_NEW_PRIVILEGES" | tr '[:upper:]' '[:lower:]')
    if [[ "$ENABLE_NO_NEW_PRIVILEGES_LC" != "true" && "$ENABLE_NO_NEW_PRIVILEGES_LC" != "false" ]]; then
        log_error "ENABLE_NO_NEW_PRIVILEGES must be 'true' or 'false'"
        exit 1
    fi
    
    ENABLE_READ_ONLY_LC=$(echo "$ENABLE_READ_ONLY" | tr '[:upper:]' '[:lower:]')
    if [[ "$ENABLE_READ_ONLY_LC" != "true" && "$ENABLE_READ_ONLY_LC" != "false" ]]; then
        log_error "ENABLE_READ_ONLY must be 'true' or 'false'"
        exit 1
    fi
    
    ENABLE_TMPFS_LC=$(echo "$ENABLE_TMPFS" | tr '[:upper:]' '[:lower:]')
    if [[ "$ENABLE_TMPFS_LC" != "true" && "$ENABLE_TMPFS_LC" != "false" ]]; then
        log_error "ENABLE_TMPFS must be 'true' or 'false'"
        exit 1
    fi
    
    DROP_ALL_CAPABILITIES_LC=$(echo "$DROP_ALL_CAPABILITIES" | tr '[:upper:]' '[:lower:]')
    if [[ "$DROP_ALL_CAPABILITIES_LC" != "true" && "$DROP_ALL_CAPABILITIES_LC" != "false" ]]; then
        log_error "DROP_ALL_CAPABILITIES must be 'true' or 'false'"
        exit 1
    fi
    
    CAP_NET_BIND_SERVICE_LC=$(echo "$CAP_NET_BIND_SERVICE" | tr '[:upper:]' '[:lower:]')
    if [[ "$CAP_NET_BIND_SERVICE_LC" != "true" && "$CAP_NET_BIND_SERVICE_LC" != "false" ]]; then
        log_error "CAP_NET_BIND_SERVICE must be 'true' or 'false'"
        exit 1
    fi
    
    CAP_CHOWN_LC=$(echo "$CAP_CHOWN" | tr '[:upper:]' '[:lower:]')
    if [[ "$CAP_CHOWN_LC" != "true" && "$CAP_CHOWN_LC" != "false" ]]; then
        log_error "CAP_CHOWN must be 'true' or 'false'"
        exit 1
    fi
    
    log_success "All required environment variables are set."
}

# Check if running as root
check_root_permissions() {
    log_info "Checking for root permissions..."
    
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root or with sudo."
        log_error "Please run with: sudo $0 [up|down] [options]"
        exit 1
    fi
    
    log_success "Running with root permissions."
}

# Check if Docker is installed and running
check_docker() {
    log_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH. Please install Docker and try again."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running or you don't have permission to use it."
        log_info "Try running the script with sudo or add your user to the docker group."
        exit 1
    fi
    
    log_success "Docker is installed and running."
}

# Determine which Docker Compose command to use
detect_docker_compose() {
    log_info "Detecting Docker Compose command..."
    
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
        log_success "Using docker-compose command."
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
        log_success "Using docker compose command."
    else
        log_error "Docker Compose is not installed. Please install Docker Compose and try again."
        exit 1
    fi
}

# Verify environment file exists and contains required variables
check_env_file() {
    log_info "Checking environment file..."
    
    if [ ! -f .env ]; then
        log_error ".env file not found. Deployment cannot continue."
        echo -e "${YELLOW}Please create an .env file with the required configuration before running this script.${NC}"
        echo -e "${YELLOW}See the README.md file for configuration instructions.${NC}"
        exit 1
    else
        log_success ".env file exists."
    fi
    
    # Check for required variables
    log_info "Validating environment variables..."
    
    # Source the .env file to get the variables
    source .env
    
    # List of required variables
    REQUIRED_VARS=("NETWORK_NAME" "NETWORK_SUBNET" "FLASK_APP_PORT" "PORT_IN_CONTAINER" "START_RANGE" "STOP_RANGE")
    MISSING_VARS=0
    
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required variable $var is not set in .env file."
            MISSING_VARS=$((MISSING_VARS+1))
        fi
    done
    
    if [ $MISSING_VARS -gt 0 ]; then
        log_error "$MISSING_VARS required variables are missing. Please check your .env file."
        exit 1
    else
        log_success "All required environment variables are set."
    fi
}

# Check for existing containers with the same name
check_existing_containers() {
    log_info "Checking for existing containers..."
    
    # Source the .env file if not already done
    if [ -z "$COMPOSE_PROJECT_NAME" ]; then
        source .env
    fi
    
    # Check if COMPOSE_PROJECT_NAME is set
    if [ -z "$COMPOSE_PROJECT_NAME" ]; then
        log_warning "COMPOSE_PROJECT_NAME not set in .env file. Container name conflicts may occur."
        return
    fi
    
    # Expected container names
    FLASK_APP_NAME="${COMPOSE_PROJECT_NAME}_flask_app"
    GENERIC_TASK_NAME="${COMPOSE_PROJECT_NAME}_ctf_task"
    
    # Check if containers exist
    EXISTING_CONTAINERS=""
    
    if docker ps -a --format "{{.Names}}" | grep -q "^${FLASK_APP_NAME}$"; then
        EXISTING_CONTAINERS="${EXISTING_CONTAINERS}${FLASK_APP_NAME}, "
    fi
    
    if docker ps -a --format "{{.Names}}" | grep -q "^${GENERIC_TASK_NAME}$"; then
        EXISTING_CONTAINERS="${EXISTING_CONTAINERS}${GENERIC_TASK_NAME}, "
    fi
    
    # Remove trailing comma and space
    EXISTING_CONTAINERS=$(echo "$EXISTING_CONTAINERS" | sed 's/, $//')
    
    if [ ! -z "$EXISTING_CONTAINERS" ]; then
        log_warning "Found existing containers with the same name: $EXISTING_CONTAINERS"
        log_warning "These containers may belong to a previous deployment of this challenge."
        
        read -p "Do you want to remove these containers and continue deployment? (y/n): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Deployment aborted by user."
            exit 1
        fi
        
        log_info "Removing existing containers..."
        
        if docker ps -a --format "{{.Names}}" | grep -q "^${FLASK_APP_NAME}$"; then
            docker rm -f "${FLASK_APP_NAME}" > /dev/null
            log_success "Removed container ${FLASK_APP_NAME}"
        fi
        
        if docker ps -a --format "{{.Names}}" | grep -q "^${GENERIC_TASK_NAME}$"; then
            docker rm -f "${GENERIC_TASK_NAME}" > /dev/null
            log_success "Removed container ${GENERIC_TASK_NAME}"
        fi
    else
        log_success "No existing containers found with the same name."
    fi
}

# Setup lock directory
setup_lock_directory() {
    # Ensure the lock directory exists
    if [ ! -d "$LOCK_DIR" ]; then
        log_info "Creating lock directory: $LOCK_DIR"
        if ! mkdir -p "$LOCK_DIR" 2>/dev/null; then
            log_error "Failed to create lock directory. Check permissions."
            exit 1
        fi
        chmod 1777 "$LOCK_DIR"
    fi
    
    # Check if the directory is writeable
    if [ ! -w "$LOCK_DIR" ]; then
        log_error "Lock directory $LOCK_DIR is not writeable. Please fix permissions."
        exit 1
    fi
    
    log_success "Lock directory is ready: $LOCK_DIR"
}

# Create a unique instance identifier based on directory path
get_instance_id() {
    # Create a unique ID based on the absolute path of this deployer
    echo "$(realpath "$(pwd)")" | md5sum | cut -d' ' -f1 | cut -c1-16
}

# Check for port range conflicts with existing lock files
check_port_range_conflicts() {
    log_info "Checking for port range conflicts with other deployers..."
    
    # Get our instance ID
    local INSTANCE_ID=$(get_instance_id)
    
    # Pattern for lock files: ctf_port_STARTRANGE-STOPRANGE_INSTANCEID
    local THIS_LOCK_FILE="${LOCK_DIR}/ctf_port_${START_RANGE}-${STOP_RANGE}_${INSTANCE_ID}"
    
    # Check for overlapping port ranges from other instances
    local CONFLICT=false
    local CONFLICT_DETAILS=""
    
    # Get all port range lock files
    local LOCK_FILES=$(ls ${LOCK_DIR}/ctf_port_*-*_* 2>/dev/null || true)
    
    for lock_file in $LOCK_FILES; do
        # Extract information from filename
        local file_basename=$(basename "$lock_file")
        local other_instance_id=$(echo "$file_basename" | sed -E 's/ctf_port_[0-9]+-[0-9]+_([^_]+)/\1/')
        
        # Skip our own instance if it exists
        if [ "$other_instance_id" = "$INSTANCE_ID" ]; then
            continue
        fi
        
        # Extract port range
        local port_range=$(echo "$file_basename" | sed -E 's/ctf_port_([0-9]+-[0-9]+)_.*/\1/')
        local other_start=$(echo "$port_range" | cut -d'-' -f1)
        local other_stop=$(echo "$port_range" | cut -d'-' -f2)
        
        # Check if the lock file refers to an actual deployer that still exists
        if [ -f "$lock_file" ]; then
            local other_path=$(cat "$lock_file" 2>/dev/null | grep "^PATH=" | cut -d'=' -f2)
            
            if [ ! -d "$other_path" ]; then
                log_info "Found stale lock file for non-existent path: $other_path. Removing it."
                rm -f "$lock_file" 2>/dev/null
                continue
            fi
            
            # Check for port range overlap
            if [ "$START_RANGE" -le "$other_stop" ] && [ "$STOP_RANGE" -ge "$other_start" ]; then
                CONFLICT=true
                CONFLICT_DETAILS="Port range ($START_RANGE-$STOP_RANGE) overlaps with ($other_start-$other_stop) from $other_path"
                break
            fi
        fi
    done
    
    # If conflict found, report and exit
    if [ "$CONFLICT" = true ]; then
        log_error "Port range conflict detected!"
        log_error "$CONFLICT_DETAILS"
        log_error "Please update your START_RANGE and STOP_RANGE in .env to avoid conflicts"
        exit 1
    fi
    
    # Create our lock file
    log_info "Registering port range ($START_RANGE-$STOP_RANGE) in lock system..."
    
    # Write information to the lock file
    mkdir -p data
    echo "PORT_RANGE=${START_RANGE}-${STOP_RANGE}" > "$THIS_LOCK_FILE"
    echo "PATH=$(realpath "$(pwd)")" >> "$THIS_LOCK_FILE"
    echo "TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$THIS_LOCK_FILE"
    echo "INSTANCE_ID=${INSTANCE_ID}" >> "$THIS_LOCK_FILE"
    
    # Remember lock file for cleanup
    echo "$THIS_LOCK_FILE" > "./data/lock_file.txt"
    
    log_success "Port range successfully registered."
}

# Check for network conflicts
check_network_conflicts() {
    log_info "Checking for network conflicts..."
    
    # Setup the lock directory and check for port range conflicts
    setup_lock_directory
    check_port_range_conflicts
    
    # Check if our network already exists
    if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        log_info "Network $NETWORK_NAME already exists."
        
        # Check if network has containers attached
        if docker network inspect "$NETWORK_NAME" | grep -q '"Containers": {}'; then
            log_info "Network $NETWORK_NAME has no attached containers. Will reuse."
        else
            CONTAINERS=$(docker network inspect "$NETWORK_NAME" | grep -A 15 "Containers" | grep "Name" | cut -d'"' -f4)
            log_warning "Network $NETWORK_NAME has the following containers attached:"
            echo "$CONTAINERS"
            
            # Instead of error, ask user if they want to delete the containers and network
            read -p "Do you want to remove these containers and the network to continue? (y/n): " -n 1 -r
            echo
            
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                log_info "Removing attached containers and network..."
                
                # Get container IDs from the network
                CONTAINER_IDS=$(docker network inspect "$NETWORK_NAME" | grep -A 65535 "Containers" |grep -v config-hash |grep -v EndpointID| grep -o '"[a-f0-9]\{64\}"' | tr -d '"')
                # Remove each container
                for container_id in $CONTAINER_IDS; do
                    log_info "Removing container $container_id..."
                    if docker rm -f "$container_id" > /dev/null; then
                        log_success "Container removed successfully."
                    else
                        log_warning "Failed to remove container $container_id."
                    fi
                done
                
                # Remove the network
                log_info "Removing network $NETWORK_NAME..."
                if docker network rm -f "$NETWORK_NAME" > /dev/null; then
                    log_success "Network removed successfully."
                else
                    log_error "Failed to remove network. Please check if all containers are properly disconnected."
                    exit 1
                fi
            else
                log_error "Deployment aborted by user. Please remove the containers manually or use a different network name."
                exit 1
            fi
        fi
    else
        log_info "Network $NETWORK_NAME does not exist yet."
    fi
    
    log_success "Network conflict check completed."
}

# Check for port conflicts
check_port_conflicts() {
    log_info "Checking for port conflicts..."
    
    PORT_CONFLICTS=false
    CONFLICT_DETAILS=""
    
    # Check FLASK_APP_PORT
    if netstat -tuln 2>/dev/null | grep -q ":$FLASK_APP_PORT " || ss -tuln 2>/dev/null | grep -q ":$FLASK_APP_PORT "; then
        PORT_CONFLICTS=true
        CONFLICT_DETAILS="Flask application port $FLASK_APP_PORT is already in use"
    fi
    
    # Check DIRECT_TEST_PORT if set
    if [ ! -z "$DIRECT_TEST_PORT" ]; then
        if netstat -tuln 2>/dev/null | grep -q ":$DIRECT_TEST_PORT " || ss -tuln 2>/dev/null | grep -q ":$DIRECT_TEST_PORT "; then
            PORT_CONFLICTS=true
            CONFLICT_DETAILS="Direct test port $DIRECT_TEST_PORT is already in use"
        fi
    fi
    
    # Fail immediately if port conflicts are detected
    if [ "$PORT_CONFLICTS" = true ]; then
        log_error "Port conflict detected: $CONFLICT_DETAILS"
        log_error "Please update your port configuration in .env to use available ports."
        exit 1
    fi
    
    # Check for conflicts in port range
    # Sample a few ports to avoid checking thousands
    SAMPLE_INTERVAL=$((($STOP_RANGE - $START_RANGE) / 10))
    SAMPLE_INTERVAL=$((SAMPLE_INTERVAL > 0 ? SAMPLE_INTERVAL : 1))
    
    PORT_RANGE_CONFLICT=false
    CONFLICTING_PORT=""
    
    for port in $(seq $START_RANGE $SAMPLE_INTERVAL $STOP_RANGE); do
        # Check if port is in use by Docker containers
        if docker ps --format "{{.Ports}}" | grep -q ":$port->"; then
            PORT_RANGE_CONFLICT=true
            CONFLICTING_PORT=$port
            break
        fi
    done
    
    # Port range conflicts are critical - fail immediately
    if [ "$PORT_RANGE_CONFLICT" = true ]; then
        log_error "Port $CONFLICTING_PORT in range $START_RANGE-$STOP_RANGE is already used by a Docker container."
        log_error "Please update your START_RANGE and STOP_RANGE in .env to use a non-conflicting port range."
        exit 1
    fi
    
    log_success "No obvious port conflicts detected."
}

clean_data_directory() {
    log_info "Cleaning data directory..."
    
    # Get DB_PATH from .env if not already sourced
    if [ -z "$DB_PATH" ]; then
        source .env
    fi
    
    # Check if data directory exists
    if [ ! -d "$(dirname "$DB_PATH")" ]; then
        log_info "Data directory doesn't exist yet. Nothing to clean."
        return
    fi
    
    # Remove the containers database if it exists
    if [ -f "$DB_PATH" ]; then
        log_info "Removing containers database at $DB_PATH"
        rm -f "$DB_PATH"
        log_success "Containers database cleaned."
    else
        log_info "No containers database found at $DB_PATH"
    fi
    
    # Clean up any lock files in the data directory
    if [ -f "./data/lock_file.txt" ]; then
        local lock_file=$(cat "./data/lock_file.txt")
        if [ -f "$lock_file" ]; then
            log_info "Removing port range lock file..."
            rm -f "$lock_file" 2>/dev/null
            log_success "Lock file removed."
        fi
        rm -f "./data/lock_file.txt"
    fi
    
    # Additional cleanup of temporary files if needed
    find "./data" -name "*.tmp" -type f -delete 2>/dev/null
    
    log_success "Data directory cleaned successfully."
}

# Safely clean up only our network if it exists and has no containers
safely_cleanup_network() {
    log_info "Safely cleaning up own network (if needed)..."
    
    # Check if network exists
    if docker network ls --format "{{.Name}}" | grep -q "^${NETWORK_NAME}$"; then
        # Check if network has containers attached
        if docker network inspect "$NETWORK_NAME" | grep -q '"Containers": {}'; then
            log_info "Removing unused network $NETWORK_NAME."
            if docker network rm "$NETWORK_NAME" &>/dev/null; then
                log_success "Successfully removed network $NETWORK_NAME."
            else
                log_warning "Failed to remove network $NETWORK_NAME. Will try to reuse it."
            fi
        else
            log_info "Network $NETWORK_NAME has attached containers. Keeping it."
        fi
    else
        log_info "Network $NETWORK_NAME does not exist yet."
    fi
}

# Check if required directories exist
check_directories() {
    log_info "Checking required directories..."
    
    # Check if data directory exists, create if not
    if [ ! -d "data" ]; then
        mkdir -p data
        log_success "Created data directory."
    fi
}

# Build the Docker images with no-cache option
build_images() {
    log_info "Building Docker images with --no-cache option..."
    
    if $DOCKER_COMPOSE build --no-cache; then
        log_success "Docker images built successfully."
    else
        log_error "Failed to build Docker images."
        exit 1
    fi
}

# Start the containers
start_containers() {
    log_info "Starting Docker containers..."
    
    # Let Docker Compose create the network and start the containers
    if $DOCKER_COMPOSE up -d; then
        log_success "Docker containers started successfully."
    else
        log_error "Failed to start Docker containers."
        exit 1
    fi
}

# Check if services are running properly
check_services() {
    log_info "Checking if services are running properly..."
    
    # Wait a bit for services to initialize
    sleep 5
    
    # Check if flask_app container is running
    if $DOCKER_COMPOSE ps | grep -q flask_app.*Up; then
        log_success "Flask application is running."
    else
        log_warning "Flask application may not be running correctly. Check the logs for details."
    fi
    
    # Check if generic_ctf_task container is running
    if $DOCKER_COMPOSE ps | grep -q generic_ctf_task.*Up; then
        log_success "Challenge task is running."
    else
        log_warning "Challenge task may not be running correctly. Check the logs for details."
    fi
}

# Verify ports are accessible
check_ports() {
    log_info "Verifying port accessibility..."
    
    # Check if ports in use
    if netstat -tuln 2>/dev/null | grep -q ":$FLASK_APP_PORT " || ss -tuln 2>/dev/null | grep -q ":$FLASK_APP_PORT "; then
        log_success "Flask application port $FLASK_APP_PORT is accessible."
    else
        log_warning "Flask application port $FLASK_APP_PORT might not be accessible. Check firewall settings."
    fi
    
    if netstat -tuln 2>/dev/null | grep -q ":$DIRECT_TEST_PORT " || ss -tuln 2>/dev/null | grep -q ":$DIRECT_TEST_PORT "; then
        log_success "Direct test port $DIRECT_TEST_PORT is accessible."
    else
        log_warning "Direct test port $DIRECT_TEST_PORT might not be accessible. Check firewall settings."
    fi
}

# Print access information
print_access_info() {
    echo -e "\n${GREEN}======== DEPLOYMENT SUCCESSFUL ========${NC}"
    echo -e "${GREEN}CTF Challenge Deployer is now running!${NC}"
    echo -e "${YELLOW}Access the deployer interface:${NC} http://localhost:$FLASK_APP_PORT"
    echo -e "${YELLOW}Access the challenge directly:${NC} http://localhost:$DIRECT_TEST_PORT"
    echo -e "${BLUE}For more information, check the README.md file.${NC}"
    echo -e "${YELLOW}To stop the service:${NC} sudo $0 down"
    echo -e "${YELLOW}To view logs:${NC} $DOCKER_COMPOSE logs -f"
}

# Print recommendations for multi-instance setup
print_multi_instance_tips() {
    if [ "$VERBOSE_MODE" = true ]; then
        echo -e "\n${BLUE}======== MULTI-INSTANCE TIPS ========${NC}"
        echo -e "When running multiple deployer instances on the same host, ensure:"
        echo -e "1. Each instance uses a different ${YELLOW}NETWORK_NAME${NC} and ${YELLOW}NETWORK_SUBNET${NC} in .env"
        echo -e "2. Each instance uses a different ${YELLOW}FLASK_APP_PORT${NC} and ${YELLOW}DIRECT_TEST_PORT${NC}"
        echo -e "3. Each instance has non-overlapping ${YELLOW}START_RANGE${NC} and ${YELLOW}STOP_RANGE${NC} port ranges"
        echo -e "4. Use separate data directories for each instance to avoid database conflicts"
        echo -e "5. Each instance uses a unique ${YELLOW}COMPOSE_PROJECT_NAME${NC} in .env"
    fi
}

# Show logs for immediate feedback
show_logs() {
    echo -e "${BLUE}======== CONTAINER LOGS ========${NC}"
    $DOCKER_COMPOSE logs -f
}

# Clean up resources when shutting down
shutdown_services() {
    log_info "Shutting down CTF Deployer services..."
    
    # Stop and remove containers
    $DOCKER_COMPOSE down
    
    # Remove the lock file
    if [ -f "./data/lock_file.txt" ]; then
        local lock_file=$(cat "./data/lock_file.txt")
        if [ -f "$lock_file" ]; then
            log_info "Removing port range lock file..."
            rm -f "$lock_file" 2>/dev/null
        fi
    fi
    
    log_success "Services shut down successfully."
}

# Handle clean shutdown with signal handler
cleanup() {
    echo ""
    log_info "Caught shutdown signal. Exiting gracefully..."
    # Do not remove lock files on CTRL+C, only on explicit shutdown
    exit 0
}

# Main function
# Main function
main() {
    echo -e "${BLUE}======== CTF CHALLENGE DEPLOYER ========${NC}"
    
    # Parse command line arguments
    parse_args "$@"
    
    # Show starting message only if verbose mode is enabled
    if [ "$VERBOSE_MODE" = true ]; then
        log_info "Starting deployment process..."
    fi
    
    # Check root permissions first for any operation
    check_root_permissions
    
    # Process the command
    case "$COMMAND" in
        up)
            # Register signal handler
            trap cleanup SIGINT SIGTERM
            
           # Run pre-checks for all required environment variables
            check_required_env_vars
            
            # Run deployment steps
            check_docker
            detect_docker_compose
            check_env_file
            check_existing_containers
            clean_data_directory
            # Important: First check network/port conflicts to validate lock files
            check_network_conflicts
            check_port_conflicts
            
            # Clean the containers database
            
            # Continue with deployment
            safely_cleanup_network
            check_directories
            build_images
            start_containers
            check_services
            check_ports
            print_access_info
            print_multi_instance_tips
            
            # Offer to show logs
            echo ""
            read -p "Do you want to view container logs? (y/n): " show_logs_choice
            if [[ "$show_logs_choice" =~ ^[Yy]$ ]]; then
                show_logs
            fi
            
            if [ "$VERBOSE_MODE" = true ]; then
                log_success "Deployment completed successfully!"
            fi
            ;;
            
        down)
            # Initialize Docker compose before shutdown
            check_docker
            detect_docker_compose
            
            # Now shutdown services
            shutdown_services
            
            # Clean data directory after shutting down
            clean_data_directory
            
            echo -e "${GREEN}Services shut down successfully.${NC}"
            ;;
            
        *)
            log_error "Invalid command: $COMMAND"
            show_usage
            ;;
    esac
}
# Execute main function with all arguments
main "$@"
