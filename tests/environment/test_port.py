"""
Port validation tests for CTF Deployer

This module validates that required ports are available and not already in use.
"""
import os
import sys
import logging
import socket
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-port')

# Load environment variables
load_dotenv()

# List of browser restricted ports to check against
BAD_PORTS = [
    1, 7, 9, 11, 13, 15, 17, 19, 20, 21, 22, 23, 25, 37, 42, 43, 53, 69, 77, 79, 87, 
    95, 101, 102, 103, 104, 109, 110, 111, 113, 115, 117, 119, 123, 135, 137, 139, 143, 
    161, 179, 389, 427, 465, 512, 513, 514, 515, 526, 530, 531, 532, 540, 548, 554, 556, 
    563, 587, 601, 636, 989, 990, 993, 995, 1719, 1720, 1723, 2049, 3659, 4045, 4190, 
    5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6679, 6697, 10080
]

def is_port_in_use(port, verbose=False):
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            if verbose:
                logger.warning(f"Port {port} is already in use")
            return True

def test_critical_ports(verbose=False):
    """Test that critical service ports are available"""
    flask_app_port = int(os.getenv("FLASK_APP_PORT", "0"))
    direct_test_port = int(os.getenv("DIRECT_TEST_PORT", "0"))
    db_port = int(os.getenv("DB_PORT", "0"))
    
    # Ports to check
    ports_to_check = {
        "FLASK_APP_PORT": flask_app_port,
        "DIRECT_TEST_PORT": direct_test_port,
        "DB_PORT": db_port
    }
    
    all_ports_available = True
    
    for name, port in ports_to_check.items():
        if port == 0:
            logger.error(f"{name} is not set or invalid")
            all_ports_available = False
            continue
        
        if is_port_in_use(port, verbose):
            logger.error(f"{name} ({port}) is already in use")
            all_ports_available = False
        elif verbose:
            logger.info(f"{name} ({port}) is available")
    
    return all_ports_available

def test_ports_not_restricted(verbose=False):
    """Test that ports are not in the browser restricted list"""
    flask_app_port = int(os.getenv("FLASK_APP_PORT", "0"))
    direct_test_port = int(os.getenv("DIRECT_TEST_PORT", "0"))
    port_in_container = int(os.getenv("PORT_IN_CONTAINER", "0"))
    start_range = int(os.getenv("START_RANGE", "0"))
    stop_range = int(os.getenv("STOP_RANGE", "0"))
    
    # Services that should not use restricted ports
    services_to_check = {
        "FLASK_APP_PORT": flask_app_port,
        "DIRECT_TEST_PORT": direct_test_port,
        "PORT_IN_CONTAINER": port_in_container
    }
    
    all_ports_valid = True
    
    # Check service ports
    for name, port in services_to_check.items():
        if port == 0:
            logger.error(f"{name} is not set or invalid")
            all_ports_valid = False
            continue
        
        if port in BAD_PORTS:
            logger.error(f"{name} ({port}) is a browser restricted port")
            all_ports_valid = False
        elif verbose:
            logger.info(f"{name} ({port}) is not a restricted port")
    
    # Check port range for restricted ports
    if start_range > 0 and stop_range > 0:
        restricted_in_range = [port for port in BAD_PORTS if start_range <= port < stop_range]
        
        if restricted_in_range:
            logger.error(f"Port range ({start_range}-{stop_range}) includes restricted ports: {restricted_in_range}")
            if verbose:
                logger.error("These ports may cause issues with browser connections")
            # We'll treat this as a warning, not a failure
            # all_ports_valid = False
        elif verbose:
            logger.info(f"Port range ({start_range}-{stop_range}) does not include any restricted ports")
    
    return all_ports_valid

def test_port_allocation_sample(verbose=False):
    """Test a sample of ports in the allocation range for availability"""
    start_range = int(os.getenv("START_RANGE", "0"))
    stop_range = int(os.getenv("STOP_RANGE", "0"))
    
    if start_range == 0 or stop_range == 0:
        logger.error("START_RANGE or STOP_RANGE is not set or invalid")
        return False
    
    # Take a sample of ports to check for availability
    range_size = stop_range - start_range
    
    # Calculate step size based on range
    # For large ranges, test fewer ports; for small ranges, test more
    if range_size > 1000:
        step = range_size // 20  # Test about 20 ports
    elif range_size > 100:
        step = range_size // 10  # Test about 10 ports
    else:
        step = max(1, range_size // 5)  # Test about 5 ports
    
    if step == 0:
        step = 1
    
    ports_to_check = list(range(start_range, stop_range, step))
    
    # Always check the first and last ports
    if start_range not in ports_to_check:
        ports_to_check.append(start_range)
    if stop_range - 1 not in ports_to_check:
        ports_to_check.append(stop_range - 1)
    
    # Sort the list for cleaner output
    ports_to_check.sort()
    
    # Ports already found to be in use
    unavailable_ports = []
    
    # Check each port
    for port in ports_to_check:
        if is_port_in_use(port, False):  # Don't log each check
            unavailable_ports.append(port)
    
    # Report results
    available_percent = 100 * (len(ports_to_check) - len(unavailable_ports)) / len(ports_to_check)
    
    if unavailable_ports:
        logger.warning(f"{len(unavailable_ports)} of {len(ports_to_check)} sampled ports are already in use")
        logger.warning(f"Approximately {available_percent:.1f}% of the port range is available")
        
        if verbose:
            logger.warning(f"Unavailable ports in sample: {unavailable_ports}")
        
        # Only fail if more than 50% of sampled ports are unavailable
        if available_percent < 50:
            logger.error("More than 50% of sampled ports are unavailable")
            logger.error("There may not be enough ports for the deployer to function properly")
            return False
    elif verbose:
        logger.info(f"All {len(ports_to_check)} sampled ports in range {start_range}-{stop_range} are available")
    
    return True

def run_tests(verbose=False):
    """Run all port validation tests"""
    tests = [
        test_critical_ports,
        test_ports_not_restricted,
        test_port_allocation_sample
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
        logger.info("All port tests passed!")
        sys.exit(0)
    else:
        logger.error("Some port tests failed!")
        sys.exit(1)
