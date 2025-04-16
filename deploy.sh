#!/bin/bash

# Terminal colors for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Command and options
COMMAND=""
VERBOSE_MODE=false
SKIP_TESTS=false
RUN_POST_DEPLOY_TESTS=false
RUN_UNIT_TESTS=false

# Directory for virtual environment
VENV_DIR=".venv"

# Directory for lock files
LOCK_DIR="/var/lock/ctf_deployer"

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
    echo -e "  -v, --verbose        Enable verbose logging output"
    echo -e "  -s, --skip-tests     Skip pre-deployment validation tests"
    echo -e "  -p, --post-tests     Run post-deployment tests after starting services"
    echo -e "  -u, --unit-tests     Run unit tests"
    echo -e "  -h, --help           Show this help message"
    echo -e ""
    echo -e "Examples:"
    echo -e "  sudo $0 up                      # Start the service with pre-deployment tests"
    echo -e "  sudo $0 up -v                   # Start with verbose logging"
    echo -e "  sudo $0 up -s                   # Start without running tests"
    echo -e "  sudo $0 up -p                   # Start and run post-deployment tests"
    echo -e ""
    exit 1
}

# Print styled messages based on level
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
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                ;;
            -p|--post-tests)
                RUN_POST_DEPLOY_TESTS=true
                ;;
            -u|--unit-tests)
                RUN_UNIT_TESTS=true
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

# Check if running as root
check_root_permissions() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root or with sudo."
        log_error "Please run with: sudo $0 [up|down] [options]"
        exit 1
    fi
    
    log_success "Running with root permissions."
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

# Create a unique instance identifier based on hostname and path
get_instance_id() {
    local path_hash=$(echo "$(hostname):$(pwd)" | md5sum | cut -d' ' -f1)
    echo "${path_hash:0:16}"  # Use first 16 characters of hash
}

# Check for port range conflicts with existing lock files
check_port_range_conflicts() {
    log_info "Checking for port range conflicts with other deployers..."
    
    # Get our instance ID
    local INSTANCE_ID=$(get_instance_id)
    
    # Get port range from environment
    local START_RANGE=$(grep START_RANGE .env | cut -d= -f2)
    local STOP_RANGE=$(grep STOP_RANGE .env | cut -d= -f2)
    
    if [ -z "$START_RANGE" ] || [ -z "$STOP_RANGE" ]; then
        log_error "START_RANGE or STOP_RANGE is not set in .env"
        exit 1
    fi
    
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

# Function to clean up lock file on exit
cleanup_lock_file() {
    if [ -f "./data/lock_file.txt" ]; then
        local lock_file=$(cat "./data/lock_file.txt")
        if [ -f "$lock_file" ]; then
            log_info "Removing port range lock file..."
            rm -f "$lock_file"
        fi
        rm -f "./data/lock_file.txt"
    fi
}

# Ensure virtual environment exists and required packages are installed
ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Virtual environment not found. Creating one at $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
        if [ $? -ne 0 ]; then
            log_error "Failed to create virtual environment. Make sure python3-venv is installed."
            log_error "  On Ubuntu/Debian: sudo apt-get install python3-venv"
            log_error "  On CentOS/RHEL: sudo yum install python3-virtualenv"
            exit 1
        fi
        
        log_info "Installing required packages..."
        "$VENV_DIR/bin/pip" install -r tests/requirements.txt
        
        if [ $? -ne 0 ]; then
            log_error "Failed to install required packages."
            exit 1
        fi
        
        log_success "Virtual environment created and packages installed."
    else
        # Verify venv has required packages
        if [ ! -f "$VENV_DIR/bin/pytest" ]; then
            log_info "Installing required packages in existing virtual environment..."
            "$VENV_DIR/bin/pip" install -r tests/requirements.txt
            
            if [ $? -ne 0 ]; then
                log_error "Failed to install required packages."
                exit 1
            fi
        fi
    fi
}

# Run pre-deployment tests with venv
run_pre_deploy_tests() {
    echo -e "${BLUE}Running pre-deployment validation tests...${NC}"
    
    # Ensure virtual environment exists
    ensure_venv
    
    # Create a temporary file to store test output
    TEMP_OUTPUT=$(mktemp)
    
    # Run the tests with venv and capture output
    "$VENV_DIR/bin/python" tests/run_tests.py $([[ "$VERBOSE_MODE" == "true" ]] && echo "-v") > "$TEMP_OUTPUT" 2>&1
    TEST_STATUS=$?
    
    # Process the output and add colors
    while IFS= read -r line; do
        if [[ $line == *"ERROR"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"INFO"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ $line == *"passed!"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"failed!"* ]]; then
            echo -e "${RED}$line${NC}"
        else
            echo "$line"
        fi
    done < "$TEMP_OUTPUT"
    
    # Clean up temp file
    rm -f "$TEMP_OUTPUT"
    
    # Return the original exit status
    if [ $TEST_STATUS -eq 0 ]; then
        echo -e "${GREEN}All pre-deployment tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some pre-deployment tests failed. Deployment cannot continue.${NC}"
        echo -e "${RED}Please fix the issues and try again.${NC}"
        return 1
    fi
}

