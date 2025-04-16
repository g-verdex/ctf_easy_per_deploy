# CTF Deployer Makefile

.PHONY: all test test-env test-unit test-post deploy clean help

# Default target
all: help

# Build dependencies for Python test framework
test-deps:
	@echo "Installing Python test dependencies..."
	pip3 install -r tests/requirements.txt

# Run pre-deployment validation tests
test-env:
	@echo "Running pre-deployment validation tests..."
	python3 ./tests/run_tests.py -v

# Run unit tests
test-unit:
	@echo "Running unit tests..."
	python3 ./tests/run_tests.py --unit-tests -v

# Run post-deployment tests (requires running service)
test-post:
	@echo "Running post-deployment tests..."
	python3 ./tests/run_tests.py --post-deploy -v

# Run all tests (pre-deployment and unit tests)
test: test-env test-unit
	@echo "All tests completed"

# Deploy the service with sudo
deploy:
	@echo "Deploying CTF challenge service..."
	sudo ./deploy.sh up

# Stop the service with sudo
clean:
	@echo "Stopping CTF challenge service..."
	sudo ./deploy.sh down

# Display help information
help:
	@echo "CTF Deployer Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  test-deps    - Install Python test dependencies"
	@echo "  test-env     - Run pre-deployment validation tests"
	@echo "  test-unit    - Run unit tests"
	@echo "  test-post    - Run post-deployment tests (requires running service)"
	@echo "  test         - Run all tests (pre-deployment and unit)"
	@echo "  deploy       - Deploy the service"
	@echo "  clean        - Stop the service"
	@echo "  help         - Display this help information"
	@echo ""
	@echo "Usage examples:"
	@echo "  make test-deps   # Install test dependencies"
	@echo "  make test-env    # Run environment tests"
	@echo "  make deploy      # Deploy the service"
	@echo "  make test-post   # Test the running service"
	@echo "  make clean       # Stop the service"
