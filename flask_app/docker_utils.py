import docker
import time
import threading
import logging
from config import (
    # Import only basic variables, not complex objects
    PORT_IN_CONTAINER, START_RANGE, STOP_RANGE, 
    CONTAINER_MEMORY_LIMIT, CONTAINER_SWAP_LIMIT, CONTAINER_CPU_LIMIT, CONTAINER_PIDS_LIMIT,
    ENABLE_NO_NEW_PRIVILEGES, ENABLE_READ_ONLY, ENABLE_TMPFS, TMPFS_SIZE,
    DROP_ALL_CAPABILITIES, CAP_NET_BIND_SERVICE, CAP_CHOWN
)
from database import execute_query, remove_container_from_db

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ctf-deployer')

# Create complex objects locally
try:
    # Create PORT_RANGE from basic variables
    PORT_RANGE = range(START_RANGE, STOP_RANGE)
    logger.info(f"Created PORT_RANGE from {START_RANGE} to {STOP_RANGE-1}")
except Exception as e:
    logger.error(f"Failed to create PORT_RANGE: {str(e)}")
    raise RuntimeError(f"Failed to initialize critical configuration: {str(e)}")

# Initialize Docker client with error handling
try:
    client = docker.from_env()
    # Test the connection
    client.ping()
    logger.info("Docker client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Docker client: {str(e)}")
    raise RuntimeError(f"Failed to connect to Docker daemon: {str(e)}")

# Set to track used ports
used_ports = set()

# Export PORT_RANGE to be accessible to other modules
__all__ = ['PORT_RANGE', 'client', 'get_free_port', 'auto_remove_container', 'remove_container', 
           'get_container_status', 'get_container_security_options', 
           'get_container_capabilities', 'get_container_tmpfs']

# Check if port is free
def is_port_free(port):
    try:
        for container in client.containers.list():
            container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            for port_binding in container_ports.get(f"{PORT_IN_CONTAINER}/tcp", []) or []:
                if port_binding.get('HostPort') == str(port):
                    return False
        return True
    except Exception as e:
        logger.error(f"Error checking if port {port} is free: {str(e)}")
        return False

# Get a free port
def get_free_port():
    try:
        # Verify we have a valid PORT_RANGE
        if not PORT_RANGE or len(list(PORT_RANGE)) == 0:
            logger.error("Invalid PORT_RANGE configuration")
            return None
        
        # Get available ports
        available_ports = list(set(PORT_RANGE) - used_ports)
        logger.debug(f"Found {len(available_ports)} potentially available ports")
        
        if not available_ports:
            logger.warning("No ports available in the range")
            return None
        
        # Try each port until we find a free one
        for port in available_ports:
            if is_port_free(port):
                used_ports.add(port)
                logger.info(f"Allocated port {port}")
                return port
        
        logger.warning("No free ports found in the available range")
        return None
    except Exception as e:
        logger.error(f"Error finding free port: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

# Remove a container
def remove_container(container_id, port):
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        logger.info(f"Container {container_id} removed.")
    except docker.errors.NotFound:
        logger.warning(f"Container {container_id} not found in Docker, but still in database.")
    except Exception as e:
        logger.error(f"Failed to remove container {container_id}: {str(e)}")

    # Always remove port from used_ports set and from database regardless of removal status
    used_ports.discard(port)
    try:
        # Use execute_insert here to avoid trying to fetch results
        remove_container_from_db(container_id)
        logger.info(f"Container {container_id} removed from database.")
    except Exception as e:
        logger.error(f"Failed to remove container {container_id} from database: {str(e)}")

# Automatically remove container after expiration time
def auto_remove_container(container_id, port):
    try:
        while True:
            container_data = execute_query("SELECT expiration_time FROM containers WHERE id = %s", (container_id,), fetchone=True)
            if not container_data:
                logger.info(f"Container {container_id} not found in database. Stopping thread.")
                return  # Exit the thread

            expiration_time = container_data[0]
            current_time = int(time.time())
            time_to_wait = expiration_time - current_time

            if time_to_wait <= 0:
                break  # Time expired - remove container

            logger.debug(f"Container {container_id} will be checked again in 30 sec. Time left: {time_to_wait}s")
            time.sleep(min(time_to_wait, 30))  # Check every 30 seconds or until time expires

        logger.info(f"Removing container {container_id} due to expiration.")
        remove_container(container_id, port)

    except Exception as e:
        logger.error(f"Unexpected error in auto_remove_container: {str(e)}")

# Get container status
def get_container_status(container_id):
    try:
        container = client.containers.get(container_id)
        return {
            'status': container.status,
            'running': container.status == 'running'
        }
    except docker.errors.NotFound:
        return {
            'status': 'not_found',
            'running': False
        }
    except Exception as e:
        logger.error(f"Error getting container status: {str(e)}")
        return {
            'status': 'error',
            'running': False
        }

# Configure security options for container
def get_container_security_options():
    try:
        security_options = []
        
        # Add no-new-privileges if enabled
        if ENABLE_NO_NEW_PRIVILEGES:
            security_options.append("no-new-privileges:true")
        
        return security_options
    except Exception as e:
        logger.error(f"Error configuring security options: {str(e)}")
        return []

# Configure container capabilities
def get_container_capabilities():
    try:
        capabilities = {
            'drop_all': DROP_ALL_CAPABILITIES,
            'add': []
        }
        
        # Add capabilities if needed
        if CAP_NET_BIND_SERVICE:
            capabilities['add'].append('NET_BIND_SERVICE')
        
        if CAP_CHOWN:
            capabilities['add'].append('CHOWN')
        
        return capabilities
    except Exception as e:
        logger.error(f"Error configuring capabilities: {str(e)}")
        return {'drop_all': False, 'add': []}

# Configure container tmpfs if enabled
def get_container_tmpfs():
    try:
        if not ENABLE_TMPFS:
            return None
        
        return {'/tmp': f'exec,size={TMPFS_SIZE}'}
    except Exception as e:
        logger.error(f"Error configuring tmpfs: {str(e)}")
        return None
