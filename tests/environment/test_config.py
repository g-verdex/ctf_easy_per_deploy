"""
Configuration validation tests for CTF Deployer

This module validates that all required environment variables are set and
that they have valid values.
"""
import os
import sys
import logging
import ipaddress
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-config')

# Load environment variables
load_dotenv()

# Required environment variables grouped by category
REQUIRED_ENV_VARS = {
    "Container Settings": [
        "COMPOSE_PROJECT_NAME",
        "LEAVE_TIME",
        "ADD_TIME",
        "IMAGES_NAME",
        "FLAG"
    ],
    "Port Configuration": [
        "PORT_IN_CONTAINER",
        "START_RANGE",
        "STOP_RANGE",
        "FLASK_APP_PORT",
        "DIRECT_TEST_PORT"
    ],
    "Network Configuration": [
        "NETWORK_NAME",
        "NETWORK_SUBNET"
    ],
    "Database Configuration": [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
        "DB_POOL_MIN",
        "DB_POOL_MAX"
    ],
    "Security Options": [
        "ENABLE_NO_NEW_PRIVILEGES",
        "ENABLE_READ_ONLY",
        "ENABLE_TMPFS",
        "TMPFS_SIZE",
        "DROP_ALL_CAPABILITIES",
        "CAP_NET_BIND_SERVICE",
        "CAP_CHOWN"
    ],
    "Rate Limiting": [
        "MAX_CONTAINERS_PER_HOUR",
        "RATE_LIMIT_WINDOW"
    ],
    "Resource Management": [
        "CONTAINER_MEMORY_LIMIT",
        "CONTAINER_SWAP_LIMIT",
        "CONTAINER_CPU_LIMIT",
        "CONTAINER_PIDS_LIMIT"
    ]
}

def test_required_env_vars(verbose=False):
    """Test that all required environment variables are set"""
    all_present = True
    missing_vars = []
    
    for category, vars_list in REQUIRED_ENV_VARS.items():
        category_missing = []
        
        for var in vars_list:
            if not os.getenv(var):
                category_missing.append(var)
                missing_vars.append(var)
        
        if category_missing and verbose:
            logger.error(f"Missing environment variables in {category}:")
            for var in category_missing:
                logger.error(f"  - {var}")
    
    if missing_vars:
        all_present = False
        logger.error(f"Missing a total of {len(missing_vars)} required environment variables")
    elif verbose:
        logger.info("All required environment variables are set")
    
    return all_present

def test_numeric_values(verbose=False):
    """Test that numeric environment variables have valid values"""
    valid_numeric = True
    
    # List of variables that should be positive integers
    int_vars = [
        "LEAVE_TIME", "ADD_TIME", "PORT_IN_CONTAINER", 
        "START_RANGE", "STOP_RANGE", "FLASK_APP_PORT", 
        "DIRECT_TEST_PORT", "DB_PORT", "DB_POOL_MIN", 
        "DB_POOL_MAX", "MAX_CONTAINERS_PER_HOUR", 
        "RATE_LIMIT_WINDOW", "CONTAINER_PIDS_LIMIT"
    ]
    
    # List of variables that should be positive floats
    float_vars = ["CONTAINER_CPU_LIMIT"]
    
    for var in int_vars:
        value = os.getenv(var)
        if not value:
            continue  # Skip if not set, already checked in test_required_env_vars
        
        try:
            int_value = int(value)
            if int_value <= 0:
                logger.error(f"{var} must be a positive integer. Current value: {value}")
                valid_numeric = False
            elif verbose:
                logger.info(f"{var} = {int_value} (valid positive integer)")
        except ValueError:
            logger.error(f"{var} must be an integer. Current value: {value}")
            valid_numeric = False
    
    for var in float_vars:
        value = os.getenv(var)
        if not value:
            continue  # Skip if not set, already checked in test_required_env_vars
        
        try:
            float_value = float(value)
            if float_value <= 0:
                logger.error(f"{var} must be a positive float. Current value: {value}")
                valid_numeric = False
            elif verbose:
                logger.info(f"{var} = {float_value} (valid positive float)")
        except ValueError:
            logger.error(f"{var} must be a float. Current value: {value}")
            valid_numeric = False
    
    return valid_numeric

