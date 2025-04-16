# CTF Deployer Testing Framework Integration Guide

## Overview

This document describes the new testing framework for the CTF Deployer project and provides instructions for integrating it into your CI/CD pipeline. The framework includes pre-deployment validation tests, unit tests, API tests, and load tests, all organized in a structured directory hierarchy.

## Test Framework Structure

```
tests/
├── __init__.py                   # Makes tests a Python package
├── run_tests.py                  # Central test runner script
├── setup_tests.sh                # Sets up test environment and dependencies
├── requirements.txt              # Test-specific dependencies
├── conftest.py                   # Pytest configuration and shared fixtures
├── environment/                  # Pre-deployment validation tests
│   ├── __init__.py
│   ├── test_config.py            # Configuration validation
│   ├── test_docker.py            # Docker environment checks
│   ├── test_network.py           # Network validation
│   ├── test_port.py              # Port availability checks
│   └── test_database.py          # Database connection validation
├── unit/                         # Unit tests
│   ├── __init__.py
│   └── test_database_minimal.py  # Database unit tests
├── api/                          # API tests (post-deployment)
│   ├── __init__.py
│   └── api_test.sh               # Shell script testing API endpoints
└── load/                         # Load tests (post-deployment)
    ├── __init__.py
    └── load_test_deploy.py       # Load testing script
```

## Test Types

1. **Pre-deployment Validation Tests**:
   - Verify environment configuration before deployment
   - Check Docker, networks, ports, and database
   - Run before deployment to prevent issues

2. **Unit Tests**:
   - Test individual components
   - Use mock objects and test databases
   - Verify internal logic works correctly

3. **API Tests**:
   - Test HTTP endpoints of running services
   - Verify correct responses and status codes
   - Run after deployment

4. **Load Tests**:
   - Test system under concurrent load
   - Verify stability and performance
   - Run after deployment

## CI Pipeline Integration

### GitHub Actions Integration

Below is a comprehensive GitHub Actions workflow that integrates our testing framework:

```yaml
name: CTF Deployer CI

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master, develop ]

jobs:
  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install lint dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort

      - name: Run flake8
        run: |
          flake8 flask_app/ --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Check formatting with black
        run: |
          black --check flask_app/

      - name: Check imports with isort
        run: |
          isort --check flask_app/

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      # PostgreSQL service container for database tests
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: secure_password
          POSTGRES_DB: ctf_deployer
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install test dependencies
        run: |
          python -m pip install --upgrade pip
          pip install psycopg2-binary python-dotenv pytest pytest-cov netifaces requests
          pip install -r flask_app/requirements.txt
      
      - name: Configure environment for CI
        run: |
          # Modify DB_HOST to use localhost instead of postgres
          sed -i 's/DB_HOST=postgres/DB_HOST=localhost/g' .env
          echo "Environment configured for CI - using localhost for database"

      - name: Verify database connection
        run: |
          python -c "
          import psycopg2
          try:
              conn = psycopg2.connect(
                  dbname='ctf_deployer',
                  user='postgres', 
                  password='secure_password',
                  host='localhost',
                  port=5432
              )
              print('Database connection successful!')
              conn.close()
          except Exception as e:
              print(f'Database connection failed: {e}')
              exit(1)
          "
      
      - name: Setup test directory structure
        run: |
          mkdir -p tests/unit
          touch tests/__init__.py tests/unit/__init__.py
          
          # Move tests to the right location if needed
          if [ -f "tests/test_database_minimal.py" ]; then
            mv tests/test_database_minimal.py tests/unit/
          fi
      
      - name: Run unit tests
        run: |
          python -m pytest tests/unit/ -v --cov=flask_app
      
      - name: Upload coverage report
        uses: actions/upload-artifact@v3
        with:
          name: unit-test-coverage
          path: .coverage
          retention-days: 5

  environment-tests:
    name: Environment Validation Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install test dependencies
        run: |
          python -m pip install --upgrade pip
          pip install psycopg2-binary python-dotenv pytest pytest-cov netifaces requests
      
      - name: Set up Docker
        uses: docker/setup-buildx-action@v2
      
      - name: Configure environment
        run: |
          # Modify specific values for CI testing
          sed -i 's/FLASK_APP_PORT=.*/FLASK_APP_PORT=7000/g' .env
          sed -i 's/DIRECT_TEST_PORT=.*/DIRECT_TEST_PORT=7001/g' .env
          sed -i 's/DB_HOST=.*/DB_HOST=localhost/g' .env
      
      - name: Setup test environment
        run: |
          # Create necessary directories and __init__.py files
          mkdir -p tests/environment
          touch tests/__init__.py tests/environment/__init__.py
          
          # Move tests to appropriate directories if needed
          for test_file in tests/test_*.py; do
            if [ -f "$test_file" ]; then
              if [[ "$test_file" != *"test_database_minimal.py"* ]]; then
                mv "$test_file" tests/environment/
              fi
            fi
          done
      
      - name: Run environment tests
        run: |
          python tests/run_tests.py -v

  build-test:
    name: Build and Smoke Test
    runs-on: ubuntu-latest
    needs: [unit-tests, environment-tests]
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Docker
        uses: docker/setup-buildx-action@v2
      
      - name: Configure environment
        run: |
          # Set specific values for CI testing
          sed -i 's/FLASK_APP_PORT=.*/FLASK_APP_PORT=7000/g' .env
          sed -i 's/DIRECT_TEST_PORT=.*/DIRECT_TEST_PORT=7001/g' .env
          sed -i 's/START_RANGE=.*/START_RANGE=7100/g' .env
          sed -i 's/STOP_RANGE=.*/STOP_RANGE=7200/g' .env

      - name: Build the Docker images
        run: |
          docker-compose build
      
      - name: Test image existence
        run: |
          docker-compose config
          docker images | grep generic_ctf_task

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install security scanner
        run: |
          python -m pip install --upgrade pip
          pip install bandit safety
      
      - name: Run Bandit security scan
        run: |
          bandit -r flask_app/ -x tests/,flask_app/templates/
      
      - name: Check dependencies for vulnerabilities
        run: |
          safety check -r flask_app/requirements.txt

  full-integration:
    name: Integration Test
    runs-on: ubuntu-latest
    needs: [build-test, security-scan]
    if: github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master')
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: secure_password
          POSTGRES_DB: ctf_deployer
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Docker
        uses: docker/setup-buildx-action@v2
      
      - name: Configure environment
        run: |
          # Modify for CI testing
          sed -i 's/DB_HOST=.*/DB_HOST=localhost/g' .env
          sed -i 's/FLASK_APP_PORT=.*/FLASK_APP_PORT=7000/g' .env
          sed -i 's/DIRECT_TEST_PORT=.*/DIRECT_TEST_PORT=7001/g' .env
          sed -i 's/START_RANGE=.*/START_RANGE=7100/g' .env
          sed -i 's/STOP_RANGE=.*/STOP_RANGE=7200/g' .env
          sed -i 's/ADMIN_KEY=.*/ADMIN_KEY=secure_test_key_for_ci_only/g' .env
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r flask_app/requirements.txt
          pip install psycopg2-binary python-dotenv pytest pytest-cov netifaces requests
      
      - name: Setup test environment
        run: |
          # Create necessary directories and __init__.py files
          mkdir -p tests/api
          touch tests/__init__.py tests/api/__init__.py
          
          # Move API test to appropriate directory if needed
          if [ -f "tests/api_test.sh" ]; then
            mv tests/api_test.sh tests/api/
            chmod +x tests/api/api_test.sh
          fi
      
      - name: Build and start services
        run: |
          docker-compose build
          docker-compose up -d
          echo "Waiting for services to start..."
          sleep 10
      
      - name: Run API tests
        run: |
          if [ -f "tests/api/api_test.sh" ]; then
            cd tests/api && ./api_test.sh
          else
            echo "API test script not found, skipping..."
          fi
      
      - name: Check service logs
        if: always()
        run: |
          docker-compose logs
      
      - name: Clean up
        if: always()
        run: |
          docker-compose down
```

