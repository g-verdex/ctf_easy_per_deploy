"""
Network validation tests for CTF Deployer

This module validates the network configuration for the CTF Deployer,
including subnet validation, network availability, and DNS resolution.
"""
import os
import sys
import logging
import ipaddress
import socket
import subprocess
import json
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-network')

# Load environment variables
load_dotenv()

def test_subnet_validation(verbose=False):
    """Test that the network subnet is valid"""
    subnet = os.getenv("NETWORK_SUBNET")
    
    if not subnet:
        logger.error("NETWORK_SUBNET is not set")
        return False
    
    try:
        network = ipaddress.ip_network(subnet)
        
        # Check network size - shouldn't be too small or too large
        if network.num_addresses < 256:  # Less than a /24
            logger.warning(f"Network subnet {subnet} is quite small, with only {network.num_addresses} addresses")
            logger.warning("This might limit the number of containers you can run")
        
        if network.num_addresses > 65536:  # Larger than a /16
            logger.warning(f"Network subnet {subnet} is very large, with {network.num_addresses} addresses")
            logger.warning("This might impact performance or conflict with other networks")
        
        # Check if it's a private network
        if not network.is_private:
            logger.warning(f"Network subnet {subnet} is not a private network")
            logger.warning("You should use private IP ranges for Docker networks")
        
        if verbose:
            logger.info(f"Network subnet {subnet} is valid")
            logger.info(f"Network has {network.num_addresses} usable addresses")
            logger.info(f"Network is {'private' if network.is_private else 'public'}")
        
        return True
    except ValueError as e:
        logger.error(f"Invalid network subnet {subnet}: {e}")
        return False

def test_subnet_conflicts(verbose=False):
    """Test that the network subnet doesn't conflict with existing networks"""
    subnet = os.getenv("NETWORK_SUBNET")
    
    if not subnet:
        logger.error("NETWORK_SUBNET is not set")
        return False
    
    try:
        our_network = ipaddress.ip_network(subnet)
        
        # Get all local interfaces and their IPs
        conflicts = []
        
        # Check for conflicts with Docker networks first
        try:
            result = subprocess.run(
                ["docker", "network", "ls", "--format", "{{.Name}}"],
                check=True,
                capture_output=True,
                text=True
            )
            
            networks = result.stdout.strip().split('\n')
            network_name = os.getenv("NETWORK_NAME")
            
            for net_name in networks:
                if not net_name or net_name == network_name:
                    continue
                
                if net_name in ["host", "none", "bridge"]:
                    continue
                
                # Inspect this network to get its subnet
                inspect_result = subprocess.run(
                    ["docker", "network", "inspect", net_name],
                    check=False,
                    capture_output=True,
                    text=True
                )
                
                if inspect_result.returncode != 0:
                    continue
                
                try:
                    net_info = json.loads(inspect_result.stdout)
                    if not net_info or not isinstance(net_info, list) or len(net_info) == 0:
                        continue
                    
                    configs = net_info[0].get("IPAM", {}).get("Config", [])
                    
                    for config in configs:
                        if "Subnet" in config:
                            other_subnet = config["Subnet"]
                            try:
                                other_network = ipaddress.ip_network(other_subnet)
                                
                                if our_network.overlaps(other_network):
                                    conflicts.append((net_name, other_subnet))
                            except ValueError:
                                continue
                except (json.JSONDecodeError, KeyError):
                    continue
        except Exception as e:
            logger.warning(f"Could not check Docker networks: {e}")
        
        # Check for conflicts with host network interfaces
        try:
            import netifaces
            
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        if 'addr' in addr and 'netmask' in addr:
                            ip = addr['addr']
                            netmask = addr['netmask']
                            
                            try:
                                # Create a network from the interface's IP and netmask
                                cidr = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                
                                if our_network.overlaps(cidr):
                                    conflicts.append((interface, f"{ip}/{netmask}"))
                            except ValueError:
                                continue
        except ImportError:
            logger.warning("netifaces module not available, skipping host network check")
        except Exception as e:
            logger.warning(f"Error checking host networks: {e}")
        
        if conflicts:
            logger.error(f"Network subnet {subnet} conflicts with existing networks:")
            for name, conflicting_subnet in conflicts:
                logger.error(f"  - {name}: {conflicting_subnet}")
            return False
        elif verbose:
            logger.info(f"Network subnet {subnet} does not conflict with existing networks")
        
        return True
    except Exception as e:
        logger.error(f"Error checking subnet conflicts: {e}")
        return False

def test_dns_resolution(verbose=False):
    """Test that DNS resolution is working"""
    try:
        # Test with a few well-known domains
        domains = [
            "google.com",
            "github.com",
            "dockerhub.com"
        ]
        
        failed_domains = []
        
        for domain in domains:
            try:
                ip = socket.gethostbyname(domain)
                if verbose:
                    logger.info(f"Successfully resolved {domain} to {ip}")
            except socket.gaierror:
                failed_domains.append(domain)
        
        if failed_domains:
            logger.error("DNS resolution failed for the following domains:")
            for domain in failed_domains:
                logger.error(f"  - {domain}")
            
            if len(failed_domains) == len(domains):
                logger.error("All DNS resolution attempts failed. Check your network configuration.")
                return False
            else:
                # If some domains resolved, it might just be those specific domains
                logger.warning("Some domains could not be resolved, but others worked")
                logger.warning("This might indicate network connectivity issues")
                # Return true since partial DNS resolution is acceptable
                return True
        elif verbose:
            logger.info("DNS resolution is working correctly")
        
        return True
    except Exception as e:
        logger.error(f"Error testing DNS resolution: {e}")
        return False

def test_network_connectivity(verbose=False):
    """Test that the network has internet connectivity"""
    endpoints = [
        ("google.com", 443),
        ("github.com", 443),
        ("dockerhub.com", 443)
    ]
    
    failed_endpoints = []
    
    for host, port in endpoints:
        try:
            start_time = time.time()
            
            # Try to connect with a timeout
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            
            try:
                ip = socket.gethostbyname(host)
                s.connect((ip, port))
                s.shutdown(socket.SHUT_RDWR)
                
                if verbose:
                    duration = time.time() - start_time
                    logger.info(f"Connected to {host}:{port} ({ip}) in {duration:.2f}s")
            except (socket.gaierror, socket.timeout, socket.error) as e:
                failed_endpoints.append((host, port, str(e)))
            finally:
                s.close()
        except Exception as e:
            failed_endpoints.append((host, port, str(e)))
    
    if failed_endpoints:
        logger.error("Network connectivity test failed for the following endpoints:")
        for host, port, error in failed_endpoints:
            logger.error(f"  - {host}:{port} - {error}")
        
        if len(failed_endpoints) == len(endpoints):
            logger.error("All connectivity tests failed. Your network might be disconnected.")
            return False
        else:
            # If some endpoints connected, it might just be those specific endpoints
            logger.warning("Some connectivity tests failed, but others succeeded")
            logger.warning("This might indicate limited network connectivity")
            # Return true since partial connectivity is acceptable
            return True
    elif verbose:
        logger.info("Network connectivity is working correctly")
    
    return True

def run_tests(verbose=False):
    """Run all network validation tests"""
    tests = [
        test_subnet_validation,
        test_subnet_conflicts,
        test_dns_resolution
    ]
    
    # Only add the connectivity test if DNS resolution works
    # (to avoid duplicating errors)
    if test_dns_resolution(False):
        tests.append(test_network_connectivity)
    
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
        logger.info("All network tests passed!")
        sys.exit(0)
    else:
        logger.error("Some network tests failed!")
        sys.exit(1)
