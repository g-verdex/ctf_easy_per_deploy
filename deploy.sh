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

# Virtual environment settings
VENV_DIR=".venv"

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

# Ensure the virtual environment is set up
ensure_venv() {
    # Check if we need to set up the virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        log_info "Virtual environment not found. Setting up test environment..."
        
        # Check if the setup script exists
        if [ ! -f "tests/setup_tests.sh" ]; then
            log_error "Test setup script not found at tests/setup_tests.sh"
            log_error "Please ensure the script exists and is executable."
            return 1
        fi
        
        # Make it executable if needed
        chmod +x tests/setup_tests.sh
        
        # Run the setup script
        (cd tests && ./setup_tests.sh)
        
        if [ $? -ne 0 ]; then
            log_error "Failed to set up test environment."
            return 1
        fi
        
        log_success "Test environment set up successfully."
    fi
    
    return 0
}

# Run tests with virtual environment
run_tests_with_venv() {
    # $1: test command flags, $2: action description
    
    # Ensure venv exists
    if ! ensure_venv; then
        return 1
    fi
    
    log_info "Running $2..."
    
    # Activate virtual environment in a subshell and run tests
    (
        source "$VENV_DIR/bin/activate"
        python tests/run_tests.py $1
        exit $?
    )
    
    return $?
}

# Run pre-deployment tests
run_pre_deploy_tests() {
    # Build test flags
    TEST_FLAGS=""
    if [ "$VERBOSE_MODE" = true ]; then
        TEST_FLAGS="$TEST_FLAGS -v"
    fi
    
    # Run the tests
    if run_tests_with_venv "$TEST_FLAGS" "pre-deployment validation tests"; then
        log_success "All pre-deployment tests passed!"
        return 0
    else
        log_error "Some pre-deployment tests failed. Deployment cannot continue."
        log_error "Please fix the issues and try again."
        return 1
    fi
}

# Run unit tests
run_unit_tests() {
    # Build test flags
    TEST_FLAGS="--unit-tests"
    if [ "$VERBOSE_MODE" = true ]; then
        TEST_FLAGS="$TEST_FLAGS -v"
    fi
    
    # Run the tests
    if run_tests_with_venv "$TEST_FLAGS" "unit tests"; then
        log_success "All unit tests passed!"
        return 0
    else
        log_error "Some unit tests failed."
        return 1
    fi
}

# Run post-deployment tests
run_post_deploy_tests() {
    # Build test flags
    TEST_FLAGS="--post-deploy"
    if [ "$VERBOSE_MODE" = true ]; then
        TEST_FLAGS="$TEST_FLAGS -v"
    fi
    
    # Run the tests
    if run_tests_with_venv "$TEST_FLAGS" "post-deployment tests"; then
        log_success "All post-deployment tests passed!"
        return 0
    else
        log_warning "Some post-deployment tests failed."
        log_warning "The service may still be running, but some functionality might be impaired."
        return 1
    fi
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
    
    # Process the command
    case "$COMMAND" in
        up)
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