### Manual CI Setup Steps

1. **Repository Setup**:
   - Create `.github/workflows/` directory in your repository
   - Add the CI workflow YAML file to this directory

2. **Secrets and Variables**:
   - Add any necessary secrets or variables in the GitHub repository settings
   - Common secrets might include database passwords or API keys

3. **Branch Protection**:
   - Enable branch protection rules for your main branches
   - Require status checks to pass before merging
   - Specify the CI workflow as a required status check

## Running Tests Locally

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL client libraries

### Running Tests

1. **Setup Test Environment**:
   ```bash
   cd tests
   ./setup_tests.sh
   ```

2. **Run Pre-Deployment Tests**:
   ```bash
   python run_tests.py -v
   ```

3. **Run Unit Tests**:
   ```bash
   python run_tests.py --unit-tests -v
   ```

4. **Deploy and Run API Tests**:
   ```bash
   # First deploy the system
   cd ..
   sudo ./deploy.sh up -s
   
   # Then run API tests
   cd tests/api
   ./api_test.sh
   ```

5. **Run Load Tests** (optional):
   ```bash
   cd tests/load
   python load_test_deploy.py
   ```

## Troubleshooting CI Issues

### Common CI Failures

1. **Database Connection Issues**:
   - Ensure the PostgreSQL service is properly configured
   - Check that the database host and credentials are correct
   - Verify database migrations run successfully

2. **Docker Build Failures**:
   - Check Dockerfile syntax
   - Ensure all required files are present
   - Verify base images are accessible

3. **Test Failures**:
   - Examine test logs for details
   - Check for environment-specific issues
   - Verify that tests are isolated and don't interfere with each other

### Debugging Strategies

1. **Enable Verbose Logging**:
   - Add `-v` flag to test commands
   - Set debug mode in the workflow file

2. **Run Specific Test Stages**:
   - Modify the workflow to run only specific jobs
   - Use conditional execution to focus on problematic areas

3. **Local Reproduction**:
   - Try to reproduce CI failures locally
   - Use Docker to simulate the CI environment

## CI Best Practices

1. **Keep Tests Fast**:
   - Optimize slow tests
   - Use test parallelization where possible
   - Consider separating long-running tests

2. **Maintain Test Independence**:
   - Tests should not depend on each other
   - Each test should clean up after itself
   - Use fresh environments for each test run

3. **Incremental Improvements**:
   - Start with basic CI and expand gradually
   - Add more comprehensive tests over time
   - Continuously improve test coverage

4. **Monitor CI Performance**:
   - Track build times and optimize slow steps
   - Watch for flaky tests
   - Regularly review and update CI configuration

## Conclusion

This testing framework and CI integration provide a solid foundation for ensuring the quality and reliability of the CTF Deployer project. By implementing these tests in your CI pipeline, you can catch issues early, maintain code quality, and provide confidence in the stability of your deployments.
