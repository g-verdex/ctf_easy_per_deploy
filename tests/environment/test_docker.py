"""
Docker validation tests for CTF Deployer

This module validates that Docker is installed, running, and properly configured
for the CTF Deployer.
"""
import os
import sys
import logging
import subprocess
import json
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger('test-docker')

# Load environment variables
load_dotenv()

def test_docker_installed(verbose=False):
    """Test that Docker is installed and in PATH"""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("Docker is not installed or not in PATH")
            return False
        
        if verbose:
            logger.info(f"Docker version: {result.stdout.strip()}")
        
        return True
    except FileNotFoundError:
        logger.error("Docker command not found in PATH")
        return False
    except Exception as e:
        logger.error(f"Error checking Docker installation: {e}")
        return False

def test_docker_running(verbose=False):
    """Test that Docker daemon is running"""
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("Docker daemon is not running")
            if verbose:
                logger.error(f"Docker info error: {result.stderr}")
            return False
        
        if verbose:
            logger.info("Docker daemon is running")
        
        return True
    except Exception as e:
        logger.error(f"Error checking Docker daemon: {e}")
        return False

def test_docker_compose(verbose=False):
    """Test that Docker Compose is installed and working"""
    # First try docker-compose
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if verbose:
                logger.info(f"docker-compose is available: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass  # Try docker compose next
    
    # Try docker compose (newer version)
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            if verbose:
                logger.info(f"docker compose is available: {result.stdout.strip()}")
            return True
    except Exception:
        pass
    
    logger.error("Neither docker-compose nor docker compose is available")
    return False

def test_image_conflict(verbose=False):
    """Test for potential image name conflicts"""
    images_name = os.getenv("IMAGES_NAME")
    if not images_name:
        logger.error("IMAGES_NAME is not set in the environment")
        return False
    
    compose_project_name = os.getenv("COMPOSE_PROJECT_NAME")
    if not compose_project_name:
        logger.error("COMPOSE_PROJECT_NAME is not set in the environment")
        return False
    
    try:
        # Check if the image already exists
        result = subprocess.run(
            ["docker", "image", "inspect", images_name],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Image exists, check if it's used by other projects
            container_check = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"ancestor={images_name}", "--format", "{{.Names}}"],
                check=False,
                capture_output=True,
                text=True
            )
            
            if container_check.returncode == 0 and container_check.stdout:
                # Get container names
                container_names = container_check.stdout.strip().split('\n')
                
                # Filter out containers from our project
                other_project_containers = [
                    name for name in container_names
                    if name and not name.startswith(compose_project_name)
                ]
                
                if other_project_containers:
                    logger.warning(f"Warning: Image {images_name} is used by containers from other projects:")
                    for container in other_project_containers:
                        logger.warning(f"  - {container}")
                    
                    logger.warning("This may cause conflicts if you continue. Consider changing IMAGES_NAME.")
                    
                    # Warning but not a failure
                    if verbose:
                        logger.info("Image conflict exists but deployment can continue")
                
            if verbose and not container_check.stdout:
                logger.info(f"Image {images_name} exists but is not used by any containers")
        
        # Not a critical failure, just a warning
        return True
    except Exception as e:
        logger.error(f"Error checking image conflicts: {e}")
        # Not a critical failure, just a warning
        return True

def test_docker_permissions(verbose=False):
    """Test that the current user has permission to use Docker"""
    try:
        # Create a simple container to test permissions
        result = subprocess.run(
            ["docker", "run", "--rm", "hello-world"],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("Current user does not have permission to use Docker")
            if "permission denied" in result.stderr.lower():
                logger.error("Permission denied. Try running the script with sudo or add your user to the docker group.")
            
            if verbose:
                logger.error(f"Docker run error: {result.stderr}")
            
            return False
        
        if verbose:
            logger.info("Current user has permission to use Docker")
        
        return True
    except Exception as e:
        logger.error(f"Error testing Docker permissions: {e}")
        return False

def test_docker_network(verbose=False):
    """Test that the Docker network configuration is valid"""
    network_name = os.getenv("NETWORK_NAME")
    if not network_name:
        logger.error("NETWORK_NAME is not set in the environment")
        return False
    
    network_subnet = os.getenv("NETWORK_SUBNET")
    if not network_subnet:
        logger.error("NETWORK_SUBNET is not set in the environment")
        return False
    
    # Check if the network already exists
    try:
        result = subprocess.run(
            ["docker", "network", "inspect", network_name],
            check=False,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Network exists, check if it's used by containers
            try:
                network_info = json.loads(result.stdout)
                if network_info and len(network_info) > 0:
                    containers = network_info[0].get("Containers", {})
                    
                    if containers and len(containers) > 0:
                        logger.warning(f"Network {network_name} has {len(containers)} containers attached")
                        
                        if verbose:
                            logger.warning("These containers may be affected if you recreate the network:")
                            for container_id, container_info in containers.items():
                                logger.warning(f"  - {container_info.get('Name', container_id)}")
                    
                    subnet = None
                    for config in network_info[0].get("IPAM", {}).get("Config", []):
                        if "Subnet" in config:
                            subnet = config["Subnet"]
                            break
                    
                    if subnet and subnet != network_subnet:
                        logger.warning(f"Network {network_name} exists with subnet {subnet}, but NETWORK_SUBNET is set to {network_subnet}")
                        logger.warning("This may cause conflicts. Consider using the existing subnet or removing the network.")
                
                if verbose:
                    logger.info(f"Network {network_name} exists and will be reused")
            except json.JSONDecodeError:
                logger.error(f"Failed to parse network inspect output: {result.stdout}")
        else:
            if verbose:
                logger.info(f"Network {network_name} does not exist and will be created")
    except Exception as e:
        logger.error(f"Error checking Docker network: {e}")
        return False
    
    # Check if the subnet conflicts with existing networks
    try:
        # Get all networks
        result = subprocess.run(
            ["docker", "network", "ls", "--format", "{{.Name}}"],
            check=True,
            capture_output=True,
            text=True
        )
        
        networks = result.stdout.strip().split('\n')
        
        for net in networks:
            if net and net != network_name and net not in ["host", "none", "bridge"]:
                # Inspect this network to get its subnet
                inspect_result = subprocess.run(
                    ["docker", "network", "inspect", net],
                    check=False,
                    capture_output=True,
                    text=True
                )
                
                if inspect_result.returncode == 0:
                    try:
                        net_info = json.loads(inspect_result.stdout)
                        if net_info and len(net_info) > 0:
                            for config in net_info[0].get("IPAM", {}).get("Config", []):
                                if "Subnet" in config and config["Subnet"] == network_subnet:
                                    logger.error(f"Subnet conflict: Network {net} already uses subnet {network_subnet}")
                                    return False
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        logger.error(f"Error checking for subnet conflicts: {e}")
        return False
    
    return True

def run_tests(verbose=False):
    """Run all Docker validation tests"""
    tests = [
        test_docker_installed,
        test_docker_running,
        test_docker_compose,
        test_image_conflict,
        test_docker_permissions,
        test_docker_network
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
        logger.info("All Docker tests passed!")
        sys.exit(0)
    else:
        logger.error("Some Docker tests failed!")
        sys.exit(1)