# Run unit tests with venv
run_unit_tests() {
    echo -e "${BLUE}Running unit tests...${NC}"
    
    # Ensure virtual environment exists
    ensure_venv
    
    # Create a temporary file to store test output
    TEMP_OUTPUT=$(mktemp)
    
    # Run the tests with venv and capture output
    "$VENV_DIR/bin/python" tests/run_tests.py --unit-tests $([[ "$VERBOSE_MODE" == "true" ]] && echo "-v") > "$TEMP_OUTPUT" 2>&1
    TEST_STATUS=$?
    
    # Process the output and add colors
    while IFS= read -r line; do
        if [[ $line == *"ERROR"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"INFO"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ $line == *"passed!"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"failed!"* ]]; then
            echo -e "${RED}$line${NC}"
        else
            echo "$line"
        fi
    done < "$TEMP_OUTPUT"
    
    # Clean up temp file
    rm -f "$TEMP_OUTPUT"
    
    # Return the original exit status
    if [ $TEST_STATUS -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# Run post-deployment tests with venv
run_post_deploy_tests() {
    echo -e "${BLUE}Running post-deployment tests...${NC}"
    
    # Ensure virtual environment exists
    ensure_venv
    
    # Create a temporary file to store test output
    TEMP_OUTPUT=$(mktemp)
    
    # Run the tests with venv and capture output
    "$VENV_DIR/bin/python" tests/run_tests.py --post-deploy $([[ "$VERBOSE_MODE" == "true" ]] && echo "-v") > "$TEMP_OUTPUT" 2>&1
    TEST_STATUS=$?
    
    # Process the output and add colors
    while IFS= read -r line; do
        if [[ $line == *"ERROR"* ]]; then
            echo -e "${RED}$line${NC}"
        elif [[ $line == *"WARNING"* ]]; then
            echo -e "${YELLOW}$line${NC}"
        elif [[ $line == *"INFO"* ]]; then
            echo -e "${BLUE}$line${NC}"
        elif [[ $line == *"passed!"* ]]; then
            echo -e "${GREEN}$line${NC}"
        elif [[ $line == *"failed!"* ]]; then
            echo -e "${RED}$line${NC}"
        else
            echo "$line"
        fi
    done < "$TEMP_OUTPUT"
    
    # Clean up temp file
    rm -f "$TEMP_OUTPUT"
    
    # Return the original exit status, but don't fail the deployment
    if [ $TEST_STATUS -eq 0 ]; then
        echo -e "${GREEN}All post-deployment tests passed!${NC}"
    else
        echo -e "${YELLOW}Some post-deployment tests failed. The service may still be running, but some functionality might be impaired.${NC}"
    fi
    return 0  # Always return success for post-deployment tests
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

# Build the Docker images
build_images() {
    log_info "Building Docker images..."
    
    if $DOCKER_COMPOSE build; then
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
    sleep 3
    
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
    
    # Get port values from .env file
    FLASK_APP_PORT=$(grep FLASK_APP_PORT .env | cut -d= -f2)
    DIRECT_TEST_PORT=$(grep DIRECT_TEST_PORT .env | cut -d= -f2)
    
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
    # Get port values from .env file
    FLASK_APP_PORT=$(grep FLASK_APP_PORT .env | cut -d= -f2)
    DIRECT_TEST_PORT=$(grep DIRECT_TEST_PORT .env | cut -d= -f2)
    
    echo -e "\n${GREEN}======== DEPLOYMENT SUCCESSFUL ========${NC}"
    echo -e "${GREEN}CTF Challenge Deployer is now running!${NC}"
    echo -e "${YELLOW}Access the deployer interface:${NC} http://localhost:$FLASK_APP_PORT"
    echo -e "${YELLOW}Access the challenge directly:${NC} http://localhost:$DIRECT_TEST_PORT"
    echo -e "${BLUE}For more information, check the README.md file.${NC}"
    echo -e "${YELLOW}To stop the service:${NC} sudo $0 down"
    echo -e "${YELLOW}To view logs:${NC} $DOCKER_COMPOSE logs -f"
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
    
    log_success "Services shut down successfully."
}

# Main function
main() {
    echo -e "${BLUE}======== CTF CHALLENGE DEPLOYER ========${NC}"
    
    # Parse command line arguments
    parse_args "$@"
    
    # Show starting message
    log_info "Starting CTF Challenge Deployer..."
    
    # Check root permissions first for any operation
    check_root_permissions
    
    # Setup lock directory
    setup_lock_directory
    
    # Register cleanup handler for lock file
    trap cleanup_lock_file EXIT
    
    # Process the command
    case "$COMMAND" in
        up)
            # Check for port range conflicts with other deployers
            check_port_range_conflicts
            
            # Run unit tests if requested
            if [ "$RUN_UNIT_TESTS" = true ]; then
                if ! run_unit_tests; then
                    exit 1
                fi
            fi
            
            # Run pre-deployment tests unless skipped
            if [ "$SKIP_TESTS" = false ]; then
                if ! run_pre_deploy_tests; then
                    exit 1
                fi
            else
                log_warning "Pre-deployment tests skipped. Proceeding with deployment..."
            fi
            
            # Deploy the application
            detect_docker_compose
            build_images
            start_containers
            check_services
            check_ports
            print_access_info
            
            # Run post-deployment tests if requested
            if [ "$RUN_POST_DEPLOY_TESTS" = true ]; then
                run_post_deploy_tests
                # Continue even if tests fail
            fi
            
            # Offer to show logs
            echo ""
            read -p "Do you want to view container logs? (y/n): " show_logs_choice
            if [[ "$show_logs_choice" =~ ^[Yy]$ ]]; then
                show_logs
            fi
            ;;
            
        down)
            # Initialize Docker compose before shutdown
            detect_docker_compose
            
            # Now shutdown services
            shutdown_services
            
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