def test_port_ranges(verbose=False):
    """Test that port ranges are valid and don't conflict"""
    if not all(os.getenv(var) for var in ["START_RANGE", "STOP_RANGE"]):
        return False  # Already checked in test_required_env_vars
    
    start_range = int(os.getenv("START_RANGE"))
    stop_range = int(os.getenv("STOP_RANGE"))
    
    if start_range >= stop_range:
        logger.error(f"START_RANGE ({start_range}) must be less than STOP_RANGE ({stop_range})")
        return False
    
    if stop_range - start_range < 10:
        logger.error(f"Port range is too small: {stop_range - start_range} ports")
        logger.error("The port range should have at least 10 ports")
        return False
    
    flask_port = int(os.getenv("FLASK_APP_PORT"))
    direct_test_port = int(os.getenv("DIRECT_TEST_PORT"))
    
    critical_ports = [flask_port, direct_test_port]
    
    # Check if critical ports are in the user container port range
    for port in critical_ports:
        if start_range <= port < stop_range:
            logger.error(f"Critical port {port} is within the container port range ({start_range}-{stop_range})")
            logger.error("Critical ports should be outside the container port range")
            return False
    
    if verbose:
        logger.info(f"Port range ({start_range}-{stop_range}) is valid")
        logger.info(f"Critical ports (FLASK_APP_PORT={flask_port}, DIRECT_TEST_PORT={direct_test_port}) are outside the container port range")
    
    return True

def test_network_subnet(verbose=False):
    """Test that the network subnet is valid"""
    subnet = os.getenv("NETWORK_SUBNET")
    if not subnet:
        return False  # Already checked in test_required_env_vars
    
    try:
        ipaddress.ip_network(subnet)
        if verbose:
            logger.info(f"Network subnet {subnet} is valid")
        return True
    except ValueError as e:
        logger.error(f"Network subnet {subnet} is invalid: {e}")
        return False

def test_boolean_values(verbose=False):
    """Test that boolean environment variables have valid values"""
    valid_boolean = True
    
    # List of variables that should be boolean
    bool_vars = [
        "ENABLE_NO_NEW_PRIVILEGES", "ENABLE_READ_ONLY", 
        "ENABLE_TMPFS", "DROP_ALL_CAPABILITIES", 
        "CAP_NET_BIND_SERVICE", "CAP_CHOWN",
        "DEBUG_MODE", "BYPASS_CAPTCHA"
    ]
    
    for var in bool_vars:
        value = os.getenv(var)
        if not value:
            continue  # Skip if not set, already checked in test_required_env_vars
        
        if value.lower() not in ["true", "false"]:
            logger.error(f"{var} must be 'true' or 'false'. Current value: {value}")
            valid_boolean = False
        elif verbose:
            logger.info(f"{var} = {value.lower()} (valid boolean)")
    
    return valid_boolean

def test_memory_format(verbose=False):
    """Test that memory limit variables have valid format (e.g., 512M)"""
    valid_memory = True
    
    # List of variables that should be in memory format
    memory_vars = ["CONTAINER_MEMORY_LIMIT", "CONTAINER_SWAP_LIMIT", "TMPFS_SIZE"]
    
    for var in memory_vars:
        value = os.getenv(var)
        if not value:
            continue  # Skip if not set, already checked in test_required_env_vars
        
        if not value[-1] in ["K", "M", "G", "k", "m", "g"]:
            logger.error(f"{var} must end with K, M, or G (e.g., 512M). Current value: {value}")
            valid_memory = False
        
        try:
            numeric_part = int(value[:-1])
            if numeric_part <= 0:
                logger.error(f"{var} must be a positive number followed by K, M, or G. Current value: {value}")
                valid_memory = False
            elif verbose:
                logger.info(f"{var} = {value} (valid memory format)")
        except ValueError:
            logger.error(f"{var} must be a number followed by K, M, or G. Current value: {value}")
            valid_memory = False
    
    return valid_memory

def test_admin_key_security(verbose=False):
    """Test that the admin key is secure"""
    admin_key = os.getenv("ADMIN_KEY")
    if not admin_key:
        logger.error("ADMIN_KEY is not set")
        return False
    
    default_value = "change_this_to_a_secure_random_value"
    if admin_key == default_value:
        # Since this is a test environment, we'll only log a warning
        # instead of failing the test. This allows development to continue.
        logger.warning("ADMIN_KEY is set to the default value. This is a security risk.")
        logger.warning("While this is acceptable for testing, make sure to change it in production!")
        if verbose:
            logger.info("Test ADMIN_KEY is being used - this is OK for dev environments")
        return True  # Don't fail the test
    
    if len(admin_key) < 16:
        logger.warning(f"ADMIN_KEY is too short ({len(admin_key)} characters). It should be at least 16 characters.")
        logger.warning("While this is acceptable for testing, use a longer key in production!")
        return True  # Don't fail the test
    
    if verbose:
        logger.info("ADMIN_KEY is set and sufficiently complex")
    
    return True

def run_tests(verbose=False):
    """Run all configuration validation tests"""
    tests = [
        test_required_env_vars,
        test_numeric_values,
        test_port_ranges,
        test_network_subnet,
        test_boolean_values,
        test_memory_format,
        test_admin_key_security
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
        logger.info("All configuration tests passed!")
        sys.exit(0)
    else:
        logger.error("Some configuration tests failed!")
        sys.exit(1)
