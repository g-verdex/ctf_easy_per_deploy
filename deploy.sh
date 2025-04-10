#!/bin/bash

# Terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directory for lock files
LOCK_DIR="/var/lock/ctf_deployer"

# Print styled messages
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if running as root
check_root_permissions() {
    log_info "Checking for root permissions..."
    
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root or with sudo."
        log_error "Please run with: sudo $0"
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
    GENERIC_TASK_NAME="${COMPOSE_PROJECT_NAME}_generic_ctf_task"
    
    # Check if containers exist
    EXISTING_CONTAINERS=""
    
    if docker ps -a --format "{{.Names}}" | grep -q "^${FLASK_APP_NAME}$"; then
        EXISTING_CONTAINERS="${EXISTING_CONTAINERS}${FLASK_APP_NAME}, "
    fi
    
    if dockeps -a --format "{{.Names}}" | grep -q "^${GENERIC_TASK_NAME}$"; then
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

# Function to check if two subnets overlap
check_subnet_overlap() {
    local subnet1=$1
    local subnet2=$2
    
    # Extract network address and prefix for first subnet
    local net1=$(echo $subnet1 | cut -d'/' -f1)
    local prefix1=$(echo $subnet1 | cut -d'/' -f2)
    
    # Extract network address and prefix for second subnet
    local net2=$(echo $subnet2 | cut -d'/' -f1)
    local prefix2=$(echo $subnet2 | cut -d'/' -f2)
    
    # Convert IP addresses to decimal
    local IFS='.'
    read -r -a oct1 <<< "$net1"
    read -r -a oct2 <<< "$net2"
    
    # Calculate decimal representations
    local dec1=$(( (${oct1[0]} << 24) + (${oct1[1]} << 16) + (${oct1[2]} << 8) + ${oct1[3]} ))
    local dec2=$(( (${oct2[0]} << 24) + (${oct2[1]} << 16) + (${oct2[2]} << 8) + ${oct2[3]} ))
    
    # Calculate subnet masks
    local mask1=$(( 0xffffffff << (32 - $prefix1) & 0xffffffff ))
    local mask2=$(( 0xffffffff << (32 - $prefix2) & 0xffffffff ))
    
    # Calculate network addresses
    local net1_addr=$(( $dec1 & $mask1 ))
    local net2_addr=$(( $dec2 & $mask2 ))
    
    # Calculate broadcast addresses
    local bcast1=$(( $net1_addr | ~$mask1 & 0xffffffff ))
    local bcast2=$(( $net2_addr | ~$mask2 & 0xffffffff ))
    
    # Check for overlap
    # If start of one network is before end of another AND
    # end of one network is after start of another
    if [ $net1_addr -le $bcast2 ] && [ $bcast1 -ge $net2_addr ]; then
        return 0  # Subnets overlap
    else
        return 1  # Subnets don't overlap
    fi
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
        
        # Check for subnet conflicts with existing networks (rest of function remains unchanged)
        # ...
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
    
    # Default values if not set
    FLASK_APP_PORT=${FLASK_APP_PORT:-6664}
    DIRECT_TEST_PORT=${DIRECT_TEST_PORT:-44444}
    
    # Check if ports are in use
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
    echo -e "\n${BLUE}======== MULTI-INSTANCE TIPS ========${NC}"
    echo -e "When running multiple deployer instances on the same host, ensure:"
    echo -e "1. Each instance uses a different ${YELLOW}NETWORK_NAME${NC} and ${YELLOW}NETWORK_SUBNET${NC} in .env"
    echo -e "2. Each instance uses a different ${YELLOW}FLASK_APP_PORT${NC} and ${YELLOW}DIRECT_TEST_PORT${NC}"
    echo -e "3. Each instance has non-overlapping ${YELLOW}START_RANGE${NC} and ${YELLOW}STOP_RANGE${NC} port ranges"
    echo -e "4. Use separate data directories for each instance to avoid database conflicts"
    echo -e "5. Each instance uses a unique ${YELLOW}COMPOSE_PROJECT_NAME${NC} in .env"
}

# Show logs for immediate feedback
show_logs() {
    log_info "Displaying container logs (press Ctrl+C to exit logs)..."
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
main() {
    echo -e "${BLUE}======== CTF CHALLENGE DEPLOYER ========${NC}"
    log_info "Starting deployment process..."
    
    # Check for down command
    if [ "$1" = "down" ]; then
        shutdown_services
        exit 0
    fi
    
    # Check root permissions first
    check_root_permissions
    
    # Register signal handler
    trap cleanup SIGINT SIGTERM
    
    # Run deployment steps
    check_docker
    detect_docker_compose
    check_env_file
    
    # Check for existing containers with the same name
    check_existing_containers
    
    check_network_conflicts
    check_port_conflicts
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
    
    log_success "Deployment completed successfully!"
}

# Execute main function with all arguments
main "$@"r
 
