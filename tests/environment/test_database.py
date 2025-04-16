"""
Database validation tests for CTF Deployer (Pre-Deployment Version)

This module validates that the database configuration settings are correct
without requiring an actual connection to the database.
"""
import os
import sys
import logging
import socket
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-database')

# Load environment variables
load_dotenv()

def test_db_config_values(verbose=False):
    """Test that database configuration values are present and valid"""
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    # Check if all required values are set
    if not all([db_host, db_port, db_name, db_user, db_password]):
        missing = []
        if not db_host: missing.append("DB_HOST")
        if not db_port: missing.append("DB_PORT")
        if not db_name: missing.append("DB_NAME")
        if not db_user: missing.append("DB_USER")
        if not db_password: missing.append("DB_PASSWORD")
        
        logger.error(f"Missing database configuration: {', '.join(missing)}")
        return False
    
    # Validate port is numeric
    try:
        port = int(db_port)
        if port <= 0 or port > 65535:
            logger.error(f"DB_PORT must be between 1 and 65535, got {port}")
            return False
        elif verbose:
            logger.info(f"DB_PORT {port} is valid")
    except ValueError:
        logger.error(f"DB_PORT must be a number, got '{db_port}'")
        return False
    
    # Check if host is reasonable (don't try to connect, just check format)
    if db_host == "":
        logger.error("DB_HOST cannot be empty")
        return False
    
    # Validate database name
    if db_name == "":
        logger.error("DB_NAME cannot be empty")
        return False
    
    # Don't validate password strength, but check it's not empty
    if db_password == "":
        logger.error("DB_PASSWORD cannot be empty")
        return False
    
    if verbose:
        logger.info(f"Database configuration appears valid:")
        logger.info(f"  - DB_HOST: {db_host}")
        logger.info(f"  - DB_PORT: {db_port}")
        logger.info(f"  - DB_NAME: {db_name}")
        logger.info(f"  - DB_USER: {db_user}")
        logger.info(f"  - DB_PASSWORD: {'*' * len(db_password)}")
    
    return True

def test_connection_params_consistency(verbose=False):
    """Test that database connection parameters are consistent with docker-compose.yml"""
    db_host = os.getenv("DB_HOST")
    
    # When running with docker-compose, the DB_HOST should typically be 'postgres'
    # unless an external database is being used
    expected_docker_db_host = "postgres"
    
    if db_host != expected_docker_db_host:
        # This is not a failure, just a warning
        logger.warning(f"DB_HOST is set to '{db_host}', but the docker-compose configuration typically uses '{expected_docker_db_host}'")
        logger.warning("This is only an issue if you're using the built-in PostgreSQL container from docker-compose.yml")
        logger.warning("If you're using an external database, this warning can be ignored")
    elif verbose:
        logger.info(f"DB_HOST is set to '{db_host}', which is consistent with docker-compose.yml")
    
    # Always return True since this is just a warning
    return True

def test_database_pool_settings(verbose=False):
    """Test that database pool settings are valid"""
    db_pool_min = os.getenv("DB_POOL_MIN")
    db_pool_max = os.getenv("DB_POOL_MAX")
    
    if not db_pool_min or not db_pool_max:
        logger.error("DB_POOL_MIN or DB_POOL_MAX is not set")
        return False
    
    try:
        db_pool_min = int(db_pool_min)
        db_pool_max = int(db_pool_max)
        
        if db_pool_min <= 0:
            logger.error(f"DB_POOL_MIN must be positive, got {db_pool_min}")
            return False
        
        if db_pool_max <= 0:
            logger.error(f"DB_POOL_MAX must be positive, got {db_pool_max}")
            return False
        
        if db_pool_min > db_pool_max:
            logger.error(f"DB_POOL_MIN ({db_pool_min}) must be less than or equal to DB_POOL_MAX ({db_pool_max})")
            return False
        
        if db_pool_max > 100:
            # This is not a failure, just a warning
            logger.warning(f"DB_POOL_MAX is set to {db_pool_max}, which is quite high")
            logger.warning("Consider reducing it to avoid overloading the database server")
        
        if verbose:
            logger.info(f"Database pool settings are valid: MIN={db_pool_min}, MAX={db_pool_max}")
        
        return True
    except ValueError:
        logger.error(f"DB_POOL_MIN ({db_pool_min}) and DB_POOL_MAX ({db_pool_max}) must be integers")
        return False

def run_tests(verbose=False):
    """Run all database configuration validation tests (pre-deployment only)"""
    tests = [
        test_db_config_values,
        test_connection_params_consistency,
        test_database_pool_settings
    ]
    
    all_tests_passed = True
    
    for test_func in tests:
        try:
            if not test_func(verbose):
                all_tests_passed = False
        except Exception as e:
            logger.error(f"Error in {test_func.__name__}: {e}")
            all_tests_passed = False
    
    return all_tests_passed

if __name__ == "__main__":
    # Set up logging when run directly
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Run all tests with verbose output
    success = run_tests(verbose=True)
    
    if success:
        logger.info("All database configuration tests passed!")
        sys.exit(0)
    else:
        logger.error("Some database configuration tests failed!")
        sys.exit(1)
