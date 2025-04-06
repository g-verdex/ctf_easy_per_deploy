import docker
import time
import threading
from config import PORT_IN_CONTAINER, PORT_RANGE
from database import execute_query, remove_container_from_db

client = docker.from_env()
used_ports = set()

# Check if port is free
def is_port_free(port):
    for container in client.containers.list():
        container_ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
        for port_binding in container_ports.get(f"{PORT_IN_CONTAINER}/tcp", []):
            if port_binding['HostPort'] == str(port):
                return False
    return True

# Get a free port
def get_free_port():
    available_ports = list(set(PORT_RANGE) - used_ports)
    for port in available_ports:
        if is_port_free(port):
            used_ports.add(port)
            return port
    return None

# Remove a container
def remove_container(container_id, port):
    try:
        container = client.containers.get(container_id)
        container.remove(force=True)
        print(f"[SUCCESS] Container {container_id} removed.")
    except docker.errors.NotFound:
        print(f"[WARNING] Container {container_id} not found in Docker, but still in database.")

    used_ports.discard(port)

    execute_query("DELETE FROM containers WHERE id = ?", (container_id,))
    print(f"[SUCCESS] Container {container_id} removed from database.")

# Automatically remove container after expiration time
def auto_remove_expired_containers():
    try:
        while True:
            current_time = int(time.time())
            containers = execute_query(
                "SELECT id, port, expiration_time FROM containers",
                fetchall=True
            )

            soonest_expiration = None

            if not containers:
                print("[INFO] No containers in database.")
            else:
                for container_id, port, expiration_time in containers:
                    time_left = expiration_time - current_time
                    if time_left <= 0:
                        print(f"[INFO] Expired container detected: {container_id}. Removing...")
                        try:
                            remove_container(container_id, port)
                        except Exception as remove_err:
                            print(f"[ERROR] Failed to remove container {container_id}: {remove_err}")
                    else:
                        if soonest_expiration is None or time_left < soonest_expiration:
                            soonest_expiration = time_left

            # We wait either until the next expiration, or 30 seconds if there are no urgent ones.
            sleep_time = min(soonest_expiration, 30) if soonest_expiration is not None else 30
            print(f"[INFO] Next check in {sleep_time} seconds.")
            time.sleep(sleep_time)

    except Exception as e:
        print(f"[ERROR] Unexpected error in auto_remove_expired_containers: {e}")

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
        print(f"[ERROR] Error getting container status: {e}")
        return {
            'status': 'error',
            'running': False
        }
